"""Step sequencer side buttons, OSD texts, Live scale listeners and drum rack lookup, for
the drum (user 2, first sub mode) and melodic (second sub mode) sequencers and the
instrument controller."""

import Live
import pytest
from harness.rig import make_song

USER1, USER2 = 5, 6
# drum sequencer side buttons
SCALE, LOCK, QUANTIZE, MODE, UP, DOWN, VELOCITY, MUTE = range(8)
# melodic sequencer side buttons
RANDOM, LENGTHS, OCTAVES, VELOCITIES, PITCHES = 3, 4, 5, 6, 7


@pytest.fixture
def seq_rig(make_rig, model):
    rig = make_rig(model, song=make_song(clips=[(0, 0)]))
    rig.tap_top(USER2)
    rig.tick(2)
    assert rig.selector._mode_index == 6
    return rig


@pytest.fixture
def melodic_rig(make_rig, model):
    rig = make_rig(model, song=make_song(clips=[(0, 0)]))
    rig.tap_top(USER2)
    rig.tap_top(USER2)
    rig.tick(2)
    assert rig.selector._mode_index == 7
    return rig


def osd(rig):
    return rig.selector._osd


def stepseq(rig):
    return rig.selector._stepseq


def hold_side(rig, index, seconds):
    rig.press_side(index)
    rig.wait(seconds)
    rig.release_side(index)


# -- drum sequencer
def test_drum_osd(seq_rig):
    rig = seq_rig
    assert osd(rig).mode == "Drum Step Sequencer"
    assert osd(rig).attribute_names == ["Scale", "Root Note", "Octave", "Quantisation", " ", " ", " ", " "]
    assert osd(rig).attributes[3] == "1/16"
    assert osd(rig).info == ["track : " + rig.song.tracks[0].name, "clip : Clip"]
    rig.tap_side(MODE)
    assert osd(rig).mode == "Drum Step Sequencer (multinote)"


def test_drum_osd_without_clip(make_rig, model):
    rig = make_rig(model)
    rig.tap_top(USER2)
    rig.tick(2)
    assert osd(rig).attribute_names == [" "] * 8
    assert osd(rig).info[1] == "no clip selected"


def test_lock_tap_locks_to_the_clip_and_long_press_to_the_track(seq_rig):
    rig = seq_rig
    rig.tap_side(LOCK)
    assert stepseq(rig)._is_locked
    assert "stepseq : locked to clip 'Clip'" in rig.messages
    assert osd(rig).info[1] == "clip : Clip (locked)"
    hold_side(rig, LOCK, 0.7)
    assert stepseq(rig)._lock_to_track
    assert stepseq(rig)._is_locked
    rig.tap_side(LOCK)
    assert not stepseq(rig)._is_locked


def test_mute_tap_is_momentary_and_double_tap_latches(seq_rig):
    rig = seq_rig
    rig.tap_side(MUTE)
    rig.wait(0.5)
    assert not stepseq(rig)._is_mute_shifted
    rig.tap_side(MUTE)
    rig.tap_side(MUTE)
    assert stepseq(rig)._is_mute_shifted
    assert rig.messages[-1] == "Mute mode locked ON (double-tap mute to unlock)"
    rig.wait(0.5)
    rig.tap_side(MUTE)  # a single tap does not unlatch
    assert stepseq(rig)._is_mute_shifted
    rig.wait(0.5)
    rig.tap_side(MUTE)
    rig.tap_side(MUTE)
    assert not stepseq(rig)._is_mute_shifted
    assert rig.messages[-1] == "Mute mode unlocked"


def test_long_press_on_mode_in_multinote_switches_to_two_lines(seq_rig):
    rig = seq_rig
    rig.tap_side(MODE)
    assert stepseq(rig)._number_of_lines_per_note == 1
    hold_side(rig, MODE, 0.4)
    assert stepseq(rig)._number_of_lines_per_note == 2
    assert stepseq(rig)._mode == 2
    rig.tap_side(MODE)  # short: back to the normal mode
    assert stepseq(rig)._mode == 1


