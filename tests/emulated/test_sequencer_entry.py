"""Entering, leaving and re-entering the step sequencers must not change the selected clip:
its notes (times and lengths) and its loop stay as they were. (In Launchpad_Pro95, entering
the melodic sequencer moved every note to time 0 with length 0 and shrank the loop.)"""
import Live
import pytest

from harness.rig import make_song

SESSION = 4
USER2 = 6
QUANTIZE = 2

NOTES = [
	(36, 0.0, 0.25, 100),
	(40, 1.0, 0.5, 90),
	(43, 2.5, 1.0, 80),
	(38, 3.75, 0.125, 70),
]


def song_with_notes():
	song = make_song(clips=[(0, 0)])
	clip = song.tracks[0].clip_slots[0].clip
	clip.add_new_notes(tuple(
		Live.Clip.MidiNoteSpecification(pitch=p, start_time=t, duration=d, velocity=v, mute=False)
		for p, t, d, v in NOTES))
	return song


def clip_state(rig):
	clip = rig.song.tracks[0].clip_slots[0].clip
	return (sorted(clip.note_tuples()), clip.loop_start, clip.loop_end, clip.start_marker, clip.end_marker)


def enter_user2_mode(rig, mode_index):
	"""From session mode, user 2 opens the sub mode used last; a second tap switches it."""
	rig.tap_top(SESSION)
	rig.tick()
	rig.tap_top(USER2)
	rig.tick(2)
	if rig.selector._mode_index != mode_index:
		rig.tap_top(USER2)
		rig.tick(2)
	assert rig.selector._mode_index == mode_index


def enter_drum(rig):
	enter_user2_mode(rig, 6)


def enter_melodic(rig):
	enter_user2_mode(rig, 7)


def test_entering_the_melodic_sequencer_keeps_the_clip(make_rig, model):
	rig = make_rig(model, song=song_with_notes())
	before = clip_state(rig)
	assert before[2] == 4.0
	enter_melodic(rig)
	assert clip_state(rig) == before


def test_leaving_and_reentering_both_sequencers_keeps_the_clip(make_rig, model):
	rig = make_rig(model, song=song_with_notes())
	before = clip_state(rig)
	for _ in range(2):
		enter_drum(rig)
		assert clip_state(rig) == before
		enter_melodic(rig)
		assert clip_state(rig) == before
	rig.tap_top(SESSION)
	rig.tick()
	assert clip_state(rig) == before


@pytest.mark.parametrize("mode", ["drum", "melodic"])
def test_reentering_keeps_a_chosen_quantization_and_the_clip(make_rig, model, mode):
	rig = make_rig(model, song=song_with_notes())
	enter = enter_melodic if mode == "melodic" else enter_drum
	enter(rig)
	seq = rig.selector._stepseq2 if mode == "melodic" else rig.selector._stepseq
	rig.tap_side(QUANTIZE)  # a change the user makes on purpose
	chosen = seq._quantization
	after_change = clip_state(rig)
	enter_drum(rig)
	enter_melodic(rig)
	enter(rig)
	assert seq._quantization == chosen
	assert clip_state(rig) == after_change
