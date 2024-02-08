🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🌍 Supported Games and Languages

**Do NOT request or distribute ROMs in the Discord under any circumstances! You will be banned from the server.**

Variations of games, languages and revisions may have different memory offsets, there will be a table of supported/tested variations under each bot mode listed on this wiki.

- ✅ Supported (tested)
- 🟨 Supported (not tested)
- ❌ Not supported

It is highly recommended to use English ROMs for now as English is typically prioritised during development, however the goal is to eventually support all languages, please be patient if you find your language is not supported.

ROM hacks will likely not work, and are ❌ **not supported** or planned to be supported! Please do not seek support or complain if you find that your ROM hack does not work with the bot.

The ROMs in the `roms/` folder are checked and verified against a list of all known official gen3 game hashes. If you **really** want to test a ROM hack with the bot, you must add the SHA1 hash of the ROM to [`modules/roms.py`](https://github.com/40Cakes/pokebot-gen3/blob/main/modules/roms.py).

The SHA1 hash of a ROM can be calculated with any of the following methods:
- [ROM Hasher](https://www.romhacking.net/utilities/1002/)
- Windows Powershell: `Get-FileHash 'rom_name.gba' -Algorithm SHA1`
- Linux: `sha1sum 'rom_name.gba'`

List of ROM hashes that the bot will accept:

| ROM Filename | SHA1 Hash |
| --- | --- |
| Pokémon - Saphir-Edition (Germany).gba | `5a087835009d552d4c5c1f96be3be3206e378153` |
| Pokémon - Saphir-Edition (Germany) (Rev 1).gba | `7e6e034f9cdca6d2c4a270fdb50a94def5883d17` |
| Pokémon - Sapphire Version (USA).gba | `3ccbbd45f8553c36463f13b938e833f652b793e4` |
| Pokémon - Sapphire Version (Europe) (Rev 1).gba | `4722efb8cd45772ca32555b98fd3b9719f8e60a9` |
| Pokémon - Sapphire Version (USA, Europe) (Rev 2).gba | `89b45fb172e6b55d51fc0e61989775187f6fe63c` |
| Pokémon - Version Saphir (France).gba | `c269b5692b2d0e5800ba1ddf117fda95ac648634` |
| Pokémon - Version Saphir (France) (Rev 1).gba | `860e93f5ea44f4278132f6c1ee5650d07b852fd8` |
| Pokémon - Versione Zaffiro (Italy).gba | `f729dd571fb2c09e72c5c1d68fe0a21e72713d34` |
| Pokémon - Versione Zaffiro (Italy) (Rev 1).gba | `73edf67b9b82ff12795622dca412733755d2c0fe` |
| Pocket Monsters - Sapphire (Japan).gba | `3233342c2f3087e6ffe6c1791cd5867db07df842` |
| Pocket Monsters - Sapphire (Japan) (Rev 1).gba | `01f509671445965236ac4c6b5a354fe2f1e69f13` |
| Pokémon - Edicion Zafiro (Spain).gba | `3a6489189e581c4b29914071b79207883b8c16d8` |
| Pokémon - Edicion Zafiro (Spain) (Rev 1).gba | `0fe9ad1e602e2fafa090aee25e43d6980625173c` |
| Pokémon - Rubin-Edition (Germany).gba | `1c2a53332382e14dab8815e3a6dd81ad89534050` |
| Pokémon - Rubin-Edition (Germany) (Rev 1).gba | `424740be1fc67a5ddb954794443646e6aeee2c1b` |
| Pokémon - Ruby Version (USA).gba | `f28b6ffc97847e94a6c21a63cacf633ee5c8df1e` |
| Pokémon - Ruby Version (Europe) (Rev 1).gba | `610b96a9c9a7d03d2bafb655e7560ccff1a6d894` |
| Pokémon - Ruby Version (USA, Europe) (Rev 2).gba | `5b64eacf892920518db4ec664e62a086dd5f5bc8` |
| Pokémon - Version Rubis (France).gba | `a6ee94202bec0641c55d242757e84dc89336d4cb` |
| Pokémon - Version Rubis (France) (Rev 1).gba | `ba888dfba231a231cbd60fe228e894b54fb1ed79` |
| Pokémon - Versione Rubino (Italy).gba | `2b3134224392f58da00f802faa1bf4b5cf6270be` |
| Pokémon - Versione Rubino (Italy) (Rev 1).gba | `015a5d380afe316a2a6fcc561798ebff9dfb3009` |
| Pocket Monsters - Ruby (Japan).gba | `5c5e546720300b99ae45d2aa35c646c8b8ff5c56` |
| Pocket Monsters - Ruby (Japan) (Rev 1).gba | `971e0d670a95e5b32240b2deed20405b8daddf47` |
| Pokémon - Edicion Rubi (Spain).gba | `1f49f7289253dcbfecbc4c5ba3e67aa0652ec83c` |
| Pokémon - Edicion Rubi (Spain) (Rev 1).gba | `9ac73481d7f5d150a018309bba91d185ce99fb7c` |
| Pokémon - Smaragd-Edition (Germany).gba | `61c2eb2b380b1a75f0c94b767a2d4c26cd7ce4e3` |
| Pokémon - Emerald Version (USA, Europe).gba | `f3ae088181bf583e55daf962a92bb46f4f1d07b7` |
| Pokémon - Version Emeraude (France).gba | `ca666651374d89ca439007bed54d839eb7bd14d0` |
| Pokémon - Versione Smeraldo (Italy).gba | `1692db322400c3141c5de2db38469913ceb1f4d4` |
| Pocket Monsters - Emerald (Japan).gba | `d7cf8f156ba9c455d164e1ea780a6bf1945465c2` |
| Pokémon - Edicion Esmeralda (Spain).gba | `fe1558a3dcb0360ab558969e09b690888b846dd9` |
| Pokémon - Blattgruene Edition (Germany).gba | `0802d1fb185ee3ed48d9a22afb25e66424076dac` |
| Pokémon - LeafGreen Version (USA).gba | `574fa542ffebb14be69902d1d36f1ec0a4afd71e` |
| Pokémon - LeafGreen Version (USA, Europe) (Rev 1).gba | `7862c67bdecbe21d1d69ce082ce34327e1c6ed5e` |
| Pokémon - Version Vert Feuille (France).gba | `4b5758c14d0a07b70ef3ef0bd7fa5e7ce6978672` |
| Pokémon - Versione Verde Foglia (Italy).gba | `a1dfea1493d26d1f024be8ba1de3d193fcfc651e` |
| Pocket Monsters - LeafGreen (Japan).gba | `5946f1b59e8d71cc61249661464d864185c92a5f` |
| Pocket Monsters - LeafGreen (Japan) (Rev 1).gba | `de9d5a844f9bfb63a4448cccd4a2d186ecf455c3` |
| Pokémon - Edicion Verde Hoja (Spain).gba | `f9ebee5d228cb695f18ef2ced41630a09fa9eb05` |
| Pokémon - Feuerrote Edition (Germany).gba | `18a3758ceeef2c77b315144be2c3910d6f1f69fe` |
| Pokémon - FireRed Version (USA).gba | `41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc` |
| Pokémon - FireRed Version (USA, Europe) (Rev 1).gba | `dd5945db9b930750cb39d00c84da8571feebf417` |
| Pokémon - Version Rouge Feu (France).gba | `fc663907256f06a3a09e2d6b967bc9af4919f111` |
| Pokémon - Versione Rosso Fuoco (Italy).gba | `66a9d415205321376b4318534c0dce5f69d28362` |
| Pocket Monsters - FireRed (Japan).gba | `04139887b6cd8f53269aca098295b006ddba6cfe` |
| Pocket Monsters - FireRed (Japan) (Rev 1).gba | `7c7107b87c3ccf6e3dbceb9cf80ceeffb25a1857` |
| Pokémon - Edicion Rojo Fuego (Spain).gba | `ab8f6bfe0ccdaf41188cd015c8c74c314d02296a` |