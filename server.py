#!/usr/bin/env python

# Built-in
import os
import asyncio
import json

# Sockets
import websockets

# MIDI
import rtmidi
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON
from midi_helpers import midi_note_name, midi_status_name


def create_message(msg_type, payload):
    return {
        "type": msg_type,
        "content": payload,
    }


async def send_to_all(msg):
    awaitables = [ws.send(json.dumps(msg)) for ws in clients]
    return await asyncio.gather(*awaitables, return_exceptions=False)


async def produce(device, port):
    port_name = device.get_port_name(port)
    device.open_port(port)
    device.ignore_types(sysex=True, timing=False, active_sense=True)

    default_sleep_time = 0.008
    max_sleep_time = 1
    sleep_time = default_sleep_time

    num_sleeps_without_activity = 0
    total_sleep_in_bracket = 0
    max_sleep_in_bracket = 2

    while True:
        midi = device.get_message()

        if midi:
            msg, deltatime = midi

            data = {
                "port_index": port,
                "port_name": port_name,
            }

            if len(msg) == 3:
                data["status"] = midi_status_name(msg[0])
                data["note_number"] = msg[1]
                data["note_name"] = midi_note_name(msg[1])
                data["velocity"] = msg[2]

            data["msg"] = msg

            data = create_message("midi_data", data)

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
    devices = []

    prev_num_ports = 0

    m = rtmidi.MidiIn()

    while True:
        num_ports = m.get_port_count()

        if num_ports != prev_num_ports:
            print("Creating new producers!")

            for producer in producers:
                producer.cancel()

            for device in devices:
                del device

            producers = []
            devices = []
            device_names = []

            for port, port_name in enumerate(m.get_ports()):
                device = rtmidi.MidiIn()
                producers.append(loop.create_task(produce(device, port)))
                devices.append(device)
                device_names.append(port_name)

            await send_to_all(create_message("device_list", {
                "devices": device_names,
            }))

        prev_num_ports = num_ports

        await asyncio.sleep(1)


def get_device_list(m=None):
    if m is None:
        m = rtmidi.MidiIn()

    return m.get_ports()




async def handler(websocket, path):

    print("Client:", websocket)

    # Register
    clients.add(websocket)

    await websocket.send(json.dumps(create_message("device_list", {
        "devices": get_device_list(),
    })))

    try:
        async for msg in websocket:
            print("Message from ", websocket, ":", msg)
            pass
    finally:
        # Unregister
        clients.remove(websocket)


if __name__ == "__main__":
    clients = set()

    loop = asyncio.get_event_loop()

    loop.create_task(handle_producers(loop))

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8765))
    start_server = websockets.serve(handler, host, port)

    loop.run_until_complete(start_server)
    loop.run_forever()