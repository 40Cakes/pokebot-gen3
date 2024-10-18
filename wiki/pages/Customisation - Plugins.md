🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🧩 Plugins

If you know Python and want to customise the behaviour of the bot, you can create a plugin.

Plugins are little scripts that get called for specific events during the game (such as a
battle starting, an egg hatching, etc.) Take a look at
[modules/plugin_interface.py](../../modules/plugin_interface.py) for a list of events that
a plugin may be called for.


## Creating a plugin

To make a plugin, create a Python file inside the `plugins/` directory. This must have the
`.py` file extension and it must be placed directly in the `plugins/` directory, not in a
subdirectory.

In this file, create a class that inherits from `BotPlugin`. So the most basic implementation
of a plugin would be:

```python
from modules.plugin_interface import BotPlugin

class MyFirstPlugin(BotPlugin):
    pass
```

Of course, this doesn't do anything yet. You can choose some method from the parent `BotPlugin`
class to overwrite (see [modules/plugin_interface.py](../../modules/plugin_interface.py) for
a list.)


## Why write a plugin and not just edit the bot's code?

The `plugins/` directory is excluded from the Git repository and will also not be touched by
the automatic updater. So code in that directory won't fall victim to future updates --
whereas if you edit the bot's code directly, this might get removed again when the bot updates
and you're not careful.


## Example plugins

While not meant to be just an example, there are some features that use the bot's plugin
infrastructure to work.

You can find those 'default plugins' in [modules/built_in_plugins/](../../modules/built_in_plugins/).