def test_long_press_on_quantize_duplicates_the_clip(seq_rig):
    rig = seq_rig
    hold_side(rig, QUANTIZE, 0.7)
    assert "Step Sequencer: duplicate clip" in rig.messages
    assert rig.song.tracks[0].clip_slots[1].has_clip


def test_quantize_taps_cycle_the_step_length(seq_rig):
    rig = seq_rig
    rig.tap_side(QUANTIZE)
    assert rig.messages[-1] == "QUANTIZATION : 1/32"
    assert osd(rig).attributes[3] == "1/32"


def test_live_root_note_and_scale_reach_the_drum_sequencer(seq_rig):
    rig = seq_rig
    rig.song.root_note = 5
    assert stepseq(rig)._scale_selector._key == 5
    rig.song.scale_name = "Minor"
    selector = stepseq(rig)._scale_selector
    assert selector._modus_names[selector._modus] == "Minor"


def test_scale_listeners_follow_the_mode(seq_rig):
    rig = seq_rig
    seq = stepseq(rig)
    assert rig.song.root_note_has_listener(seq.handle_root_note_changed)
    rig.tap_top(4)  # session
    rig.tick()
    assert not rig.song.root_note_has_listener(seq.handle_root_note_changed)
    assert not rig.song.scale_name_has_listener(seq.handle_scale_name_changed)


def drum_song(nested=False):
    song = make_song(clips=[(0, 0)])
    track = song.tracks[0]
    drums = Live.RackDevice.RackDevice(name="Drums", drum=True)
    device = drums
    if nested:
        device = Live.RackDevice.RackDevice(name="Outer", chains=(Live.Chain.Chain(devices=(drums,)),))
        drums.canonical_parent = device.chains[0]
    device.canonical_parent = track
    track.devices = (device,)
    return song, drums


@pytest.mark.parametrize("nested", [False, True], ids=["top", "in-chain"])
def test_drum_sequencer_finds_the_drum_rack(make_rig, model, nested):
    song, drums = drum_song(nested)
    rig = make_rig(model, song=song)
    rig.tap_top(USER2)
    rig.tick(2)
    assert stepseq(rig)._drum_group_device is drums


@pytest.mark.parametrize("nested", [False, True], ids=["top", "in-chain"])
def test_instrument_controller_finds_the_drum_rack(make_rig, model, nested):
    song, drums = drum_song(nested)
    rig = make_rig(model, song=song)
    rig.tap_top(USER1)
    rig.tick(2)
    assert rig.selector._instrument_controller._drum_group_device is drums


def test_no_drum_rack_on_a_plain_instrument(make_rig, model):
    song = make_song(clips=[(0, 0)])
    synth = Live.Device.Device(name="Synth")
    synth.canonical_parent = song.tracks[0]
    song.tracks[0].devices = (synth,)
    rig = make_rig(model, song=song)
    rig.tap_top(USER2)
    rig.tick(2)
    assert stepseq(rig)._drum_group_device is None


def test_live_root_note_reaches_the_instrument_controller(make_rig, model):
    rig = make_rig(model)
    rig.tap_top(USER1)
    rig.tick(2)
    rig.song.root_note = 7
    assert rig.selector._instrument_controller._scales._key == 7


# -- melodic sequencer
def test_melodic_osd_pages(melodic_rig):
    rig = melodic_rig
    assert osd(rig).mode == "Melodic Step Sequencer"
    assert osd(rig).attribute_names[:6] == ["Scale", "Root Note", "Octave", "Quantisation", "Polyphony", "Page"]
    assert osd(rig).attributes[4:6] == ["Poly", "Notes"]
    for side, page, message in (
        (VELOCITIES, "Velocity", "velocity"),
        (OCTAVES, "Octave", "octave"),
        (LENGTHS, "Length", "length"),
    ):
        rig.tap_side(side)
        assert osd(rig).attributes[5] == page
        assert rig.messages[-1] == message
        rig.wait(0.6)
    rig.tap_side(PITCHES)
    assert osd(rig).attributes[5] == "Notes"


