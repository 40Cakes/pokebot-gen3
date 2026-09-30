"""
WebRTC streaming of the emulator's video and audio output (and input from the browser.)

This needs aiortc, which is an optional dependency. `modules.web.http` only imports this
module if it is installed.
"""

import asyncio
import base64
import fractions
import hashlib
import hmac
import json
import queue
import time
import uuid
from queue import Queue
from typing import Callable, Union

from aiortc import (
    MediaStreamTrack,
    VideoStreamTrack,
    RTCConfiguration,
    RTCPeerConnection,
    RTCSessionDescription,
)
from aiortc.contrib.media import MediaRelay
from aiortc.mediastreams import MediaStreamError
from av import VideoFrame, Packet, AudioFrame, AudioResampler
from av.frame import Frame
from PIL import Image

from modules.context import context

# How long the TURN credentials handed out to the browser remain valid, in seconds. The TURN
# server only checks this when a connection is set up, so it does not limit how long a stream
# can run. And the browser fetches new credentials before every connection attempt.
turn_credential_lifetime = 3600


def get_client_config() -> dict:
    """
    :return: The ICE configuration for the browser's `RTCPeerConnection`. If a TURN server has been
             configured, the browser is told to only use that (see `startVideo()` in `index.html`.)
    """
    turn = context.config.http.webrtc.turn
    if turn is None:
        return {"iceServers": [], "iceTransportPolicy": "all"}

    # This is the 'TURN REST API' scheme that coturn's `use-auth-secret` option expects,
    # so the secret itself never has to be handed to the browser.
    username = f"{int(time.time()) + turn_credential_lifetime}:pokebot"
    digest = hmac.new(turn.secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1).digest()
    credential = base64.b64encode(digest).decode("ascii")

    return {
        "iceServers": [{"urls": turn.urls, "username": username, "credential": credential}],
        "iceTransportPolicy": "relay",
    }


