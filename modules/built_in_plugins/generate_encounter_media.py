import os
import time
from pathlib import Path
from threading import Thread
from typing import Generator, TYPE_CHECKING

import PIL.Image

from modules.context import context
from modules.encounter import EncounterValue
from modules.modes import BotListener, BotMode, FrameInfo
from modules.plugin_interface import BotPlugin
from modules.tcg_card import get_tcg_card_file_name, generate_tcg_card

if TYPE_CHECKING:
    from modules.battle_state import BattleOutcome
    from modules.encounter import EncounterInfo


class GifGeneratorListener(BotListener):
    def __init__(self):
        self._frames: list[PIL.Image.Image] = []

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if len(self._frames) < 1000:
            self._frames.append(context.emulator.get_screenshot())

    def save_gif(self, directory: Path, file_name: str):
        if len(self._frames) > 0:
            if not directory.exists():
                directory.mkdir(parents=True)

            # Repeat the last frame for a second so you can actually read the text
            extra_frames = self._frames[1:]
            for _ in range(60):
                extra_frames.append(self._frames[-1])

            # Closest to 60 fps we can get, as Pillow only seems to support 10ms steps.
            milliseconds_per_frame = 20
            self._frames[0].save(
                directory / (file_name + ".tmp"),
                format="GIF",
                append_images=extra_frames,
                save_all=True,
                duration=milliseconds_per_frame,
                loop=0,
            )
            self._frames.clear()

            os.replace(directory / (file_name + ".tmp"), directory / file_name)


class GenerateEncounterMediaPlugin(BotPlugin):
    def __init__(self):
        self._listener: GifGeneratorListener | None = None

    def on_battle_started(self, encounter: "EncounterInfo | None") -> Generator | None:
        if self._listener is not None:
            context.bot_listeners.remove(self._listener)
            self._listener = None

        if context.config.logging.shiny_gifs:
            if encounter is not None and encounter.value is EncounterValue.Shiny:
                self._listener = GifGeneratorListener()
                context.bot_listeners.append(self._listener)

        return None

    def on_wild_encounter_visible(self, encounter: "EncounterInfo") -> Generator | None:
        # Finalise and save encounter GIF
        if self._listener is not None:
            gif_dir = context.profile.path / "screenshots" / "gifs"
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            file_name = f"{timestamp}_{encounter.pokemon.species_name_for_stats}.gif"

            # Set the GIF's path so that other plugins can use it.
            encounter.gif_path = gif_dir / file_name

            Thread(
                target=self._listener.save_gif,
                args=(
                    gif_dir,
                    file_name,
                ),
            ).start()
            context.bot_listeners.remove(self._listener)
            self._listener = None

        # Generate TCG card
        if context.config.logging.tcg_cards and encounter.value is EncounterValue.Shiny:
            cards_dir = context.profile.path / "screenshots" / "cards"
            file_name = get_tcg_card_file_name(encounter.pokemon)

            # Set the TCG card's path so that other plugins can use it.
            encounter.tcg_card_path = cards_dir / file_name

            Thread(target=generate_tcg_card, args=(encounter.pokemon.data, encounter.pokemon.location_met)).start()

        return None

    def on_battle_ended(self, outcome: "BattleOutcome") -> Generator | None:
        if self._listener is not None:
            context.bot_listeners.remove(self._listener)
            self._listener = None

        return None

    def on_egg_starting_to_hatch(self, hatching_pokemon: "EncounterInfo") -> Generator | None:
        return self.on_battle_started(hatching_pokemon)

    def on_egg_hatched(self, hatched_pokemon: "EncounterInfo") -> Generator | None:
        return self.on_wild_encounter_visible(hatched_pokemon)
