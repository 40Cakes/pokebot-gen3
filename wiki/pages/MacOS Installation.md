# MacOS Installation Guide

<img src="../images/os_apple.png" alt="MacOS" style="max-width: 80px">

> All of these instructions are assuming you are using Apple Silicon.

#### Install Brew

Navigate to [HomeBrew](https://brew.sh/)'s website and use the command provided.

#### Update and upgrade brew

`brew update && brew upgrade`

#### Install pyenv, and mgba

`brew install pyenv`
`brew install mgba`

#### Pokébot Folder

Download the latest version of the Pokébot (either release or dev), and move it to the directory you want to store it in.

#### Terminal

Close your existing terminal, and open a new one.
Create a `.zshrc` file for your user by running:
`touch ~/.zshrc`

#### .zshrc

Edit this new file with textedit, nano, vim, or a text editor of your choice.
If using a GUI editor, ensure you save it as **Plain Text** format.
Insert the following text into .zshrc file:

```bash
eval "$(pyenv init -)"
if which pyenv-virtualenv-init > /dev/null; then eval "$(pyenv virtualenv-init -))"; fi
```

Close and re-open the terminal again.

#### Install tcl/tk version 8.6.16 for your local user

Unfortuantely, Brew does not have 8.6.16 (at the time of writing this), so we have to do this ourselves.

- Make a new directory `mkdir ~/local-tcltk-src`
- Download tcl 8.6.16 source and tk 8.6.16 source files - the `.tar.gz` files for both from https://www.tcl-lang.org/software/tcltk/download.html
- Move both files to the `~/local-tcltk-src` folder we just created.
- Navigate to ~/local-tcltk-src and run the following commands:
  `tar xzf tcl8.6.16-src.tar.gz`
  `tar xzf tcl8.6.16-src.tar.gz`
- You should now have to files: `tcl8.6.16` and `tk8.6.16`
- Create a dedicated install directory (aka 'Prefix') so Tcl/Tk does not interfere with system-wide or homebrew versions.
- In a new terminal, `mkdir -p ~/local-tcltk`
- Navigate to `~/local-tcltk-src/tcl8.6.16/unix` in the terminal, and enter:

```bash
./configure --prefix="$HOME/local-tcltk" \
            --enable-threads \
            --enable-64bit
make
make install
```

- Navigate to `~/local-tcltk-src/tck8.6.16/unix` in the terminal, and enter:

```bash
./configure --prefix="$HOME/local-tcltk" \
            --enable-aqua \
            --without-x \
            --with-tcl="$HOME/local-tcltk/lib" \
            --enable-threads \
            --enable-64bit
make
make install
```

- Close and re-open the terminal

#### Export linker/compiler flags, so Python build process uses your local Tcl/Tk:

```bash
export LDFLAGS="-L$HOME/local-tcltk/lib"
export CPPFLAGS="-I$HOME/local-tcltk/include"
export PKG_CONFIG_PATH="$HOME/local-tcltk/lib/pkgconfig"
export TCL_LIBRARY="$HOME/local-tcltk/lib/tcl8.6"
export TK_LIBRARY="$HOME/local-tcltk/lib/tk8.6"
```

#### Use PYTHON_CONFIGURE_OPTS when installing via pyenv

```bash
env \
PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I$HOME/local-tcltk/inc
lude' \
--with-tcltk-libs='-L$HOME/local-tcltk/lib -ltcl8.6 -ltk8.6'" \
pyenv install 3.12.8
```

#### Verify dependencies:

```bash
pyenv shell 3.12.8
python -V
```

- You should see `3.12.8`

```bash
python -m tkinter
```

- You should see a small window open

#### Create your pyenv and activate it

> Replace `myproject` with anything you like such as `pokebot`

```bash
pyenv virtualenv 3.12.8 myproject
pyenv local myproject
```

#### Finished!
Now your prompt should start with `(myproject)` (or whatever you named it).
If it does, you are safe to go ahead and run the command:
```python
python /path-to/pokebot-gen3/pokebot.py
```

You should now see the bot window open as expected.

#### Credits
Thanks to **.orch** in the discord for figuring these steps out and creating a guide for future MacOS users!