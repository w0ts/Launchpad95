"""Melodic step sequencer (user 2 button, second sub mode): one column per step, rows 0-6
are the 7 scale degrees (top row = highest), row 7 is the loop selector."""
import Live
import pytest

from harness.rig import make_song

USER2 = 6


@pytest.fixture
def melodic_rig(make_rig, model):
	rig = make_rig(model, song=make_song(clips=[(0, 0)]))
	rig.tap_top(USER2)
	rig.tap_top(USER2)
	rig.tick(2)
	assert rig.selector._mode_index == 7
	return rig


def clip(rig):
	return rig.song.tracks[0].clip_slots[0].clip


def editor(rig):
	return rig.selector._stepseq2._note_editor


def test_pad_enters_a_note_at_its_step_and_degree(melodic_rig):
	rig = melodic_rig
	ed = editor(rig)
	rig.tap(2, 6)  # third step, lowest degree
	notes = clip(rig).note_tuples()
	assert len(notes) == 1
	pitch, start, duration, velocity, mute = notes[0]
	assert start == pytest.approx(2 * ed.quantization)
	assert pitch == ed._key_indexes[0] + 12 * (ed._notes_octaves[2] - 2)
	assert not mute


def test_higher_row_gives_a_higher_degree(melodic_rig):
	rig = melodic_rig
	rig.tap(0, 6)
	rig.tap(1, 0)
	by_start = dict((n[1], n[0]) for n in clip(rig).note_tuples())
	q = editor(rig).quantization
	assert by_start[q] > by_start[0.0]


def test_second_press_clears_the_note(melodic_rig):
	rig = melodic_rig
	rig.tap(4, 3)
	assert len(clip(rig).note_tuples()) == 1
	rig.tap(4, 3)
	assert clip(rig).note_tuples() == ()


def test_note_lights_its_pad(melodic_rig):
	rig = melodic_rig
	before = rig.device.led(5, 2)
	rig.tap(5, 2)
	rig.tick()
	assert rig.device.led(5, 2) != before


def test_existing_notes_are_parsed_into_steps(make_rig, model):
	song = make_song(clips=[(0, 0)])
	song.tracks[0].clip_slots[0].clip.add_new_notes((Live.Clip.MidiNoteSpecification(
		pitch=36, start_time=0.0, duration=0.25, velocity=100, mute=False),))
	rig = make_rig(model, song=song)
	rig.tap_top(USER2)
	rig.tap_top(USER2)
	rig.tick(2)
	ed = editor(rig)
	assert ed._notes_pitches[0 * 7 + 0] == 1


@pytest.mark.xfail(strict=True, reason="bug: MelodicNoteEditorComponent._parse_notes indexes fixed 128-entry lists by step, so a note after step 127 (beat 32 at 1/16) raises IndexError")
def test_notes_after_step_128_do_not_crash(make_rig, model):
	song = make_song(clips=[(0, 0)])
	slot_clip = song.tracks[0].clip_slots[0].clip
	slot_clip.loop_end = 64.0
	slot_clip.add_new_notes((Live.Clip.MidiNoteSpecification(pitch=36, start_time=40.0, duration=0.25,
		velocity=100, mute=False),))
	rig = make_rig(model, song=song)
	rig.tap_top(USER2)
	rig.tap_top(USER2)
	rig.tick(2)
	assert editor(rig)._notes_pitches[160 * 7] == 1


def test_melodic_sequencer_uses_only_the_live11_note_api(melodic_rig):
	rig = melodic_rig
	rig.tap(0, 0)
	rig.tap(0, 0)
	assert clip(rig).deprecated_calls == []
