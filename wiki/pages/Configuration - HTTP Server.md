🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 📡 HTTP Server Config

[`profiles/http.yml`](../../modules/config/templates/http.yml)

This configuration can be used to drive custom stream overlays and web UIs.

Note that if you enable the HTTP server, you can only run one instance of the bot at once. Or rather, you can run
multiple instances but only the first one will have its HTTP server running -- while the rest will show an error message
on startup.

## HTTP server
The `http_server` config will enable a Flask HTTP server, which can be used to retrieve data and drive stream overlays.

`enable` - toggle HTTP server on/off

`ip` - IP address for HTTP server to listen on

`port` - TCP port for HTTP server to listen on
- Port must be unique for each bot instance

### HTTP Endpoints
The bot has a built-in HTTP server that can serve lots of data about the running emulator the current profile.

It also allows remote-controlling the bot.

The following pages are available if the HTTP server is enabled:
- Test/example UI: [http://127.0.0.1:8888/](http://127.0.0.1:8888/)
- Swagger UI (API Documentation): [http://127.0.0.1:8888/docs/](http://127.0.0.1:8888/docs/)

![image](../images/http_api.png)
