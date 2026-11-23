"""Instrument mode (user 1 button): pads play notes on the selected track. Their MIDI is
translated to channel 11+ and not forwarded to the script, so Live sends it to the track."""
import pytest

USER1 = 5
NOTE_ON = 0x90


@pytest.fixture
def instrument_rig(rig):
	rig.tap_top(USER1)
	rig.tick(2)
	assert rig.selector._mode_index == 4
	return rig


def pattern_note(rig, x, y):
	controller = rig.selector._instrument_controller
	return controller._scales.get_pattern().note(x, 7 - y)


def test_pads_play_notes_to_the_track(instrument_rig):
	rig = instrument_rig
	note = pattern_note(rig, 0, 7)
	assert note.index is not None
	assert rig.press(0, 7, velocity=100) == "track"
	status, pitch, velocity = rig.track_input[-1]
	assert status & 0xF0 == NOTE_ON
	assert status & 0x0F >= 11
	assert (pitch, velocity) == (note.index, 100)
	rig.release(0, 7)
	assert rig.track_input[-1][1:] == (note.index, 0)


def test_pads_up_a_row_play_a_higher_note(instrument_rig):
	rig = instrument_rig
	rig.tap(0, 7)
	rig.tap(0, 6)
	low, high = rig.track_input[0][1], rig.track_input[2][1]
	assert high > low


def test_instrument_mode_controls_the_selected_track(instrument_rig):
	rig = instrument_rig
	assert rig.c_instance.controlled_track is rig.song.view.selected_track


def test_root_note_pads_use_the_root_colour(instrument_rig):
	rig = instrument_rig
	root_value = rig.surface._skin["Note.Pads.Root"].midi_value
	for x in range(8):
		for y in range(2, 8):
			if pattern_note(rig, x, y).root:
				assert rig.device.led(x, y) == root_value, (x, y)


def test_song_root_note_change_moves_the_pad_notes(instrument_rig):
	rig = instrument_rig
	before = pattern_note(rig, 0, 7).index
	rig.song.root_note = 2  # D
	rig.tick(2)
	assert rig.selector._instrument_controller._scales._key == 2
	assert pattern_note(rig, 0, 7).index == before + 2
	rig.tap(0, 7)
	assert rig.track_input[0][1] == before + 2


def test_leaving_instrument_mode_restores_pad_channels(instrument_rig):
	rig = instrument_rig
	rig.tap_top(4)
	rig.tick(2)
	assert rig.press(0, 0) == "script"
	rig.release(0, 0)


SCALES, UNDO, OCTAVE_UP, OCTAVE_DOWN, START_STOP, LOCK, SOLO, RECORD = range(8)
NEXT_TRACK = 3


def test_octave_buttons_shift_the_pads_by_an_octave(instrument_rig):
	rig = instrument_rig
	low = pattern_note(rig, 0, 7).index
	rig.tap_side(OCTAVE_UP)
	assert pattern_note(rig, 0, 7).index == low + 12
	rig.tap_side(OCTAVE_DOWN)
	rig.tap_side(OCTAVE_DOWN)
	assert pattern_note(rig, 0, 7).index == low - 12


def test_lowest_octave_does_not_wrap_around(instrument_rig):
	rig = instrument_rig
	for _ in range(10):
		rig.tap_side(OCTAVE_DOWN)
	notes = [pattern_note(rig, 0, y).index for y in range(7, -1, -1)]
	played = [n for n in notes if n is not None]  # None: below MIDI note 0, the pad plays nothing
	assert played and played == sorted(played)
	assert all(0 <= n < 128 for n in played)


def test_scale_editor_sets_the_song_key_and_scale(instrument_rig):
	rig = instrument_rig
	rig.press_side(SCALES)
	rig.tap(1, 2)  # white keys row: D
	rig.tap(1, 4)  # second scale of the list
	rig.release_side(SCALES)
	assert rig.song.root_note == 2
	assert rig.song.scale_name == rig.selector._instrument_controller._scales._modus_names[1]


def test_next_track_button_moves_the_controlled_track(instrument_rig):
	rig = instrument_rig
	rig.tap_top(NEXT_TRACK)
	rig.tick()
	assert rig.song.view.selected_track is rig.song.tracks[1]
	assert rig.c_instance.controlled_track is rig.song.tracks[1]


def test_solo_button_solos_the_selected_track(instrument_rig):
	rig = instrument_rig
	rig.tap_side(SOLO)
	assert rig.song.tracks[0].solo
	rig.press_side(SOLO)
	rig.wait(1.0)  # long press: mute instead
	rig.release_side(SOLO)
	assert rig.song.tracks[0].mute


def test_start_stop_button_fires_the_selected_clip(make_rig, model):
	from harness.rig import make_song

	rig = make_rig(model, song=make_song(clips=[(0, 0)]))
	rig.tap_top(USER1)
	rig.tap_side(START_STOP)
	assert rig.song.tracks[0].clip_slots[0].fire_count == 1


def test_drum_rack_track_gets_the_drum_layout(make_rig, model):
	import Live
	from harness.rig import make_song

	song = make_song()
	rack = Live.RackDevice.RackDevice(name="Drums", drum=True)
	rack.canonical_parent = song.tracks[0]
	song.tracks[0].devices = (rack,)
	rig = make_rig(model, song=song)
	rig.tap_top(USER1)
	rig.tick(2)
	scales = rig.selector._instrument_controller._scales
	assert scales.is_drumrack
	rig.tap(0, 7)
	rig.tap(1, 7)
	rig.tap(0, 6)
	first, second, above = (rig.track_input[i][1] for i in (0, 2, 4))
	assert second == first + 1  # 4x4 blocks: next pad to the right is the next drum
	assert above == first + 4


def test_quick_scale_turns_the_top_rows_into_scale_buttons(instrument_rig):
	rig = instrument_rig
	rig.press_side(SCALES)
	rig.tap(7, 1)  # quick scale on
	rig.release_side(SCALES)
	scales = rig.selector._instrument_controller._scales
	assert scales.is_quick_scale
	assert rig.press(0, 7) == "track"  # lower rows still play
	rig.release(0, 7)
	assert rig.press(1, 1) == "script"  # top rows: key / mode buttons
	rig.release(1, 1)
	assert rig.song.root_note != 0 or rig.song.scale_name != "Major"


def test_leaving_instrument_mode_stops_following_the_song_scale(instrument_rig):
	rig = instrument_rig
	controller = rig.selector._instrument_controller
	assert rig.song.root_note_has_listener(controller.handle_root_note_changed)
	rig.tap_top(4)  # session
	rig.tick(2)
	assert not controller.is_enabled()
	assert not rig.song.root_note_has_listener(controller.handle_root_note_changed)
	assert not rig.song.scale_name_has_listener(controller.handle_scale_name_changed)
