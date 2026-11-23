"""Pro session (short tap on Session while in session mode). The side buttons become
modifiers held while tapping a pad: 0 undo, 1 shift, 2 click/copy, 3 quantize,
4 double, 5 delete, 6 duplicate, 7 record. The bottom row stops tracks, or with a
modifier held sets tempo, launch/record quantization, mute, solo and arm."""
import pytest
from harness.rig import make_song

SESSION = 4
UNDO, SHIFT, CLICK, QUANTIZE, DOUBLE, DELETE, DUPLICATE, RECORD = range(8)


@pytest.fixture
def pro_rig(make_rig, model):
	rig = make_rig(model, song=make_song(clips=[(0, 0), (1, 1), (2, 2)]))
	rig.tap_top(SESSION)
	rig.tick()
	assert rig.selector._pro_session_on
	return rig


def slot(rig, track, scene):
	return rig.song.tracks[track].clip_slots[scene]


def with_modifier(rig, side, action):
	rig.press_side(side)
	action()
	rig.release_side(side)


def test_pads_still_launch_clips(pro_rig):
	pro_rig.tap(0, 0)
	pro_rig.song.advance(1.0)
	assert slot(pro_rig, 0, 0).is_playing


def test_delete_and_pad_deletes_the_clip(pro_rig):
	with_modifier(pro_rig, DELETE, lambda: pro_rig.tap(1, 1))
	assert not slot(pro_rig, 1, 1).has_clip
	assert slot(pro_rig, 1, 1).fire_count == 0


def test_shift_delete_and_pad_deletes_the_scene(pro_rig):
	pro_rig.press_side(SHIFT)
	with_modifier(pro_rig, DELETE, lambda: pro_rig.tap(0, 2))
	pro_rig.release_side(SHIFT)
	assert len(pro_rig.song.scenes) == 7
	assert slot(pro_rig, 0, 0).has_clip  # scene 0 kept


def test_duplicate_and_pad_duplicates_the_clip(pro_rig):
	with_modifier(pro_rig, DUPLICATE, lambda: pro_rig.tap(0, 0))
	assert slot(pro_rig, 0, 1).has_clip
	assert pro_rig.song.view.highlighted_clip_slot is slot(pro_rig, 0, 1)


def test_click_copies_then_pastes_a_clip(pro_rig):
	pro_rig.press_side(CLICK)
	pro_rig.tap(2, 2)  # copy
	pro_rig.tap(5, 4)  # paste
	pro_rig.release_side(CLICK)
	assert slot(pro_rig, 5, 4).has_clip


def test_double_tap_on_click_toggles_the_metronome(pro_rig):
	assert not pro_rig.song.metronome
	pro_rig.tap_side(CLICK)
	assert not pro_rig.song.metronome  # a single tap does nothing
	pro_rig.tap_side(CLICK)
	assert pro_rig.song.metronome
	pro_rig.wait(1.0)
	pro_rig.tap_side(CLICK)
	assert pro_rig.song.metronome


def test_quantize_and_pad_quantizes_the_clip(pro_rig):
	with_modifier(pro_rig, QUANTIZE, lambda: pro_rig.tap(1, 1))
	assert getattr(slot(pro_rig, 1, 1).clip, "quantized_with", None) is not None


def test_double_and_pad_doubles_the_loop(pro_rig):
	clip = slot(pro_rig, 2, 2).clip
	with_modifier(pro_rig, DOUBLE, lambda: pro_rig.tap(2, 2))
	assert clip.length == 8.0


def test_undo_tap_undoes_and_long_press_redoes(pro_rig):
	pro_rig.song.can_undo = True
	pro_rig.song.can_redo = True
	pro_rig.tap_side(UNDO)
	assert pro_rig.song.undo_steps == ["undo"]
	pro_rig.press_side(UNDO)
	pro_rig.wait(1.0)
	pro_rig.release_side(UNDO)
	assert pro_rig.song.undo_steps == ["undo", "redo"]


