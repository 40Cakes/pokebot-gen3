# PokéBot Event Stream

Event streams ([server side events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#event_stream_format) (SSE)) are a way to receive continuous updates by the bot in JavaScript or any other client that is capable of handling `text/event-stream` content.

Note: Swagger UI does not support `text/event-stream`, use [Postman](https://www.postman.com/) for testing instead.

[Open example event stream page](/)

## How to use in JavaScript

[All modern browsers](https://caniuse.com/eventsource) have a built-in client for this data type.

Example:
```javascript
const connection = new EventSource("http://127.0.0.1:8888/stream_events?topic=...&topic=...");

connection.addEventListener("PerformanceData", event => handlePerformanceData(JSON.parse(event.data)));
connection.addEventListener("Opponent", ...);

function handlePerformanceData(data) {
    console.log(`FPS: ${data.fps}`);
}
```

## Subscribe to topics

For performance reasons, this endpoint requires you to specify which events you want to receive.
This allows much more efficient data transfers without the client needing to constantly poll the server.

To specify which topics you would like to receive, you need to provide **one or more** `topic=...` query parameters:

`/stream_events?topic=PerformanceData`  
or  
`/stream_events?topic=PerformanceData&topic=Opponent&topic=Party`

## Handle events

The JavaScript client acts as an event emitter, so you can just call its `addEventHandler()` function (see the example code above) to handle them.

The first argument is the event name (a list of which will follow below) and the second argument is a function that accepts the event.

See [MDN](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/message_event) for a description of the event object.

Note that while all our events are JSON-encoded, the `event.data` property is _a string_.
So you have to call `JSON.parse(event.data)` in order to get back the actual value/data object.

## Topics

This directory contains TypeScript declaration files that describe the structure of event payloads. See `modules/web/stream_events.d.ts`.

### Topic `Player`

This will send you a `Player` event whenever some basic data of the player changes, such as name, cash, coins, and the registered (select) item.

### Topic `Party`

This will send you a `Party` event whenever something about the player's party changes.

That is going to happen for every small change, such as a party Pokémon taking damage or its HP decreasing due to walking while poisoned.

### Topic `Pokedex`

This will notify you each time the Pokédex data (seen and owned species) changes.

The event is also called `Pokedex`.

### Topic `Opponent`

This will send you an `Opponent` event each time the opponent changes.

That is going to happen when a wild encounter/trainer battle starts, when the opponent switches Pokémon in a trainer battle, when the opposing Pokémon takes damage or uses a move (due to its PP decreasing) etc.

This event will also be fired when a battle _ends_, in which case the payload is `null`.

### Topic `GameState`

This will send you a `GameState` event whenever the in-game 'state' changes.

Game state is not something the game defines itself, but rather something the bot detects and then uses internally. There is no definite list of possible values as this might change regularly as bot development progresses.

### Topic `Map`

This will send you a `MapChange` event when the user _enters a new map_.

### Topic `MapTile`

This will send you a `MapTileChange` event whenever the user moves to a new tile.
The data is exactly the same as for the `MapChange` event, but you will receive this one much more frequently due to it being fired on each new tile.

If you subscribe to both the `Map` and `MapTile` topics, you will receive _both_ a `MapChange` and a `MapTileChange` event (with identical data) when the user enters a new map.

### Topic `LastEncounterLog`

This will send you the latest entry in the encounter log on every new encounter.

### Topic `LastShinyLog`

This will send you the latest entry in the shiny log on every new shiny encounter.

### Topic `BotMode`

This will send you a `BotMode` event each time the bot mode is changed.

### Topic `Message`

This will send you a `Message` event whenever the message displayed in the GUI
changes.

### Topic `EmulatorSettings`

This will send you one of the following events whenever that respective setting in the bot is changed:

- `EmulationSpeed`
- `AudioEnabled`
- `VideoEnabled`

### Topic `PerformanceData`

When subscribing to this topic, your client will receive an event every second containing some basic performance data (e.g. FPS, encounter rate, ...)

This event is also called `PerformanceData`.