def test_double_tap_on_pitches_toggles_mono(melodic_rig):
    rig = melodic_rig
    rig.tap_side(PITCHES)
    rig.tap_side(PITCHES)
    assert osd(rig).attributes[4] == "Mono"
    rig.wait(0.6)
    rig.tap_side(PITCHES)
    assert osd(rig).attributes[4] == "Mono"


def test_held_velocities_button_mute_shifts(melodic_rig):
    rig = melodic_rig
    rig.press_side(VELOCITIES)
    assert rig.selector._stepseq2._is_mute_shifted
    rig.release_side(VELOCITIES)
    assert not rig.selector._stepseq2._is_mute_shifted


def test_random_button_randomises(melodic_rig):
    rig = melodic_rig
    rig.tap_side(RANDOM)
    assert rig.messages[-1] == "randomise"
    assert rig.song.tracks[0].clip_slots[0].clip.note_tuples()


# -- which clip the drum sequencer follows
@pytest.fixture
def three_clip_rig(make_rig, model):
    rig = make_rig(model, song=make_song(clips=[(0, 0), (0, 2), (0, 4)]))
    rig.tap_top(USER2)
    rig.tick(2)
    return rig


def slot_clip(rig, scene):
    return rig.song.tracks[0].clip_slots[scene].clip


def test_unlocked_sequencer_follows_the_selected_scene(three_clip_rig):
    rig = three_clip_rig
    rig.song.view.selected_scene = rig.song.scenes[2]
    rig.tick()
    assert stepseq(rig)._clip is slot_clip(rig, 2)
    rig.song.view.selected_scene = rig.song.scenes[1]  # empty slot
    rig.tick()
    assert stepseq(rig)._clip is None


def test_clip_lock_keeps_the_clip_when_the_scene_changes(three_clip_rig):
    rig = three_clip_rig
    rig.tap_side(LOCK)
    rig.song.view.selected_scene = rig.song.scenes[2]
    rig.tick()
    assert stepseq(rig)._clip is slot_clip(rig, 0)


def test_track_lock_follows_the_triggered_then_the_playing_clip(three_clip_rig):
    rig = three_clip_rig
    hold_side(rig, LOCK, 0.7)  # locked to the track
    assert stepseq(rig)._lock_to_track and stepseq(rig)._is_locked
    rig.song.tracks[0].clip_slots[4].fire()
    rig.song.view.selected_scene = rig.song.scenes[1]
    rig.tick(6)  # the refresh scheduled 5 ticks later sees the triggered clip
    assert stepseq(rig)._clip is slot_clip(rig, 4)
    rig.song.advance(1.0)  # now playing
    rig.song.view.selected_scene = rig.song.scenes[3]
    rig.tick(6)
    assert stepseq(rig)._clip is slot_clip(rig, 4)


def test_track_lock_without_playing_clip_uses_the_selected_scene(three_clip_rig):
    rig = three_clip_rig
    hold_side(rig, LOCK, 0.7)
    rig.song.view.selected_scene = rig.song.scenes[2]
    rig.tick(6)
    assert stepseq(rig)._clip is slot_clip(rig, 2)


def test_deleting_the_locked_clip_unlocks(three_clip_rig):
    rig = three_clip_rig
    rig.tap_side(LOCK)
    rig.song.tracks[0].clip_slots[0].delete_clip()
    rig.tick()
    assert not stepseq(rig)._is_locked
    assert stepseq(rig)._clip is None


# -- melodic editor grid
def melodic_editor(rig):
    return rig.selector._stepseq2._note_editor


def grid_column(rig, x):
    return [melodic_editor(rig)._grid_buffer[x][y] for y in range(7)]


def show_page(rig, side):
    rig.tap_side(side)
    rig.wait(0.6)


