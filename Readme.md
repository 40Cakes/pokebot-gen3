# PokéBot Gen3 for mGBA

Re-write of [pokebot-bizhawk](https://github.com/40Cakes/pokebot-bizhawk) to work in mGBA using direct memory reads (no more image detection dependencies).

This is a *VERY early* release of this bot so minimal support will be provided in Discord, if you do encounter any issues, use the channel [#bot-support-mgba🧪](https://discord.com/channels/1057088810950860850/1139190426834833528)

⚠ Use this bot at your own risk! The bot directly writes to mGBA memory, there is a good chance mGBA may crash while using this version.

The bot is hard-coded to spin on the spot and exit once a shiny is encountered. You must ensure you are able to escape battle 100% of the time, otherwise the bot will get stuck. There is currently no UI, auto-catching, encounter logging etc. It is as bare-bones as it gets, these features will be added in due time.

1. Run `requirements.py` to install required modules.
2. Run `bot.py`, then click on an mGBA instance to attach the bot to it.