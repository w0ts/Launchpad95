"""Drum step sequencer (user 2 button, first sub mode): pads edit the notes of the clip in
the selected track's selected scene."""
import Live
import pytest

from harness.rig import make_song

USER2 = 6


@pytest.fixture
def seq_rig(make_rig, model):
	song = make_song(clips=[(0, 0)])
	rig = make_rig(model, song=song)
	rig.tap_top(USER2)
	rig.tick(2)
	assert rig.selector._mode_index == 6  # drum step sequencer
	return rig


def clip(rig, track=0, scene=0):
	return rig.song.tracks[track].clip_slots[scene].clip


def stepseq(rig):
	return rig.selector._stepseq


def test_step_sequencer_follows_the_selected_clip(seq_rig):
	assert stepseq(seq_rig)._clip is clip(seq_rig)


def test_pad_adds_a_note_and_second_press_removes_it(seq_rig):
	rig = seq_rig
	rig.tap(0, 0)
	notes = clip(rig).note_tuples()
	assert len(notes) == 1
	pitch, start, duration, velocity, mute = notes[0]
	assert start == 0.0
	assert duration == stepseq(rig)._note_editor.quantization
	assert not mute
	rig.tap(0, 0)
	assert clip(rig).note_tuples() == ()


def test_pads_map_to_steps_left_to_right_then_down(seq_rig):
	rig = seq_rig
	step = stepseq(rig)._note_editor.quantization
	rig.tap(3, 0)
	rig.tap(0, 1)
	starts = sorted(note[1] for note in clip(rig).note_tuples())
	assert starts == [3 * step, 8 * step]


def test_note_lights_its_pad(seq_rig):
	rig = seq_rig
	before = rig.device.led(2, 0)
	rig.tap(2, 0)
	rig.tick()
	assert rig.device.led(2, 0) != before


def test_notes_added_in_live_show_on_the_pads(seq_rig):
	rig = seq_rig
	empty = rig.device.led(1, 0)
	editor = stepseq(rig)._note_editor
	pitch = editor._key_indexes[0]
	clip(rig).add_new_notes((Live.Clip.MidiNoteSpecification(pitch=pitch, start_time=editor.quantization,
		duration=editor.quantization, velocity=100, mute=False),))
	rig.tick()
	assert rig.device.led(1, 0) != empty


def test_editing_keeps_probability_of_other_notes(seq_rig):
	"""Live 11+ note attributes survive edits of other notes."""
	rig = seq_rig
	editor = stepseq(rig)._note_editor
	pitch = editor._key_indexes[0]
	clip(rig).add_new_notes((Live.Clip.MidiNoteSpecification(pitch=pitch, start_time=0.0, duration=editor.quantization,
		velocity=100, mute=False, probability=0.5, velocity_deviation=12.0),))
	rig.tick()
	rig.tap(1, 0)  # add another note
	kept = [n for n in clip(rig).get_all_notes_extended() if n.start_time == 0.0]
	assert len(kept) == 1
	assert (kept[0].probability, kept[0].velocity_deviation) == (0.5, 12.0)


def test_step_sequencer_uses_only_the_live11_note_api(seq_rig):
	rig = seq_rig
	rig.tap(0, 0)
	rig.tap(1, 0)
	rig.tap(0, 0)
	assert clip(rig).deprecated_calls == []


def test_pad_on_empty_slot_creates_a_clip(make_rig, model):
	rig = make_rig(model)  # no clips
	rig.tap_top(USER2)
	rig.tick(2)
	rig.tap(0, 0)
	rig.tick(2)
	slot = rig.song.tracks[0].clip_slots[0]
	assert slot.has_clip
	assert slot.clip.length > 0


def test_selecting_another_scene_follows_its_clip(seq_rig):
	rig = seq_rig
	rig.song.tracks[0].clip_slots[1].create_clip(4.0)
	rig.song.view.selected_scene = rig.song.scenes[1]
	rig.tick()
	assert stepseq(rig)._clip is clip(rig, 0, 1)
	rig.tap(0, 0)
	assert clip(rig, 0, 1).note_tuples() != ()
	assert clip(rig, 0, 0).note_tuples() == ()


def test_switching_slots_releases_the_old_slot_listener(seq_rig):
	rig = seq_rig
	old_slot = rig.song.tracks[0].clip_slots[0]
	listener = stepseq(rig).on_clip_slot_has_clip_changed
	assert old_slot.has_clip_has_listener(listener)
	rig.song.view.selected_scene = rig.song.scenes[1]
	rig.tick()
	assert not old_slot.has_clip_has_listener(listener)


