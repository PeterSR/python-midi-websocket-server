#!/usr/bin/env python

import asyncio
import json

import websockets
import rtmidi


def create_message(msg_type, payload):
    return {
        "type": msg_type,
        "content": payload,
    }


async def send_to_all(msg):
    awaitables = [ws.send(json.dumps(msg)) for ws in clients]
    return await asyncio.gather(*awaitables, return_exceptions=False)

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

    default_sleep_time = 0.008
    max_sleep_time = 1
    sleep_time = default_sleep_time

    num_sleeps_without_activity = 0
    total_sleep_in_bracket = 0
    max_sleep_in_bracket = 2

    while True:
        midi = device.getMessage()

        if midi and clients:
            data = create_message("midi_data", {
                "port_index": port,
                "port_name": port_name,
                "note_number": midi.getNoteNumber(),
                "note_name": midi.getMidiNoteName(midi.getNoteNumber()),
                "velocity": midi.getVelocity(),
                "state": midi_type(midi),
                "controller_number": midi.getControllerNumber(),
                "controller_value": midi.getControllerValue(),
            })

            await send_to_all(data)
            await asyncio.sleep(0)

            num_sleeps_without_activity = 0
            total_sleep_in_bracket = 0
            sleep_time = default_sleep_time
        else:
            await asyncio.sleep(sleep_time)
            num_sleeps_without_activity += 1
            total_sleep_in_bracket += sleep_time
            if total_sleep_in_bracket >= max_sleep_in_bracket:
                sleep_time *= 2
                sleep_time = min(sleep_time, max_sleep_time)
                total_sleep_in_bracket = 0


async def handle_producers(loop):

    producers = []

    prev_num_ports = 0

    while True:
        m = rtmidi.RtMidiIn()
        num_ports = m.getPortCount()

        if num_ports != prev_num_ports:
            print("Creating new producers!")

            for producer in producers:
                producer.cancel()

            producers = []
            device_names = []

            for port in range(num_ports):
                device = rtmidi.RtMidiIn()
                producers.append(loop.create_task(produce(device, port)))
                device_names.append(m.getPortName(port))

            await send_to_all(create_message("device_list", {
                "devices": device_names,
            }))

        prev_num_ports = num_ports
        await asyncio.sleep(1)


def get_device_list(m=None):
    if m is None:
        m = rtmidi.RtMidiIn()

    return [
        m.getPortName(i)
        for i in range(m.getPortCount())
    ]


clients = set()

async def handler(websocket, path):

    print("Client:", websocket)

    # Register
    clients.add(websocket)

    await websocket.send(json.dumps(create_message("device_list", {
        "devices": get_device_list(),
    })))

    try:
        async for msg in websocket:
            pass
    finally:
        # Unregister
        clients.remove(websocket)



loop = asyncio.get_event_loop()

loop.create_task(handle_producers(loop))

start_server = websockets.serve(handler, "localhost", 8765)

loop.run_until_complete(start_server)
loop.run_forever()