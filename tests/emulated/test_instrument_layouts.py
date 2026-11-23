"""Instrument controller pad layouts and quick-scale / note-repeat actions, checked against
recorded snapshots (tests/emulated/snapshots/instrument_layouts.json).

Each scenario drives the emulated Launchpad, then records every pad's skin names, MIDI
channel and note, whether the script receives it, and the LED the device shows, plus the
scale, note repeat and swing state after each action. The snapshots were recorded before
the instrument controller was restructured; refresh them only for an intended change, with
UPDATE_SNAPSHOTS=1.
"""

import json
import os

import Live
import pytest
from harness.rig import make_song

USER1 = 5
SCALES = 0
SNAPSHOT_FILE = os.path.join(os.path.dirname(__file__), "snapshots", "instrument_layouts.json")


def _load():
    if not os.path.exists(SNAPSHOT_FILE):
        return {}
    with open(SNAPSHOT_FILE) as handle:
        return json.load(handle)


def _matrix(rig):
    matrix = rig.selector._matrix
    pads = []
    for y in range(8):
        for x in range(8):
            button = matrix.get_button(x, y)
            pads.append(
                [
                    str(button.states[True]),
                    str(button.states[False]),
                    button.message_channel(),
                    button.message_identifier(),
                    button.is_enabled(),
                    rig.device.led(x, y),
                ]
            )
    return pads


def _state(rig):
    controller = rig.selector._instrument_controller
    scales = controller._scales
    return {
        "key": scales._key,
        "modus": scales._modus,
        "octave": scales._octave,
        "quick_scale_root": controller._quick_scale_root,
        "repeat_on": controller._note_repeat.is_enabled(),
        "repeat_index": controller._note_repeat.freq_index(),
        "swing": round(rig.song.swing_amount, 4),
        "message": rig.messages[-1] if rig.messages else None,
    }


def _record(rig, steps):
    return {"state": _state(rig), "matrix": _matrix(rig), "steps": steps}


def _instrument_rig(make_rig, model, song=None):
    rig = make_rig(model, song=song)
    rig.tap_top(USER1)
    rig.tick(2)
    assert rig.selector._mode_index == 4
    return rig


def _quick_scale_on(rig):
    rig.press_side(SCALES)
    rig.tap(7, 1)
    rig.release_side(SCALES)
    rig.tick()
    assert rig.selector._instrument_controller._scales.is_quick_scale


def _taps(rig, pads):
    steps = []
    for x, y in pads:
        rig.tap(x, y)
        rig.tick()
        steps.append(_state(rig))
    return steps


QUICK_KEYS = [(x, 1) for x in range(7)] + [(x, 0) for x in (0, 1, 3, 4, 5)]
QUICK_NAV = [(7, 1), (7, 1), (6, 0), (2, 0), (2, 0), (1, 1), (1, 1)]  # fifths, relative, same root twice


def scenario_note_pads(make_rig, model):
    rig = _instrument_rig(make_rig, model)
    return _record(rig, [])


def scenario_quick_scale_keys(make_rig, model):
    rig = _instrument_rig(make_rig, model)
    _quick_scale_on(rig)
    steps = _taps(rig, QUICK_KEYS + QUICK_NAV)
    return _record(rig, steps)


def scenario_quick_scale_minor_colours(make_rig, model):
    rig = _instrument_rig(make_rig, model)
    _quick_scale_on(rig)
    rig.tap(2, 0)  # relative minor
    rig.tick()
    return _record(rig, [])


def scenario_quick_scale_modes(make_rig, model):
    rig = _instrument_rig(make_rig, model)
    _quick_scale_on(rig)
    rig.tap(7, 0)  # modes page
    rig.tick()
    steps = _taps(rig, [(x, 0) for x in range(7)] + [(x, 1) for x in range(8)])
    return _record(rig, steps)


def scenario_quick_scale_repeater(make_rig, model):
    rig = _instrument_rig(make_rig, model)
    _quick_scale_on(rig)
    rig.tap(7, 0)
    rig.tap(7, 0)  # repeater page
    rig.tick()
    steps = _taps(rig, [(1, 0), (0, 0), (3, 0), (2, 0), (4, 0), (5, 0), (6, 0)] + [(x, 1) for x in range(8)])
    steps.append(_record(rig, [])["matrix"])
    rig.tap(6, 0)  # repeater off again
    rig.tap(7, 0)  # back to the root page
    rig.tick()
    return _record(rig, steps)


def drum_song():
    song = make_song()
    rack = Live.RackDevice.RackDevice(name="Drums", drum=True)
    rack.canonical_parent = song.tracks[0]
    song.tracks[0].devices = (rack,)
    return song


def scenario_drum_pads(make_rig, model):
    rig = _instrument_rig(make_rig, model, song=drum_song())
    return _record(rig, [])


def scenario_drum_repeater(make_rig, model):
    rig = _instrument_rig(make_rig, model, song=drum_song())
    rig.press_side(SCALES)  # on a drum rack: the note repeat selector
    rig.release_side(SCALES)
    rig.tick()
    steps = _taps(
        rig,
        [(5, 0), (4, 0), (6, 0), (7, 0), (4, 1), (5, 1), (6, 1), (7, 1)]
        + [(x, y) for y in (2, 3) for x in range(4, 8)],
    )
    steps.append(_record(rig, [])["matrix"])
    rig.tap(7, 0)  # repeater off
    rig.tick()
    return _record(rig, steps)


SCENARIOS = {
    name[len("scenario_") :]: function for name, function in sorted(globals().items()) if name.startswith("scenario_")
}


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_instrument_layout_matches_the_snapshot(make_rig, model, scenario):
    result = json.loads(json.dumps(SCENARIOS[scenario](make_rig, model)))
    key = f"{model.__name__}/{scenario}"
    snapshots = _load()
    if os.environ.get("UPDATE_SNAPSHOTS"):
        snapshots[key] = result
        os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)
        with open(SNAPSHOT_FILE, "w") as handle:
            json.dump(snapshots, handle, indent=0, sort_keys=True)
        return
    assert key in snapshots, f"no snapshot for {key}: record it with UPDATE_SNAPSHOTS=1"
    expected = snapshots[key]
    assert result["state"] == expected["state"]
    assert result["steps"] == expected["steps"]
    for index, (pad, expected_pad) in enumerate(zip(result["matrix"], expected["matrix"], strict=True)):
        assert pad == expected_pad, f"pad x={index % 8} y={index // 8}"
