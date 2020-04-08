#!/usr/bin/env python

# Built-in
import os
import gc
import json
import functools
import argparse

# Sockets
import asyncio
import websockets

# MIDI
import rtmidi
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON
from .midi_helpers import midi_note_name, midi_status_name


class Device:
    """
    Lifetime of a Device object is until the list of MIDI devices change.
    This means that every time a change is discovered,
    all devices are removed and new ones are instanciated,
    even if they have not changed.
    """

    out_suffix = "_OUT"

    def __init__(self, master, port, port_name):
        self.master = master
        self.port = port
        self.port_name = port_name

        self.midi_in_name = self.port_name
        self.midi_in = rtmidi.MidiIn(name=self.midi_in_name)
        self.midi_in.open_port(self.port)
        self.midi_in.ignore_types(sysex=True, timing=False, active_sense=True)

        self.midi_out_name = self.port_name + self.out_suffix
        self.midi_out = rtmidi.MidiOut(name=self.midi_out_name)
        self.midi_out.open_port(self.port)

        self.async_task = None # Will be a coroutine instance of self.listen.


    async def listen(self):
        server = self.master.server_state

        default_sleep_time = 0.008
        max_sleep_time = 1
        sleep_time = default_sleep_time

        num_sleeps_without_activity = 0
        total_sleep_in_bracket = 0
        max_sleep_in_bracket = 2

        while True:
            midi = self.midi_in.get_message()

            if midi and server.clients:
                msg, deltatime = midi

                data = {
                    "device_name": self.port_name,
                }

                if len(msg) == 3:
                    data["status"] = midi_status_name(msg[0])
                    data["note_number"] = msg[1]
                    data["note_name"] = midi_note_name(msg[1])
                    data["velocity"] = msg[2]

                data["msg"] = msg

                data = create_message("midi_data", data)

                await server.send_to_all(data)
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


    def play(self, data):
        status_name = data.get("status")
        note_number = data.get("note_number")
        velocity = data.get("velocity")

        if status_name not in ["note_on", "note_off"] or note_number is None or velocity is None:
            print("Invalid message", data)
            return

        if status_name == "note_on":
            status = NOTE_ON
        elif status_name == "note_off":
            status = NOTE_OFF

        midi_data = [status, note_number, velocity]

        self.midi_out.send_message(midi_data)



class DeviceMaster:
    """
    Keeps track of all MIDI devices. Has discovery of new devices.
    When new devices are discovered, every single device is removed and re-created.

    Assumptions for now:
    - rtmidi.MidiIn.get_ports and rtmidi.MidiOut.get_ports
      returns the same list meaning that the indices / port numbers match up.

    TODO: Do not use port_index from MidiIn as port_index for MidiOut.
    """

    def __init__(self, server_state):
        self.server_state = server_state
        self.discovery_device = rtmidi.MidiIn()
        self.devices = {}

    def get_device_list(self):
        return list(self.devices.keys())


    async def discovery(self, loop):
        out_devices = set()
        existing_devices = set()

        while True:
            current_devices = set(self.discovery_device.get_ports()) - out_devices

            if existing_devices != current_devices:
                print("Discovered new devices")


                # Remove existing devices, including clean-up
                for device in self.devices.values():
                    device.async_task.cancel()
                    device.midi_in.close_port()
                    device.midi_out.close_port()
                    del device.midi_in
                    del device.midi_out

                self.devices = {}

                # We should not have do do this, but here we are.
                gc.collect()

                # Create new devices
                for port, port_name in enumerate(self.discovery_device.get_ports()):
                    self.devices[port_name] = Device(self, port, port_name)
                    self.devices[port_name].async_task = loop.create_task(self.devices[port_name].listen())

                existing_devices = set(self.get_device_list())

                # Find the newly created MidiOut devices and remember them.
                out_devices = set()
                for port, port_name in enumerate(self.discovery_device.get_ports()):
                    if port_name not in self.devices and Device.out_suffix in port_name:
                        out_devices.add(port_name)


                await self.server_state.send_to_all(create_message("device_list", {
                    "devices": self.get_device_list(),
                }))


            await asyncio.sleep(1)


    def play(self, data):
        device_name = data.get("device_name")
        device = self.devices.get(device_name)
        if device:
            device.play(data)




class ServerState:
    def __init__(self):
        self.device_master = DeviceMaster(self)
        self.clients = set()

    async def send_to_one(self, ws, msg):
        await ws.send(json.dumps(msg))

    async def send_to_all(self, msg):
        dump = json.dumps(msg)
        awaitables = [ws.send(dump) for ws in self.clients]
        return await asyncio.gather(*awaitables, return_exceptions=False)





def create_message(msg_type, payload):
    return {
        "type": msg_type,
        "content": payload,
    }





async def handler(websocket, path, server_state):
    print("Client:", websocket)

    # Register
    server_state.clients.add(websocket)

    # Send device list to client
    await server_state.send_to_one(websocket, create_message("device_list", {
        "devices": server_state.device_master.get_device_list(),
    }))

    # Listen for messages
    try:
        async for msg in websocket:
            try:
                data = json.loads(msg)
            except ValueError as e:
                pass
            else:
                server_state.device_master.play(data)
    finally:
        # Unregister
        server_state.clients.remove(websocket)


def main():

    parser = argparse.ArgumentParser(
        prog="midi_websocket_server",
        description='Start the MIDI Websocket server.',
    )
    parser.add_argument('-H', '--host', type=str, help='Interface to host server on (default: %(default)s)', default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument('-p', '--port', type=int, help='Port to host server on (default: %(default)s)', default=int(os.getenv("PORT", 8765)))

    args = parser.parse_args()

    print("Starting server on {host}:{port}".format(
        host=args.host,
        port=args.port,
    ))

    server_state = ServerState()


    loop = asyncio.get_event_loop()

    loop.create_task(server_state.device_master.discovery(loop))

    start_server = websockets.serve(
        functools.partial(handler, server_state=server_state),
        args.host,
        args.port,
    )

    loop.run_until_complete(start_server)
    loop.run_forever()