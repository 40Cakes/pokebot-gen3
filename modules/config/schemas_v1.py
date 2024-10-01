"""Contains default schemas for configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from confz import BaseConfig
from pydantic import ConfigDict, Field, field_validator
from pydantic.types import Annotated, ClassVar, NonNegativeInt, PositiveInt


class Battle(BaseConfig):
    """Schema for the catch_block configuration."""

    filename: ClassVar = "battle.yml"
    auto_catch: bool = True
    save_after_catching: bool = False
    pickup: bool = True
    pickup_threshold: Annotated[int, Field(gt=0, lt=7)] = 1
    pickup_check_frequency: Annotated[int, Field(gt=0)] = 5
    hp_threshold: Annotated[float, Field(ge=0, le=100)] = 20
    lead_cannot_battle_action: Literal["stop", "flee", "rotate"] = "flee"
    faint_action: Literal["stop", "flee", "rotate"] = "flee"
    new_move: Literal["stop", "cancel", "learn_best"] = "stop"
    stop_evolution: bool = True
    switch_strategy: Literal["first_available", "lowest_level"] = "first_available"
    lead_mon_balance_levels: bool = False
    banned_moves: list[str] = [
        "None",
        # 2-turn
        "Bounce",
        "Dig",
        "Dive",
        "Fly",
        "Sky Attack",
        "Razor Wind",
        "Doom Desire",
        "Solar Beam",
        # Inconsistent
        "Fake Out",
        "False Swipe",
        "Nature Power",
        "Present",
        "Destiny Bond",
        "Wrap",
        "Snore",
        "Spit Up",
        "Bide",
        "Bind",
        "Counter",
        "Future Sight",
        "Mirror Coat",
        "Grudge",
        "Snatch",
        "Spite",
        "Curse",
        "Endeavor",
        "Revenge",
        "Assist",
        "Focus Punch",
        "Eruption",
        "Flail",
        # Ends battle
        "Roar",
        "Whirlwind",
        "Selfdestruct",
        "Perish Song",
        "Explosion",
        "Memento",
    ]
    avoided_pokemon: list[str] = []
    targeted_pokemon: list[str] = []


class CatchBlock(BaseConfig):
    """Schema for the catch_block configuration."""

    filename: ClassVar = "catch_block.yml"
    block_list: list[str] = ["MissingNo"]


class Cheats(BaseConfig):
    """Schema for the cheat configuration."""

    filename: ClassVar = "cheats.yml"
    random_soft_reset_rng: bool = False
    faster_pickup: bool = False


class Discord(BaseConfig):
    """Schema for the discord configuration."""

    filename: ClassVar = "discord.yml"
    rich_presence: bool = False
    iv_format: Literal["basic", "formatted"] = "formatted"
    delay: int = 0
    bot_id: str = "PokéBot Gen3"
    global_webhook_url: str = ""
    shiny_pokemon_encounter: DiscordWebhook = Field(default_factory=lambda: DiscordWebhook())
    pokemon_encounter_milestones: DiscordWebhook = Field(default_factory=lambda: DiscordWebhook(interval=10000))
    shiny_pokemon_encounter_milestones: DiscordWebhook = Field(default_factory=lambda: DiscordWebhook(interval=5))
    total_encounter_milestones: DiscordWebhook = Field(default_factory=lambda: DiscordWebhook(interval=25000))
    phase_summary: DiscordWebhook = Field(
        default_factory=lambda: DiscordWebhook(first_interval=8192, consequent_interval=5000)
    )
    anti_shiny_pokemon_encounter: DiscordWebhook = Field(default_factory=lambda: DiscordWebhook())
    custom_filter_pokemon_encounter: DiscordWebhook = Field(default_factory=lambda: DiscordWebhook())
    pickup: DiscordWebhook = Field(default_factory=lambda: DiscordWebhook(interval=10))
    tcg_cards: DiscordWebhook = Field(default_factory=lambda: DiscordWebhook())

    def is_anything_enabled(self) -> bool:
        return (
            self.rich_presence
            or self.shiny_pokemon_encounter.enable
            or self.pokemon_encounter_milestones.enable
            or self.shiny_pokemon_encounter_milestones.enable
            or self.total_encounter_milestones.enable
            or self.phase_summary.enable
            or self.anti_shiny_pokemon_encounter.enable
            or self.custom_filter_pokemon_encounter.enable
        )


class DiscordWebhook(BaseConfig):
    """Schema for the different webhooks sections contained in the Discord config."""

    # This allows `ping_id` to just be an integer, even though it is treated like a string later on.
    model_config = ConfigDict(coerce_numbers_to_str=True)

    enable: bool = False
    first_interval: PositiveInt | None = 0
    consequent_interval: PositiveInt | None = 0
    interval: PositiveInt = 0
    ping_mode: Literal["user", "role", None] = None
    ping_id: str | None = None
    webhook_url: str | None = None


class Keys(BaseConfig):
    """Schema for GBA key configuration."""

    filename: ClassVar = "keys.yml"
    gba: KeysGBA = Field(default_factory=lambda: KeysGBA())
    emulator: KeysEmulator = Field(default_factory=lambda: KeysEmulator())


class KeysEmulator(BaseConfig):
    """Schema for the emulator keys section in the Keys config."""

    zoom_in: str = "plus"
    zoom_out: str = "minus"
    toggle_manual: str = "Tab"
    toggle_video: str = "v"
    toggle_audio: str = "b"
    set_speed_1x: str = "1"
    set_speed_2x: str = "2"
    set_speed_3x: str = "3"
    set_speed_4x: str = "4"
    set_speed_8x: str = "5"
    set_speed_16x: str = "6"
    set_speed_32x: str = "7"
    set_speed_unthrottled: str = "0"
    reset: str = "Ctrl+R"
    reload_config: str = "Ctrl+C"
    exit: str = "Ctrl+Q"
    save_state: str = "Ctrl+S"
    load_state: str = "Ctrl+L"
    toggle_stepping_mode: str = "Ctrl+P"
    screenshot: str = "F12"


class KeysGBA(BaseConfig):
    """Schema for the GBA keys section in the Keys config."""

    Up: str = "Up"
    Down: str = "Down"
    Left: str = "Left"
    Right: str = "Right"
    A: str = "x"
    B: str = "z"
    L: str = "a"
    R: str = "s"
    Start: str = "Return"
    Select: str = "BackSpace"


class Logging(BaseConfig):
    """Schema for the logging configuration."""

    filename: ClassVar = "logging.yml"
    console: LoggingConsole = Field(default_factory=lambda: LoggingConsole())
    save_pk3: LoggingSavePK3 = Field(default_factory=lambda: LoggingSavePK3())
    log_encounters: bool = False
    desktop_notifications: bool = True
    shiny_gifs: bool = True
    tcg_cards: bool = True


class LoggingConsole(BaseConfig):
    """Schema for the console section in the Logging config."""

    encounter_data: Literal["verbose", "basic", "disable"] = "verbose"
    encounter_ivs: Literal["verbose", "basic", "disable"] = "verbose"
    encounter_moves: Literal["verbose", "basic", "disable"] = "disable"
    statistics: Literal["verbose", "basic", "disable"] = "verbose"


class LoggingSavePK3(BaseConfig):
    """Schema for the save_pk3 section in the Logging config."""

    all: bool = False
    shiny: bool = True
    custom: bool = True
    roamer: bool = True


class HTTP(BaseConfig):
    """Schema for the HTTP configuration."""

    filename: ClassVar = "http.yml"
    http_server: HTTPServer = Field(default_factory=lambda: HTTPServer())


class OBS(BaseConfig):
    """Schema for the OBS configuration."""

    filename: ClassVar = "obs.yml"
    discord_delay: NonNegativeInt = 0
    discord_webhook_url: str | None = None
    replay_buffer: bool = False
    replay_buffer_delay: NonNegativeInt = 0
    screenshot: bool = False
    shiny_delay: NonNegativeInt = 0
    obs_websocket: OBSWebsocket = Field(default_factory=lambda: OBSWebsocket())


class OBSWebsocket(BaseConfig):
    """Schema for the obs_websocket section in the OBS config."""

    host: str = "127.0.0.1"
    password: str = "password"
    port: Annotated[int, Field(gt=0, lt=65536)] = 4455


class HTTPServer(BaseConfig):
    """Schema for the http_server section in the HTTP config."""

    enable: bool = False
    ip: str = "127.0.0.1"
    port: Annotated[int, Field(gt=0, lt=65536)] = 8888


class ProfileMetadata(BaseConfig):
    """Schema for the metadata configuration file part of profiles."""

    filename: ClassVar = "metadata.yml"
    version: PositiveInt = 1
    rom: ProfileMetadataROM = Field(default_factory=lambda: ProfileMetadataROM())


class ProfileMetadataROM(BaseConfig):
    """Schema for the rom section of the metadata config."""

    file_name: str = ""
    game_code: str = ""
    revision: NonNegativeInt = 0
    language: Literal["E", "F", "D", "I", "J", "S"] = ""
