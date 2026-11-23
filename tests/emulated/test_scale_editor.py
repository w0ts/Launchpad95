"""Scale editor (instrument mode, scale button held): what every pad shows and does,
checked against recorded snapshots (tests/emulated/snapshots/scale_editor.json).

The pads are tapped in a fixed order covering the 8 rows (layout modes, root keys,
circle of fifths, relative scale, quick scale, octaves, scales); after each tap the test
records the scale state, the message and the LED of every pad. The snapshots were recorded
before ScaleComponent was restructured; refresh them only for an intended change, with
UPDATE_SNAPSHOTS=1.
"""

import json
import os

USER1 = 5
SCALES = 0
SNAPSHOT_FILE = os.path.join(os.path.dirname(__file__), "snapshots", "scale_editor.json")

TAPS = (
    [(x, 2) for x in range(7)]  # white keys
    + [(x, 1) for x in (0, 1, 3, 4, 5)]  # black keys
    + [(7, 2), (7, 2), (6, 1), (2, 1), (2, 1)]  # circle of fifths, relative scale
    + [(x, 3) for x in range(8)]  # octaves
    + [(x, y) for y in range(4, 8) for x in range(8)]  # scales
    + [(0, 4), (2, 1), (3, 5), (2, 1), (4, 5), (2, 1)]  # relative from other scales
    + [(0, 0), (0, 0), (1, 0), (1, 0)]  # absolute root, horizontal
    + [(x, 0) for x in (2, 3, 4, 6, 5)]  # layouts
    + [(7, 1), (7, 1)]  # quick scale on / off
    + [(7, 0)]  # drum rack layout
    + [(x, y) for y in (1, 2, 4) for x in (0, 7)]  # ignored or quick scale on a drum rack
    + [(7, 1), (3, 3), (5, 0)]  # quick scale off, octave, back to diatonic
)


def _state(rig):
    scales = rig.selector._instrument_controller._scales
    return {
        "key": scales._key,
        "modus": scales._modus,
        "octave": scales._octave,
        "mode": scales._mode,
        "absolute": scales._is_absolute,
        "horizontal": scales._is_horizontal,
        "quick": scales._quick_scale,
        "drumrack": scales.is_drumrack,
        "message": rig.messages[-1] if rig.messages else None,
    }


def _leds(rig):
    return [[rig.device.led(x, y) for x in range(8)] for y in range(8)]


def _run(make_rig, model):
    rig = make_rig(model)
    rig.tap_top(USER1)
    rig.tick(2)
    rig.press_side(SCALES)
    steps = [{"state": _state(rig), "leds": _leds(rig)}]
    for x, y in TAPS:
        rig.tap(x, y)
        steps.append({"tap": [x, y], "state": _state(rig), "leds": _leds(rig)})
    rig.release_side(SCALES)
    return steps


def _load():
    if not os.path.exists(SNAPSHOT_FILE):
        return {}
    with open(SNAPSHOT_FILE) as handle:
        return json.load(handle)


def test_scale_editor_matches_the_snapshot(make_rig, model):
    steps = json.loads(json.dumps(_run(make_rig, model)))
    key = model.__name__
    snapshots = _load()
    if os.environ.get("UPDATE_SNAPSHOTS"):
        snapshots[key] = steps
        os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)
        with open(SNAPSHOT_FILE, "w") as handle:
            json.dump(snapshots, handle, separators=(",", ":"), sort_keys=True)
        return
    assert key in snapshots, f"no snapshot for {key}: record it with UPDATE_SNAPSHOTS=1"
    for step, expected in zip(steps, snapshots[key], strict=True):
        assert step == expected, step.get("tap")


def test_relative_scale_of_a_minor_key_is_its_major(make_rig, model):
    rig = make_rig(model)
    rig.tap_top(USER1)
    rig.tick(2)
    scales = rig.selector._instrument_controller._scales
    rig.press_side(SCALES)
    rig.tap(5, 2)  # A
    rig.tap(1, 4)  # the second scale (minor)
    rig.tap(2, 1)  # relative scale
    rig.release_side(SCALES)
    assert scales._key == 0
    assert scales._modus == 0