class EmuVideo(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self._black_image: Image.Image = Image.new("RGB", (240, 160))

    async def recv(self) -> Union[Frame, Packet]:
        pts, time_base = await self.next_timestamp()

        # If video is disabled, mGBA does not render anything, so the screen buffer
        # would contain rubbish. Send a black image instead.
        if context.video:
            image = context.emulator.get_current_screen_image()
        else:
            image = self._black_image

        # The same frame object is passed to the encoders of all connected clients, which
        # run in separate threads. The encoder would convert the frame to YUV if it isn't
        # already, but `reformat()` is not thread-safe and crashes the process if several
        # threads call it on the same frame at once. So convert it once, here.
        frame = VideoFrame.from_image(image).reformat(format="yuv420p")
        frame.pts = pts
        frame.time_base = time_base

        return frame


class EmuAudio(MediaStreamTrack):
    """
    Streams the emulator's audio output.

    The emulator's sample rate depends on the host's audio device and may change at
    runtime (e.g. when that device disappears), but aiortc's encoder cannot handle a
    change of sample rate mid-stream. So all audio is resampled to a fixed rate here.
    """

    kind = "audio"
    output_sample_rate = 48000

    # If the timestamp of the audio lags behind the wall clock by more than this
    # many seconds, it is assumed that the emulator has not been producing audio
    # for a while (because it was paused or running unthrottled.)
    maximum_lag = 0.25

    def __init__(self):
        super().__init__()
        self._queue: Queue[bytes] = context.emulator.get_last_audio_data()
        self._resampler: AudioResampler | None = None
        self._resampler_input_rate: int | None = None
        self._start: float | None = None
        self._timestamp: int = 0

    async def _get_audio_data(self) -> bytes:
        while True:
            if self.readyState != "live":
                raise MediaStreamError
            try:
                data = self._queue.get_nowait()
                if len(data) > 0:
                    return data
            except queue.Empty:
                await asyncio.sleep(1 / 480)

    def _resample(self, data: bytes) -> bytes:
        input_sample_rate = context.emulator.get_sample_rate()
        if self._resampler is None or self._resampler_input_rate != input_sample_rate:
            self._resampler = AudioResampler(format="s16", layout="stereo", rate=self.output_sample_rate)
            self._resampler_input_rate = input_sample_rate

        input_frame = AudioFrame(format="s16", layout="stereo", samples=len(data) // 4)
        input_frame.planes[0].update(data)
        input_frame.sample_rate = input_sample_rate

        return b"".join(
            bytes(output_frame.planes[0])[: output_frame.samples * 4]
            for output_frame in self._resampler.resample(input_frame)
        )

    async def recv(self) -> Union[Frame, Packet]:
        if self.readyState != "live":
            raise MediaStreamError

        if self._start is None:
            # Discard audio that has been queued up before anyone was listening.
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break

        # The resampler may hold back some samples, so it is possible that we
        # need to feed it more than one chunk before we get any output.
        data = b""
        while len(data) == 0:
            data = self._resample(await self._get_audio_data())

        now = time.time()
        if self._start is None:
            self._start = now
        elif now - (self._start + self._timestamp / self.output_sample_rate) > self.maximum_lag:
            # Skip the timestamp ahead so that the browser treats this as a gap in
            # the audio rather than as audio that has been delayed.
            self._timestamp = int((now - self._start) * self.output_sample_rate)

        frame = AudioFrame(format="s16", layout="stereo", samples=len(data) // 4)
        frame.planes[0].update(data)
        frame.sample_rate = self.output_sample_rate
        frame.time_base = fractions.Fraction(1, self.output_sample_rate)
        frame.pts = self._timestamp

        self._timestamp += frame.samples

        return frame


# Open connections, by the ID that `answer_offer()` returned for them.
rtc_connections: dict[str, RTCPeerConnection] = {}
relay = MediaRelay()
emu_audio: EmuAudio | None = None
emu_video: EmuVideo | None = None


def stop_streams_if_unused() -> None:
    """
    The relay keeps reading from the source tracks even after all subscribers are
    gone. So once the last connection has closed, we stop the tracks (which ends the
    relay's reading task) and create new ones for the next client.
    """
    global emu_video, emu_audio
    if len(rtc_connections) == 0:
        if emu_video is not None:
            emu_video.stop()
            emu_video = None
        if emu_audio is not None:
            emu_audio.stop()
            emu_audio = None


async def answer_offer(sdp: str, type: str, set_held_buttons: Callable[[list], None]) -> dict:
    """
    Sets up a connection to a browser that wants to receive the stream.

    :param sdp: SDP of the browser's offer.
    :param type: Type of the browser's session description (i.e. 'offer'.)
    :param set_held_buttons: Function that replaces the set of buttons held down in the emulator,
                             for input that the browser sends via the 'input' data channel.
    :return: The answer's session description, to be sent back to the browser, plus the ID
             of the new connection (which can be passed to `close_connections()`.)
    """
    global emu_video, emu_audio

    offer = RTCSessionDescription(sdp=sdp, type=type)

    connection = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    connection_id = str(uuid.uuid4())
    rtc_connections[connection_id] = connection

    @connection.on("datachannel")
    def on_datachannel(channel):
        if channel.label == "input":
            last_message_time = time.monotonic()
            buttons_held = False

            # Each message contains the full list of buttons that should be held down,
            # in the same format as `POST /input`.
            @channel.on("message")
            def on_input_message(message):
                nonlocal last_message_time, buttons_held
                last_message_time = time.monotonic()
                try:
                    buttons = json.loads(message)
                except (TypeError, ValueError):
                    return
                if isinstance(buttons, list):
                    set_held_buttons(buttons)
                    buttons_held = len(buttons) > 0

            # The client repeats its current input state every second. Some browsers do not
            # tell us when a tab is closed, in which case it would take ~30 seconds for the
            # connection to time out. So if the client has gone quiet for a few seconds, we
            # assume that it has gone away and release any buttons that it held down.
            async def release_buttons_if_client_is_gone():
                nonlocal buttons_held
                while True:
                    await asyncio.sleep(0.5)
                    if buttons_held and time.monotonic() - last_message_time > 3:
                        set_held_buttons([])
                        buttons_held = False

            watchdog = asyncio.ensure_future(release_buttons_if_client_is_gone())

            # This also gets called if the connection fails or the client goes away, so
            # this makes sure that no buttons remain held down in that case.
            @channel.on("close")
            def on_input_close():
                watchdog.cancel()
                set_held_buttons([])

        else:

            @channel.on("message")
            def on_message(message):
                if isinstance(message, str) and message.startswith("ping"):
                    channel.send("pong" + message[4:])

    @connection.on("connectionstatechange")
    async def on_connection_state_change():
        if connection.connectionState in ("failed", "closed"):
            await connection.close()
            rtc_connections.pop(connection_id, None)
            stop_streams_if_unused()

    if emu_video is None:
        emu_video = EmuVideo()

    if emu_audio is None:
        emu_audio = EmuAudio()

    # Video is not buffered so that a slow client always gets the most recent frame
    # rather than lagging further and further behind. Audio needs to be buffered because
    # dropping parts of it would be audible.
    connection.addTrack(relay.subscribe(emu_video, buffered=False))
    connection.addTrack(relay.subscribe(emu_audio))

    try:
        await connection.setRemoteDescription(offer)
        answer = await connection.createAnswer()
        await connection.setLocalDescription(answer)
    except Exception:
        await connection.close()
        rtc_connections.pop(connection_id, None)
        stop_streams_if_unused()
        raise

    return {"id": connection_id, "sdp": connection.localDescription.sdp, "type": connection.localDescription.type}


async def close_connections(connection_ids: list[str]) -> list[str]:
    """
    Closes connections to browsers. This also closes their input data channels, which
    releases any buttons they held down.

    :param connection_ids: IDs of the connections to close, as returned by `answer_offer()`.
                           IDs of connections that do not exist (anymore) are ignored.
    :return: IDs of the connections that have actually been closed.
    """
    connections = {}
    for connection_id in connection_ids:
        if connection_id in rtc_connections:
            connections[connection_id] = rtc_connections.pop(connection_id)

    await asyncio.gather(*(connection.close() for connection in connections.values()))
    stop_streams_if_unused()

    return list(connections)


async def close_all_connections() -> list[str]:
    """
    Closes the connections to all browsers.

    :return: IDs of the connections that have been closed.
    """
    return await close_connections(list(rtc_connections))
