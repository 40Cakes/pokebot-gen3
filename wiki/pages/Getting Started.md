🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# ❓ Getting Started

## Supported Operating Systems

<img src="../images/os_windows.png" alt="Windows" style="max-width: 80px"> <img src="../images/os_apple.png" alt="MacOS" style="max-width: 80px"> <img src="../images/os_ubuntu.png" alt="Ubuntu" style="max-width: 80px"> <img src="../images/os_debian.png" alt="Debian" style="max-width: 80px"> <img src="../images/os_pop.png" alt="PopOS" style="max-width: 80px"> <img src="../images/os_arch.png" alt="Arch Linux" style="max-width: 80px">

- Windows
- MacOS
- Linux, tested and confirmed working on the following distros:
  - Ubuntu 23.04, 23.10
  - Debian 12
  - Pop!_OS 22.04 LTS
  - Arch Linux

## Requirements
### Windows
- [Python 3.12](https://www.python.org/downloads/windows/) **Windows installer 64-bit**
  - Tick `Add Python to PATH` when installing Python

### MacOS
- [Python 3.12](https://www.python.org/downloads/macos/) **macOS 64-bit universal2 installer** or `brew install python@3.12`
- mGBA 0.10.x `brew install mgba`

Note: `brew` requires [Homebrew](https://brew.sh/) to be installed.

### Linux
- [Python 3.12](https://www.python.org/downloads/source/) or `sudo apt install python3.12`
- Install the following packages with `apt` or appropriate package manager: `sudo apt install python3-distutils python3-tk libmgba0.10 portaudio19-dev`
- If `libmgba0.10` is not available on your distro, you can manually install the [mGBA 0.10.x .deb package](https://mgba.io/downloads.html) which includes `libmgba0.10`

## Download the Bot
### Stable Releases
Visit the [releases](https://github.com/40Cakes/pokebot-gen3/releases) page for the latest stable releases, download the **pokebot-vX.X.X.zip** file.

The bot has an auto-updater that will check for new stable releases, once a day.

### Dev Releases
To download the latest dev releases, go to the top of the repo page > click the green **Code** button > **Download ZIP**.

Alternatively, if you'd like to be able to easily pull the latest dev releases, use git:
- Install [GitHub Desktop](https://desktop.github.com/) (you don't need an account)
- Click **Clone a repository from the Internet...**
- Use repository URL `https://github.com/40Cakes/pokebot-gen3.git` and choose a save location on your PC
- Click **Clone**
- Any time there's a new update, you can pull the latest changes by clicking **Fetch origin**, then **Pull origin**

### Optional
- [Windows Terminal](https://github.com/microsoft/terminal/releases) - recommended for full 🌈<span style="color:#FF0000">c</span><span style="color:#FF7F00">o</span><span style="color:#FFFF00">l</span><span style="color:#00FF00">o</span><span style="color:#00FFFF">u</span><span style="color:#CF9FFF">r</span>🌈 and  ✨emoji support✨ in the console output
- [Notepad++](https://notepad-plus-plus.org/) - recommended for syntax highlighting while editing `.yml` config files

### Use a `venv` (optional)
If you're using Python for any other projects, it is **highly recommended** to use a virtual environment (`venv`) to isolate these packages from your base environment.

Once Python is installed, set up a `venv`, open a shell in the bot directory and enter the following command:

`python -m venv .`

A `venv` may be “activated” using a script in its binary directory (`bin` on POSIX; `Scripts` on Windows). This will prepend that directory to your PATH, so that running python will invoke the environment’s Python interpreter and you can run installed scripts without having to use their full path. The invocation of the activation script is platform-specific (`<venv>` must be replaced by the path to the directory containing the virtual environment):

| Platform | Shell                                         | Command to activate virtual environment                                                                                                       |
|----------|-----------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| POSIX    | bash/zsh<br/>fish<br/>csh/tcsh<br/>PowerShell | `$ source <venv>/bin/activate`<br/>`$ source <venv>/bin/activate.fish`<br/>`$ source <venv>/bin/activate.csh`<br/>`$ <venv>/bin/Activate.ps1` |
| Windows  | cmd.exe<br/>PowerShell                        | `C:\> <venv>\Scripts\activate.bat`<br/>`PS C:\> <venv>\Scripts\Activate.ps1`                                                                  |

Once activated, run the bot (your shell should show `(venv)` if activated correctly):

`(venv)$ python ./pokebot.py` (POSIX)

`(venv) PS C:\> python ./pokebot.py` (Windows)

## Run the Bot
- Place some **official** Pokémon .gba ROMs into the `roms/` folder
- Double click `pokebot.py` or run `python pokebot.py` in a terminal and follow the on-screen steps to create and/or select a profile

The bot ships with the default mGBA input mapping, see [here](Configuration%20-%20Emulator%20Input%20Mapping.md) for the default mapping, or customise them to your preference.

The bot will pause once a shiny is encountered. You **must** ensure you are able to escape battle **100% of the time**, otherwise the bot will get stuck. Auto-catching and other features will be added in due time.
If you have a save from mGBA that you'd like to import and use with the bot, then you will need to import the save state.

## Import a Save
- In mGBA (standalone), run a game and load into the save file
- **File** > **Save State File...** > **Save**
- Double click `pokebot.py` or run `python pokebot.py` in a terminal > type a profile **name** > click **Load Existing Save**
- Open the save state file you just saved
- A new bot profile will be created in the `profiles/` folder, and launched

## Tips/Tricks
- Set in-game **TEXT SPEED** to **FAST**
- Set in-game **BATTLE SCENE** to **OFF**
- Utilise [repel tricks](https://bulbapedia.bulbagarden.net/wiki/Appendix:Repel_trick) to boost encounter rates of target Pokémon
- Using modes [Spin](Mode%20-%20Spin.md) or [Bunny Hop](Mode%20-%20Acro%20Bike%20Bunny%20Hop.md), repels will become effectively infinite + steps won't be counted in Safari Zone
- Use a lead Pokémon with encounter rate boosting [abilities](https://bulbapedia.bulbagarden.net/wiki/Category:Abilities_that_affect_appearance_of_wild_Pok%C3%A9mon), such as **[Illuminate](https://bulbapedia.bulbagarden.net/wiki/Illuminate_(Ability))**
- Use a lead Pokémon with a [short cry](https://docs.google.com/spreadsheets/d/1rmtNdlIXiif1Sz20i-9mfhFdoqb1VnAOIntlr3tnPeU)
- Use a lead Pokémon with a single character nickname
- Don't use a shiny lead Pokémon (shiny animation takes a few frames at the start of every battle)

## Debugging (advanced)

The bot supports auto-starting a profile and can also be launched into a "debug" mode which will open an extra pane next to the emulator to aid bot development.

The debug tabs includes information such as currently running game tasks and callbacks, emulator inputs, as well as information about recent battles, player status, current map, daycare and event flags.

```
positional arguments:
  profile               Profile to initialize. Otherwise, the profile selection menu will appear.

options:
  -h, --help            show this help message and exit
  -m {MODE_NAME}, --bot-mode {MODE_NAME}
                        Initial bot mode (default: Manual)
  -s {0,1,2,3,4}, --emulation-speed {0,1,2,3,4}
                        Initial emulation speed (0 for unthrottled; default: 1)
  -nv, --no-video       Turn off video output by default
  -na, --no-audio       Turn off audio output by default
  -t, --always-on-top   Keep the bot window always on top of other windows
  -d, --debug           Enable extra debug options and a debug menu
```

Use environment variable `POKEBOT_UNTHEMED=1` with debug mode as `ttkthemes` causes major lag with complex UIs.