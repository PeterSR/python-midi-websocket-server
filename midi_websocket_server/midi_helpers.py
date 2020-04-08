from rtmidi.midiconstants import NOTE_OFF, NOTE_ON

sharp_note_names = [
    "C", "C#", "D", "D#", "E",
    "F", "F#", "G", "G#", "A",
    "A#", "B",
]

flat_note_names = [
    "C", "Db", "D", "Eb", "E",
    "F", "Gb", "G", "Ab", "A",
    "Bb", "B",
]

def midi_note_name(note, use_sharps=True, octave_number=True, octave_number_middle_c=5):
    note_name = sharp_note_names[note % 12] if use_sharps else flat_note_names[note % 12]

    if octave_number:
        note_name += str(note // 12 + (octave_number_middle_c - 5))

    return note_name


_midi_status = {
    NOTE_OFF: "note_off",
    NOTE_ON: "note_on",
}

def midi_status_name(status):
    return _midi_status.get(status)
