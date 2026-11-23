"""Drum step sequencer grid colours (note editor) while a clip plays, checked against
recorded snapshots (tests/emulated/snapshots/sequencer_grids.json): velocities, muted
notes, the playhead, playing notes, other pages, one-note and multinote layouts.

The snapshots were recorded before the note editor's drawing was restructured; refresh
them only for an intended change, with UPDATE_SNAPSHOTS=1.
"""

import json
import os

import pytest
from harness.rig import make_song

USER2 = 6
MODE = 3
SNAPSHOT_FILE = os.path.join(os.path.dirname(__file__), "snapshots", "sequencer_grids.json")

NOTES = (
    # (pitch, time, length, velocity, muted)
    (36, 0.0, 0.25, 127, False),
    (36, 0.25, 0.25, 20, False),
    (36, 0.5, 0.25, 100, True),
    (36, 1.0, 0.25, 50, False),
    (36, 4.25, 0.25, 90, False),  # second page
    (37, 0.25, 0.25, 64, False),
    (38, 0.75, 0.25, 110, False),
    (40, 2.0, 0.25, 80, True),
)


def _grid(rig):
    editor = rig.selector._stepseq._note_editor
    return [[str(editor._grid_buffer[x][y]) for x in range(8)] for y in range(8)]


def _scenario(make_rig, model, mode_taps, mode_hold, beats_list):
    song = make_song(clips=[(0, 0)])
    song.tracks[0].clip_slots[0].clip.set_notes(NOTES)
    rig = make_rig(model, song=song)
    rig.tap_top(USER2)
    rig.tick(2)
    for _ in range(mode_taps):
        rig.tap_side(MODE)
    if mode_hold:
        rig.press_side(MODE)
        rig.wait(0.4)
        rig.release_side(MODE)
    frames = [_grid(rig)]
    rig.song.tracks[0].clip_slots[0].fire()
    for beats in beats_list:
        rig.song.advance(beats)
        rig.tick()
        frames.append(_grid(rig))
    return frames


SCENARIOS = {
    "one_note": (0, False),
    "multinote": (1, False),
    "multinote_two_lines": (1, True),
}
BEATS = (0.25, 0.25, 0.5, 3.5, 0.5)


def _load():
    if not os.path.exists(SNAPSHOT_FILE):
        return {}
    with open(SNAPSHOT_FILE) as handle:
        return json.load(handle)


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_drum_grid_matches_the_snapshot(make_rig, model, scenario):
    taps, hold = SCENARIOS[scenario]
    frames = _scenario(make_rig, model, taps, hold, BEATS)
    key = f"{model.__name__}/{scenario}"
    snapshots = _load()
    if os.environ.get("UPDATE_SNAPSHOTS"):
        snapshots[key] = frames
        os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)
        with open(SNAPSHOT_FILE, "w") as handle:
            json.dump(snapshots, handle, indent=0, sort_keys=True)
        return
    assert key in snapshots, f"no snapshot for {key}: record it with UPDATE_SNAPSHOTS=1"
    for index, (frame, expected) in enumerate(zip(frames, snapshots[key], strict=True)):
        assert frame == expected, f"frame {index}"
