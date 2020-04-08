# MIDI Websocket server

Python Websocket server to facilitate two-way communication with all connected MIDI devices.

Features:

- Broadcasting all `NOTE ON` and `NOTE OFF` MIDI signals from all MIDI devices to all clients listening via websocket.
- Playing received `NOTE ON` and `NOTE OFF` MIDI signals from connected clients to specific MIDI device.
- Discovery of new devices when they are plugged in. Changes to device list is broadcasted to all connected clients.

The server is designed to run on a Raspberry Pi with a MIDI keyboard plugged in via USB.

Powered by [aaugustin/websockets](https://github.com/aaugustin/websockets) and [SpotlightKid/python-rtmidi](https://github.com/SpotlightKid/python-rtmidi).