def test_melodic_pitch_grid_and_mono(melodic_rig):
    rig = melodic_rig
    rig.tap(0, 6)
    rig.tap(0, 2)  # poly: a second note on the same step
    assert grid_column(rig, 0) == ["StepSequencer2.Pitch.Off"] * 2 + ["StepSequencer2.Pitch.On"] + [
        "StepSequencer2.Pitch.Off"
    ] * 3 + ["StepSequencer2.Pitch.On"]
    rig.tap_side(PITCHES)
    rig.tap_side(PITCHES)  # mono
    rig.tap(1, 6)
    rig.tap(1, 3)  # mono: replaces the step's note
    assert grid_column(rig, 1).count("StepSequencer2.Pitch.On") == 1


def test_melodic_held_pitch_button_fills_the_loop(melodic_rig):
    rig = melodic_rig
    rig.press_side(PITCHES)
    rig.tap(3, 4)
    rig.release_side(PITCHES)
    ed = melodic_editor(rig)
    loop_steps = int(rig.song.tracks[0].clip_slots[0].clip.loop_end / ed._quantization)
    assert all(ed._notes_pitches[x * 7 + 6 - 4] == 1 for x in range(loop_steps))


@pytest.mark.parametrize(
    "side, values, skin, bar",
    [
        (OCTAVES, "_notes_octaves", "StepSequencer2.Octave", False),
        (VELOCITIES, "_notes_velocities", "StepSequencer2.Velocity", True),
        (LENGTHS, "_notes_lengths", "StepSequencer2.Length", True),
    ],
    ids=["octaves", "velocities", "lengths"],
)
def test_melodic_value_pages(melodic_rig, side, values, skin, bar):
    rig = melodic_rig
    rig.tap(0, 6)  # a note on step 0, none on step 1
    show_page(rig, side)
    ed = melodic_editor(rig)
    rig.tap(0, 2)  # step 0: value 4
    rig.tap(1, 5)  # step 1: value 1
    assert getattr(ed, values)[0] == 4
    assert getattr(ed, values)[1] == 1
    on = [y for y in range(7) if grid_column(rig, 0)[y] == skin + ".On"]
    assert on == ([2, 3, 4, 5, 6] if bar else [2])
    dim = [y for y in range(7) if grid_column(rig, 1)[y] == skin + ".Dim"]  # no note on step 1
    assert dim == ([5, 6] if bar else [5])
    # held: the left half sets every step of the loop, the right half steps them up/down
    loop_steps = int(rig.song.tracks[0].clip_slots[0].clip.loop_end / ed._quantization)
    rig.press_side(side)
    rig.tap(2, 3)
    assert all(getattr(ed, values)[x] == 3 for x in range(loop_steps))
    rig.tap(6, 1)  # up
    assert all(getattr(ed, values)[x] == 4 for x in range(loop_steps))
    rig.tap(6, 5)  # down
    rig.tap(6, 5)
    assert all(getattr(ed, values)[x] == 2 for x in range(loop_steps))
    rig.release_side(side)


def test_melodic_playhead_and_playing_notes(melodic_rig):
    rig = melodic_rig
    ed = melodic_editor(rig)
    rig.tap(2, 4)
    ed.set_playhead(2 * ed.quantization)
    assert ed._grid_buffer[2][6] == "StepSequencer2.NoteEditor.MetronomeInPage"
    assert ed._grid_buffer[2][4] == "StepSequencer2.NoteEditor.PlayInPage"
    ed.set_playhead(10 * ed.quantization)  # second page: shown in the other-page colour
    assert ed._grid_buffer[2][6] == "StepSequencer2.NoteEditor.MetronomeInOtherPage"
    ed.set_playhead(None)
    assert ed._grid_buffer[2][6] != "StepSequencer2.NoteEditor.MetronomeInOtherPage"


def test_melodic_pad_without_clip_creates_one(make_rig, model):
    rig = make_rig(model)
    rig.tap_top(USER2)
    rig.tap_top(USER2)
    rig.tick(2)
    rig.song.view.highlighted_clip_slot = rig.song.tracks[0].clip_slots[0]
    rig.tap(0, 0)
    assert rig.song.tracks[0].clip_slots[0].has_clip
