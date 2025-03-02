🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 💀 Using unsupported ROMs 💀

> [!CAUTION]
> Even if you follow these instructions, it's possible (and likely) that unsupported
> (modified) ROMs will **not work at all**, or that at least **some features** of the bot
> will be **broken**.
> 
> **Do not ask for support on GitHub or Discord if you are using this option!**  
> We cannot help you with modified game ROMs.

By default, the bot will only work with ROMs that match original retail cartridges of
the mainline Gen3 games (Ruby, Sapphire, Emerald, FireRed, LeafGreen.)

Any modifications to these ROMs, or read errors while dumping the cartridge, will lead
to the bot not recognising it as a Pokémon game.

If you are **really sure** about it, you can configure the bot to accept additional
ROM files.


## How to whitelist one or more ROM files

1. In the `profiles/` directory, create a new text file called `extra_allowed_roms.txt`.
2. Open this file in Notepad or some text editor of your choice.
3. Paste the SHA1 file hash (see below) or the file name of the ROM. Each hash/file name must be on a
   separate line without any spaces or tabs before/after.
4. Save the file and restart the bot.


## How to find the file hash for a ROM

The SHA1 hash of a ROM can be calculated with any of the following methods:

- [ROM Hasher](https://www.romhacking.net/utilities/1002/)
- Windows PowerShell: `Get-FileHash 'rom_name.gba' -Algorithm SHA1`
- Linux: `sha1sum 'rom_name.gba'`
