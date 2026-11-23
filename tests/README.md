# Launchpad95 tests

The tests run the script outside Ableton Live, against emulated Launchpads, with
Python 3.11 (the Python of Live 11+). They also run on GitHub Actions
(`.github/workflows/tests.yml`).

## Run

```sh
python3.11 -m pip install future pytest pytest-cov pytest-timeout
scripts/fetch_framework.sh /some/dir/ableton-framework      # once
ABLETON_FRAMEWORK_DIR=/some/dir/ableton-framework python3.11 -m pytest
```

Add `--cov` for the coverage of the script modules.

### Where `_Framework` comes from

The script imports Ableton's `_Framework` (plus `ableton.v2.base` and `_Generic`), which
is not in this repository. `ABLETON_FRAMEWORK_DIR` points at one of:

- **A fetched tree** (what CI uses): `scripts/fetch_framework.sh <dir>` clones pinned
  commits of the decompiled scripts from gluon/AbletonLive11_MIDIRemoteScripts and
  gluon/AbletonLive12_MIDIRemoteScripts, keeps only `_Framework`, `_Generic` and
  `ableton/v2/base`, and applies `tests/framework.patch`. The patch fixes decompiler
  mistakes (mostly mangled `if`/`while` conditions). Each fix was checked by compiling the
  patched function and comparing its bytecode with the `.pyc` of an installed Live. The
  script does nothing when `<dir>` is already up to date.
- **An installed Live**: `ABLETON_FRAMEWORK_DIR="/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts"`.
  Its `.pyc` files load in a Python 3.11 of the same minor version. Use this to check
  that the fetched tree still behaves like the real one. The two sources should give the
  same results.

The `Live` module is always the fake one in `tests/fake_live/Live`.

## Layout

- `fake_live/Live/`: the fake `Live` API. It has a small object model (Song, Track,
  ClipSlot, Clip with the Live 11 note API, Scene, Device, RackDevice, MixerDevice...). Its
  listenable properties fire their listeners at once. Time moves only when a test calls
  `song.advance(beats)`, which launches fired clips and moves the playing position.
- `harness/`:
  - `c_instance.py`: `FakeCInstance`, which records sent MIDI, logs and translations.
  - `devices.py`: emulated `LaunchpadMK1` (also covers S and Mini), `LaunchpadMK2`,
    `LaunchpadMiniMK3` and `LaunchpadX`. They answer the handshake, turn presses into
    MIDI and decode LED states.
  - `rig.py`: `Rig`, which wires everything together the way Live routes MIDI (forwarded,
    mapped, or sent to the track as notes).
  - `clock.py`: a fake clock for the script's long-press and double-tap timings. It moves
    100 ms per `rig.tick()`, so taps are always short; use `rig.wait(seconds)` for a long
    press.
- `conftest.py`: path setup, loads the repository as package `Launchpad95`, and provides
  these fixtures: `rig` (a booted surface, run once per Launchpad model), `make_rig`,
  `model` and `clock`.
- `unit/`: pure logic (ClipNotes, scale patterns, skin keys).
- `emulated/`: boot, modes, session, pro session, step sequencers, instrument, mixer,
  device controller.

## Known bugs

Tests marked `xfail(strict=True, reason="bug: ...")` describe bugs in the script that
are not fixed yet. When a fix lands, the test passes, strict xfail turns that into a
failure, and the mark must be removed.

## Writing tests

```python
def test_pad_fires_clip(make_rig, model):
    rig = make_rig(model, song=make_song(clips=[(0, 0)]))
    rig.tap(0, 0)                 # grid x=0 (left), y=0 (top)
    rig.song.advance(1.0)         # Live launches the clip
    rig.tick()                    # update_display
    assert rig.song.tracks[0].clip_slots[0].is_playing
```

`rig.tap_top(i)` taps the round buttons above the grid (up, down, left, right, session,
user 1, user 2, mixer). `rig.tap_side(i)` taps the buttons on the right side, top first.
`rig.device.led(x, y)` returns the colour of a pad.

The device controller mode starts 8 threads. `disconnect()` stops them, and the fixtures
check that they did.
