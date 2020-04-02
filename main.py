import sys
import rtmidi
import threading


class Collector(threading.Thread):
    def __init__(self, device, port, timeout_ms=100):
        super().__init__()
        self.setDaemon(True)
        self.port = port
        self.port_name = device.getPortName(port)
        self.device = device
        self.quit = False
        self.timeout_ms = timeout_ms

    def run(self):
        self.device.openPort(self.port)
        self.device.ignoreTypes(True, False, True)
        while True:
            if self.quit:
                return
            msg = self.device.getMessage(self.timeout_ms)
            if msg:
                self.callback(msg)

    def callback(self, midi):
        if midi.isNoteOn():
            print('%s: ON: ' % self.port_name, midi.getMidiNoteName(midi.getNoteNumber()), midi.getVelocity())
        elif midi.isNoteOff():
            print('%s: OFF:' % self.port_name, midi.getMidiNoteName(midi.getNoteNumber()))
        elif midi.isController():
            print('%s: CONTROLLER' % self.port_name, midi.getControllerNumber(), midi.getControllerValue())

dev = rtmidi.RtMidiIn()
collectors = []
for i in range(dev.getPortCount()):
    device = rtmidi.RtMidiIn()
    print('OPENING',dev.getPortName(i))
    collector = Collector(device, i)
    collector.start()
    collectors.append(collector)


print('HIT ENTER TO EXIT')
sys.stdin.read(1)
for c in collectors:
    c.quit = True