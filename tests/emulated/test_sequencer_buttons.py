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