def test_click_and_bottom_row_set_the_tempo(pro_rig):
	song = pro_rig.song
	with_modifier(pro_rig, CLICK, lambda: pro_rig.tap(6, 7))  # +5
	assert song.tempo == 125.0
	with_modifier(pro_rig, CLICK, lambda: pro_rig.tap(4, 7))  # -1
	assert song.tempo == 124.0


def test_record_and_bottom_row_arms_the_track(pro_rig):
	with_modifier(pro_rig, RECORD, lambda: pro_rig.tap(3, 7))
	assert pro_rig.song.tracks[3].arm


def test_duplicate_and_bottom_row_solos_the_track(pro_rig):
	with_modifier(pro_rig, DUPLICATE, lambda: pro_rig.tap(2, 7))
	assert pro_rig.song.tracks[2].solo


def test_delete_and_bottom_row_mutes_the_track(pro_rig):
	with_modifier(pro_rig, DELETE, lambda: pro_rig.tap(5, 7))
	assert pro_rig.song.tracks[5].mute


def test_shift_and_bottom_row_sets_launch_quantization(pro_rig):
	import Live

	with_modifier(pro_rig, SHIFT, lambda: pro_rig.tap(3, 7))  # first fixed rate: 2 bars
	assert pro_rig.song.clip_trigger_quantization == Live.Song.Quantization.q_2_bars


def test_quantize_and_bottom_row_sets_record_quantization(pro_rig):
	import Live

	with_modifier(pro_rig, QUANTIZE, lambda: pro_rig.tap(4, 7))  # second fixed rate: 1/8
	assert pro_rig.song.midi_recording_quantization == Live.Song.RecordingQuantization.rec_q_eight


def test_double_and_bottom_row_sets_fixed_length(pro_rig):
	session = pro_rig.selector.session_component()
	with_modifier(pro_rig, DOUBLE, lambda: pro_rig.tap(6, 7))  # 4 bars
	assert session._fixed_length_on
	assert session._fixed_length == 4


def test_leaving_pro_session_restores_scene_buttons(pro_rig):
	pro_rig.tap_top(SESSION)
	assert not pro_rig.selector._pro_session_on
	pro_rig.tap_side(0)
	pro_rig.song.advance(1.0)
	assert pro_rig.song.scenes[0].fire_count == 1


def test_pad_release_reaches_the_clip_for_gate_launch_mode(pro_rig):
	clip = slot(pro_rig, 0, 0).clip
	pro_rig.tap(0, 0)
	assert clip.fire_button_states == [True, False]


def test_pads_past_the_last_track_do_nothing(make_rig, model):
	rig = make_rig(model, song=make_song(clips=[(0, 0)], num_tracks=4))
	rig.tap_top(SESSION)
	rig.tick()
	assert rig.selector._pro_session_on
	rig.tap(6, 0)
	with_modifier(rig, DELETE, lambda: rig.tap(6, 0))
	with_modifier(rig, RECORD, lambda: rig.tap(6, 0))
	rig.tick()


def test_modifier_press_release_does_not_reach_the_clip(pro_rig):
	clip = slot(pro_rig, 0, 0).clip
	with_modifier(pro_rig, QUANTIZE, lambda: pro_rig.tap(0, 0))
	assert clip.fire_button_states == []


def test_fixed_length_empty_pad_fires_once(pro_rig):
	pro_rig.selector._session._fixed_length_on = True
	empty = slot(pro_rig, 3, 0)
	pro_rig.tap(3, 0)
	assert empty.fire_count == 1


def test_fixed_length_plus_led_is_off_at_the_maximum(pro_rig, monkeypatch):
	from Launchpad95.SpecialProSessionComponent import MAX_FIXED_LENGTH

	session = pro_rig.selector._session
	sent = []
	button = session._stop_track_clip_buttons[2]
	monkeypatch.setattr(button, "send_value", lambda value, *a, **k: sent.append(value))
	session._fixed_length_on = True
	session._fixed_length = MAX_FIXED_LENGTH
	session._update_fixed_length_leds(2)
	assert sent == ["FixedLength.PlusMinus.Off"]
	session._fixed_length = MAX_FIXED_LENGTH - 1
	session._update_fixed_length_leds(2)
	assert sent[-1] == "FixedLength.PlusMinus.On"
