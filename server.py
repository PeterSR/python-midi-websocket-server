#!/usr/bin/env python

import asyncio
import json

import websockets
import rtmidi



class Hub():
    # https://gist.github.com/appeltel/fd3ddeeed6c330c7208502462639d2c9

    def __init__(self):
        self.subscriptions = set()

    def publish(self, message):
        for queue in self.subscriptions:
            queue.put_nowait(message)


class Subscription():

    def __init__(self, hub):
        self.hub = hub
        self.queue = asyncio.Queue()

    def __enter__(self):
        hub.subscriptions.add(self.queue)
        return self.queue

    def __exit__(self, type, value, traceback):
        hub.subscriptions.remove(self.queue)



def midi_type(midi):
    if midi.isNoteOn():
        return "on"
    elif midi.isNoteOff():
        return "off"
    elif midi.isController():
        return "controller"

async def produce(device, port):
    port_name = device.getPortName(port)
    device.openPort(port)
    device.ignoreTypes(True, False, True)
    timeout_ms = 50

    while True:
        midi = device.getMessage(timeout_ms)

        if midi and clients:
            data = {
                "port": port,
                "port_name": port_name,
                "note_number": midi.getNoteNumber(),
                "velocity": midi.getVelocity(),
                "state": midi_type(midi),
                "controller_number": midi.getControllerNumber(),
                "controller_value": midi.getControllerValue(),
            }

            awaitables = [ws.send(json.dumps(data)) for ws in clients]

            await asyncio.gather(*awaitables, return_exceptions=False)

        await asyncio.sleep(0)




clients = set()

async def handler(websocket, path):

    print("Client:", websocket)

    # Register
    clients.add(websocket)

    try:
        async for msg in websocket:
            pass
    finally:
        # Unregister
        clients.remove(websocket)



device = rtmidi.RtMidiIn()
port = 1

loop = asyncio.get_event_loop()

loop.create_task(produce(device, port))

start_server = websockets.serve(handler, "localhost", 8765)

loop.run_until_complete(start_server)
loop.run_forever()