def test_playhead_follows_the_playing_clip(seq_rig):
	rig = seq_rig
	rig.tap(0, 0)
	rig.song.tracks[0].clip_slots[0].fire()
	rig.song.advance(1.0)
	rig.tick()
	assert stepseq(rig)._playhead is not None
	assert stepseq(rig)._playhead == pytest.approx(clip(rig).playing_position)


SCALE, LOCK, QUANTIZE, MODE, NOTE_UP, NOTE_DOWN, VELOCITY, MUTE = range(8)


def long_clip_rig(make_rig, model, length=16.0):
	song = make_song(clips=[(0, 0)])
	song.tracks[0].clip_slots[0].clip.loop_end = length
	song.tracks[0].clip_slots[0].clip.end_marker = length
	rig = make_rig(model, song=song)
	rig.tap_top(USER2)
	rig.tick(2)
	return rig


def test_note_selector_pads_choose_the_pitch(seq_rig):
	rig = seq_rig
	rig.tap(0, 0)
	rig.tap(1, 7)  # note selector (lower left 4x4): next note
	rig.tap(1, 0)
	pitches = dict((n[1], n[0]) for n in clip(rig).note_tuples())
	step = stepseq(rig)._note_editor.quantization
	assert pitches[step] == pitches[0.0] + 1


def test_loop_selector_pad_shows_another_page(make_rig, model):
	rig = long_clip_rig(make_rig, model)
	# Loop selector: lower right 4x4, one pad per 8 steps; the 4-row editor shows 4 pads.
	rig.tap(4, 5)  # fifth block: second editor page
	editor = stepseq(rig)._note_editor
	assert editor._page == 1
	rig.tap(0, 0)
	assert clip(rig).note_tuples()[0][1] == 32 * editor.quantization


@pytest.mark.xfail(strict=True, reason="bug (if Live fires loop listeners synchronously, as the fake does): LoopSelectorComponent.set_clip_loop sets loop_start first, the loop_start listener re-reads the old loop_end into _loop_end, so the new loop_end is lost")
def test_double_tap_on_a_loop_pad_sets_the_clip_loop(make_rig, model):
	rig = long_clip_rig(make_rig, model)
	rig.tap(5, 4)
	rig.tap(5, 4)
	step = stepseq(rig)._note_editor.quantization
	assert (clip(rig).loop_start, clip(rig).loop_end) == (8 * step, 16 * step)


def test_quantization_button_changes_the_step_length(seq_rig):
	rig = seq_rig
	before = stepseq(rig)._note_editor.quantization
	rig.tap_side(QUANTIZE)
	assert stepseq(rig)._note_editor.quantization != before


def test_mute_shift_adds_muted_notes(seq_rig):
	rig = seq_rig
	rig.press_side(MUTE)
	rig.tap(2, 0)
	rig.release_side(MUTE)
	assert clip(rig).note_tuples()[0][4] is True


def test_velocity_button_cycles_the_note_velocity(seq_rig):
	rig = seq_rig
	rig.tap(0, 0)
	rig.tap_side(VELOCITY)
	rig.tap(1, 0)
	velocities = [n[3] for n in clip(rig).note_tuples()]
	assert velocities[0] != velocities[1]


def test_mode_button_switches_to_multinote(seq_rig):
	rig = seq_rig
	rig.tap_side(MODE)
	assert stepseq(rig)._mode == 2  # STEPSEQ_MODE_MULTINOTE
	rig.tap(0, 0)
	rig.tap(0, 7)
	pitches = sorted(set(n[0] for n in clip(rig).note_tuples()))
	assert len(pitches) == 2


def test_scale_button_held_shows_the_scale_editor(seq_rig):
	rig = seq_rig
	rig.press_side(SCALE)
	assert stepseq(rig)._mode == 10  # STEPSEQ_MODE_SCALE_EDIT
	rig.tap(1, 2)  # D
	rig.release_side(SCALE)
	assert stepseq(rig)._mode == 1
	assert stepseq(rig)._note_selector._key == 2


def test_next_track_button_follows_the_next_track(seq_rig):
	rig = seq_rig
	rig.song.tracks[1].clip_slots[0].create_clip(4.0)
	rig.tap_top(3)
	rig.tick()
	assert stepseq(rig)._clip is clip(rig, 1, 0)
