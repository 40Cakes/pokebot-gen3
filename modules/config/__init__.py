"""Module for managing and accessing configuration."""

from pathlib import Path

from confz import BaseConfig, FileSource
from ruamel.yaml import YAML

from modules import exceptions
from modules.runtime import get_base_path
from modules.config.schemas_v1 import Battle, CatchBlock, Cheats, Discord, Keys, Logging, OBS, ProfileMetadata

# Defines which class attributes of the Config class are meant to hold required configuration data.
CONFIG_ATTRS = {
    "battle",
    "catch_block",
    "cheats",
    "discord",
    "keys",
    "logging",
    "obs",
}


class Config:
    """Initializes a config directory and provides access to the different settings."""

    def __init__(self, config_dir: str | Path | None = None, is_profile: bool = False, strict: bool = False) -> None:
        """Initialize the configuration folder, loading all config files.

        :param config_dir: Config directory to load during initialization.
        :param is_profile: Whether profile files are expected in this directory.
        :param strict: Whether to allow files to be missing.
        """
        self.battle: Battle = Battle()
        self.config_dir = get_base_path() / "profiles" if not config_dir else Path(config_dir)
        self.catch_block: CatchBlock = CatchBlock()
        self.cheats: Cheats = Cheats()
        self.discord: Discord = Discord()
        self.is_profile = is_profile
        self.keys: Keys = Keys()
        self.loaded = False
        self.logging: Logging = Logging()
        self.metadata: ProfileMetadata | None = None
        self.obs: OBS = OBS()
        self.load(strict=strict)

    def load(self, config_dir: str | Path | None = None, strict: bool = True):
        """Load the configuration files in the config_dir.

        :param config_dir: New config dir to load.
        :param strict: Whether all files must be present in the directory.
        """
        if config_dir:
            self.config_dir = config_dir

        for attr in CONFIG_ATTRS:
            self.reload_file(attr, strict=strict)
        if self.is_profile:
            file_path = self.config_dir / ProfileMetadata.filename
            self.metadata = load_config_file(file_path, ProfileMetadata, strict=True)
        self.loaded = True

    def save(self, config_dir: str | Path | None = None, strict: bool = True):
        """Saves currently loaded configuration into files inside config_dir.

        :param config_dir: New config dir to save to.
        :param strict: Whether to allow overwriting files or creating missing directories.
        """
        if config_dir:
            self.config_dir = config_dir

        for attr in CONFIG_ATTRS:
            self.save_file(attr, strict=strict)
        if self.is_profile:
            self.save_file("metadata", strict=strict)

    def reload_file(self, attr: str, strict: bool = False) -> None:
        """Reload a specific configuration file, using the same source.

        :param attr: The instance attribute that holds the config file to load.
        :param strict: Whether all files must be present in the directory.
        """

        config_inst = getattr(self, attr, None)
        if not isinstance(config_inst, BaseConfig):
            raise exceptions.PrettyValueError(f"Config.{attr} is not a valid configuration to load.")
        file_path = self.config_dir / config_inst.filename
        config_inst = load_config_file(file_path, config_inst.__class__, strict=strict)
        if config_inst:
            setattr(self, attr, config_inst)

    def save_file(self, attr: str, strict: bool = False) -> None:
        """Save a specific configuration file, using the same source.

        :param attr: The instance attribute that holds the config file to save.
        :param strict: Whether all files must be present in the directory.
        """

        config_inst = getattr(self, attr, None)
        if not isinstance(config_inst, BaseConfig):
            raise exceptions.PrettyValueError(f"Config.{attr} is not a valid configuration to save.")
        save_config_file(self.config_dir, config_inst, strict=strict)


def load_config_file(file_path: Path, config_cls: type[BaseConfig], strict: bool = False) -> BaseConfig | None:
    """Helper to load files from a path without manually creating the sources.

    :param file_path: The path to the file to load.
    :param config_cls: Class to instance from the specified path.
    :param strict: Whether to raise an exception if the file is missing.
    """
    if not file_path.is_file():
        if strict:
            raise exceptions.CriticalFileMissing(file_path)
        config_inst = None
    else:
        sources = [FileSource(file_path)]
        config_inst = config_cls(config_sources=sources)
    return config_inst


def save_config_file(config_dir: Path, config_inst: BaseConfig, strict: bool = False) -> None:
    """Helper to save config data from a model into a config directory.

    :param config_dir: The directory to store the file into.
    :param config_inst: Config instance to save.
        :param strict: Whether to allow overwriting files or creating missing directories.
    """
    if not config_dir.is_dir():
        if strict:
            raise exceptions.CriticalDirectoryMissing(config_dir)
        config_dir.mkdir()
    if not isinstance(config_inst, BaseConfig):
        raise exceptions.PrettyValueError(f"The provided config is not a valid config instance.")
    config_file = config_dir / config_inst.filename
    if strict and config_file.is_file():
        raise exceptions.PrettyValueError(f"The file {config_file} already exists. Refusing to overwrite it.")
    yaml = YAML()
    yaml.allow_unicode = False
    yaml.dump(config_inst.model_dump(), config_dir / config_inst.filename)
