#!/usr/bin/env python

import asyncio
import json

import websockets
import rtmidi



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
    timeout_ms = 1/50

    while True:
        midi = device.getMessage()

        if midi and clients:
            data = {
                "port": port,
                "port_name": port_name,
                "note_number": midi.getNoteNumber(),
                "note_name": midi.getMidiNoteName(midi.getNoteNumber()),
                "velocity": midi.getVelocity(),
                "state": midi_type(midi),
                "controller_number": midi.getControllerNumber(),
                "controller_value": midi.getControllerValue(),
            }

            awaitables = [ws.send(json.dumps(data)) for ws in clients]

            await asyncio.gather(*awaitables, return_exceptions=False)

        await asyncio.sleep(timeout_ms)


async def handle_producers(loop):

    producers = []

    prev_num_ports = 0

    while True:
        num_ports = rtmidi.RtMidiIn().getPortCount()

        if num_ports != prev_num_ports:
            print("Creating new producers!")

            for producer in producers:
                producer.cancel()

            producers = []

            for port in range(num_ports):
                device = rtmidi.RtMidiIn()
                producers.append(loop.create_task(produce(device, port)))

        prev_num_ports = num_ports
        await asyncio.sleep(1)



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

loop.create_task(handle_producers(loop))

start_server = websockets.serve(handler, "localhost", 8765)

loop.run_until_complete(start_server)
loop.run_forever()