"""Pro session side buttons (modifiers): their LEDs, double taps, the shift + modifier + pad
scene actions, and what the bottom row shows and does while each one is held."""

import Live
import pytest
from harness.rig import make_song

SESSION = 4
UNDO, SHIFT, CLICK, QUANTIZE, DOUBLE, DELETE, DUPLICATE, RECORD = range(8)
BOTTOM = 7
_Q = Live.Song.Quantization
Rec_Q = Live.Song.RecordingQuantization


@pytest.fixture
def pro_rig(make_rig, model):
    rig = make_rig(model, song=make_song(clips=[(0, 0), (1, 1), (2, 2)]))
    rig.tap_top(SESSION)
    rig.tick()
    assert rig.selector._pro_session_on
    return rig


def session(rig):
    return rig.selector._session


def side_names(rig):
    return [button.states[True] for button in rig.selector._side_buttons]


def double_tap_side(rig, index):
    rig.tap_side(index)
    rig.tap_side(index)


def held(rig, side, action):
    rig.press_side(side)
    result = action()
    rig.release_side(side)
    return result


@pytest.fixture
def bottom_row(pro_rig, monkeypatch):
    """What the bottom-row buttons were last sent (send_value), by index."""
    sent = {}
    for index, button in enumerate(session(pro_rig)._stop_track_clip_buttons):

        def record(value, *a, _index=index, **k):
            sent[_index] = value

        monkeypatch.setattr(button, "send_value", record)
    return sent


def test_side_buttons_get_their_pro_session_colours(pro_rig):
    assert side_names(pro_rig) == [
        "ProSession.Undo.On",
        "ProSession.Shift.On",
        "ProSession.Click.On",
        "ProSession.Quantize.On",
        "ProSession.Double.On",
        "ProSession.Delete.On",
        "ProSession.Duplicate.On",
        "ProSession.SessionRec.On",
    ]


def test_shift_record_toggles_autorecord_and_its_colour(pro_rig):
    held(pro_rig, SHIFT, lambda: pro_rig.tap_side(RECORD))
    assert "Autorecord: On" in pro_rig.messages
    assert side_names(pro_rig)[RECORD] == "ProSession.SessionRecMode.On"
    held(pro_rig, SHIFT, lambda: pro_rig.tap_side(RECORD))
    assert "Autorecord: Off" in pro_rig.messages
    assert side_names(pro_rig)[RECORD] == "ProSession.SessionRec.On"


def test_record_tap_toggles_session_record_and_long_press_does_not(pro_rig):
    pro_rig.tap_side(RECORD)
    assert pro_rig.song.session_record
    assert "SESSION RECORD ON" in pro_rig.messages
    pro_rig.press_side(RECORD)
    pro_rig.wait(0.6)
    pro_rig.release_side(RECORD)
    assert pro_rig.song.session_record


def test_record_tap_after_arming_does_not_record(pro_rig):
    held(pro_rig, RECORD, lambda: pro_rig.tap(1, BOTTOM))
    assert pro_rig.song.tracks[1].arm
    assert not pro_rig.song.session_record


def test_autorecord_pad_arms_the_track_and_launches(pro_rig):
    held(pro_rig, SHIFT, lambda: pro_rig.tap_side(RECORD))
    pro_rig.tap(4, 0)
    assert pro_rig.song.tracks[4].arm
    assert pro_rig.song.view.selected_track is pro_rig.song.tracks[4]
    assert pro_rig.song.tracks[4].clip_slots[0].fire_count == 1


def test_double_tap_on_shift_hides_the_detail_view(pro_rig):
    view = Live.Application.get_application().view
    view.show_view("Detail")
    pro_rig.tap_side(SHIFT)
    assert view.is_view_visible("Detail")
    pro_rig.tap_side(SHIFT)
    assert not view.is_view_visible("Detail")


def test_double_tap_on_quantize_toggles_record_quantization(pro_rig):
    song = pro_rig.song
    song.midi_recording_quantization = Rec_Q.rec_q_eight
    double_tap_side(pro_rig, QUANTIZE)
    assert song.midi_recording_quantization == Rec_Q.rec_q_no_q
    pro_rig.wait(0.5)
    double_tap_side(pro_rig, QUANTIZE)
    assert song.midi_recording_quantization == Rec_Q.rec_q_eight


def test_double_tap_on_double_toggles_fixed_length(pro_rig):
    double_tap_side(pro_rig, DOUBLE)
    assert session(pro_rig)._fixed_length_on
    assert "Fixed length: ON: 1 Bar" in pro_rig.messages


def test_double_tap_on_delete_unmutes_every_track(pro_rig):
    song = pro_rig.song
    song.tracks[1].mute = True
    song.return_tracks[0].mute = True
    double_tap_side(pro_rig, DELETE)
    assert not song.tracks[1].mute
    assert not song.return_tracks[0].mute


def test_double_tap_on_duplicate_unsolos_every_track(pro_rig):
    song = pro_rig.song
    song.tracks[2].solo = True
    double_tap_side(pro_rig, DUPLICATE)
    assert not song.tracks[2].solo


def test_slow_taps_are_not_double_taps(pro_rig):
    song = pro_rig.song
    song.tracks[2].solo = True
    pro_rig.tap_side(DUPLICATE)
    pro_rig.wait(0.5)
    pro_rig.tap_side(DUPLICATE)
    assert song.tracks[2].solo


def test_modifier_messages(pro_rig):
    for side, message in (
        (SHIFT, "Select clip - [ Set launch quantization -> now: ON: 1 Bar ]"),
        (CLICK, "Copy/paste clip - [ Tempo ]"),
        (QUANTIZE, "Quantize clip - [ Record quantization -> now: OFF ]"),
        (DOUBLE, "Double midi clip - [ Clip fixed length recording -> now: OFF ]"),
        (DELETE, "Delete clip  - [ Mute Tracks ]"),
        (DUPLICATE, "Duplicate clip - [ Solo track ]"),
        (RECORD, "Record clip -  [ Arm track ]"),
    ):
        pro_rig.press_side(side)
        assert pro_rig.messages[-1] == message
        pro_rig.release_side(side)
        pro_rig.wait(0.5)


def test_shifted_modifier_messages(pro_rig):
    pro_rig.press_side(SHIFT)
    for side, message in (
        (CLICK, "Launch scene - [ Tempo ]"),
        (QUANTIZE, "Create Scene - [ Record quantization -> now: OFF ]"),
        (DOUBLE, "Capture scene - [ Clip fixed length recording -> now: OFF ]"),
        (DELETE, "Delete scene"),
        (DUPLICATE, "Duplicate scene"),
    ):
        pro_rig.press_side(side)
        assert pro_rig.messages[-1] == message
        pro_rig.release_side(side)
        pro_rig.wait(0.5)
    pro_rig.release_side(SHIFT)


def shifted(rig, side, action):
    rig.press_side(SHIFT)
    held(rig, side, action)
    rig.release_side(SHIFT)


def test_shift_pad_selects_the_clip(pro_rig):
    pro_rig.tap(1, 1)  # launches; the shift tap below selects
    held(pro_rig, SHIFT, lambda: pro_rig.tap(2, 2))
    assert pro_rig.song.view.highlighted_clip_slot is pro_rig.song.tracks[2].clip_slots[2]


def test_shift_click_pad_launches_the_scene(pro_rig):
    shifted(pro_rig, CLICK, lambda: pro_rig.tap(3, 1))
    assert pro_rig.song.scenes[1].fire_count == 1


def test_shift_quantize_pad_creates_a_scene_below(pro_rig):
    shifted(pro_rig, QUANTIZE, lambda: pro_rig.tap(0, 1))
    assert len(pro_rig.song.scenes) == 9
    assert pro_rig.song.view.selected_scene is pro_rig.song.scenes[2]


def test_shift_double_pad_captures_the_scene(pro_rig):
    shifted(pro_rig, DOUBLE, lambda: pro_rig.tap(0, 2))
    assert len(pro_rig.song.scenes) == 9
    assert any(m.startswith("Captured to scene") for m in pro_rig.messages)


def test_shift_duplicate_pad_duplicates_the_scene(pro_rig):
    shifted(pro_rig, DUPLICATE, lambda: pro_rig.tap(0, 1))
    assert len(pro_rig.song.scenes) == 9
    assert pro_rig.song.tracks[1].clip_slots[2].has_clip
    assert "Scene duplicated" in pro_rig.messages


def test_bottom_row_shows_track_states_under_record_duplicate_delete(pro_rig, bottom_row):
    song = pro_rig.song
    song.tracks[0].arm = True
    song.tracks[1].solo = True
    song.tracks[2].mute = True
    pro_rig.press_side(RECORD)
    assert [bottom_row[i] for i in range(3)] == ["Recording.On", "Recording.Off", "Recording.Off"]
    pro_rig.release_side(RECORD)
    pro_rig.press_side(DUPLICATE)
    assert [bottom_row[i] for i in range(3)] == ["Mixer.Solo.Off", "Mixer.Solo.On", "Mixer.Solo.Off"]
    pro_rig.release_side(DUPLICATE)
    pro_rig.press_side(DELETE)
    assert [bottom_row[i] for i in range(3)] == [
        "TrackController.Mute.On",
        "TrackController.Mute.On",
        "TrackController.Mute.Off",
    ]
    pro_rig.release_side(DELETE)


def test_bottom_row_shows_settings_under_shift_quantize_click_double(pro_rig, bottom_row):
    pro_rig.press_side(SHIFT)
    assert [bottom_row[i] for i in range(8)] == ["LaunchQuant.On"] + ["LaunchQuant.PlusMinus.On"] * 2 + [
        "LaunchQuant.Value.Off",
        "LaunchQuant.Value.On",  # 1 bar, the song's default
        "LaunchQuant.Value.Off",
        "LaunchQuant.Value.Off",
        "LaunchQuant.Value.Off",
    ]
    pro_rig.release_side(SHIFT)
    pro_rig.wait(0.5)
    pro_rig.song.midi_recording_quantization = Rec_Q.rec_q_eight
    pro_rig.press_side(QUANTIZE)
    assert [bottom_row[i] for i in range(8)] == ["RecQuant.On"] + ["RecQuant.PlusMinus.On"] * 2 + [
        "RecQuant.Value.Off",
        "RecQuant.Value.On",
        "RecQuant.Value.Off",
        "RecQuant.Value.Off",
        "RecQuant.Value.Off",
    ]
    pro_rig.release_side(QUANTIZE)
    pro_rig.wait(0.5)
    pro_rig.press_side(CLICK)
    assert [bottom_row[i] for i in range(8)] == [
        "Metronome.Off",
        "Metronome.Nudge",
        "Metronome.Nudge",
        "Metronome.DeltaFive",
        "Metronome.DeltaOne",
        "Metronome.DeltaOne",
        "Metronome.DeltaFive",
        "Metronome.DeltaOne",
    ]
    pro_rig.release_side(CLICK)
    pro_rig.wait(0.5)
    pro_rig.press_side(DOUBLE)
    assert [bottom_row[i] for i in range(8)] == ["FixedLength.Off"] + ["FixedLength.PlusMinus.Off"] * 2 + [
        "FixedLength.Value.Off",
        "FixedLength.Value.Idle",
        "FixedLength.Value.Off",
        "FixedLength.Value.Off",
        "FixedLength.Value.Off",
    ]
    pro_rig.release_side(DOUBLE)


def test_click_row_nudges_toggles_the_metronome_and_taps_tempo(pro_rig):
    song = pro_rig.song
    pro_rig.press_side(CLICK)
    pro_rig.press(1, BOTTOM)
    assert song.nudge_down
    pro_rig.release(1, BOTTOM)
    assert not song.nudge_down
    pro_rig.press(2, BOTTOM)
    assert song.nudge_up
    pro_rig.release(2, BOTTOM)
    pro_rig.tap(0, BOTTOM)
    assert song.metronome
    pro_rig.tap(7, BOTTOM)
    pro_rig.tap(7, BOTTOM)
    assert song.tap_count == 2
    pro_rig.tap(3, BOTTOM)
    assert song.tempo == 115.0
    pro_rig.release_side(CLICK)


def test_shift_row_steps_launch_quantization(pro_rig):
    song = pro_rig.song
    song.clip_trigger_quantization = _Q.q_bar
    pro_rig.press_side(SHIFT)
    pro_rig.tap(2, BOTTOM)  # finer
    assert song.clip_trigger_quantization == _Q.q_half
    pro_rig.tap(1, BOTTOM)  # coarser
    pro_rig.tap(1, BOTTOM)
    assert song.clip_trigger_quantization == _Q.q_2_bars
    pro_rig.tap(0, BOTTOM)  # off
    assert song.clip_trigger_quantization == _Q.q_no_q
    pro_rig.tap(0, BOTTOM)  # back on, with the last rate
    assert song.clip_trigger_quantization == _Q.q_2_bars
    pro_rig.tap(3, BOTTOM)  # same fixed rate again: off
    assert song.clip_trigger_quantization == _Q.q_no_q
    pro_rig.release_side(SHIFT)


def test_quantize_row_steps_record_quantization(pro_rig):
    song = pro_rig.song
    song.midi_recording_quantization = Rec_Q.rec_q_eight
    pro_rig.press_side(QUANTIZE)
    pro_rig.tap(2, BOTTOM)
    assert song.midi_recording_quantization == Rec_Q.rec_q_eight_triplet
    pro_rig.tap(1, BOTTOM)
    pro_rig.tap(1, BOTTOM)
    assert song.midi_recording_quantization == Rec_Q.rec_q_quarter
    pro_rig.tap(0, BOTTOM)
    assert song.midi_recording_quantization == Rec_Q.rec_q_no_q
    pro_rig.tap(6, BOTTOM)
    assert song.midi_recording_quantization == Rec_Q.rec_q_sixtenth
    pro_rig.release_side(QUANTIZE)


def test_double_row_steps_fixed_length(pro_rig):
    s = session(pro_rig)
    pro_rig.press_side(DOUBLE)
    pro_rig.tap(0, BOTTOM)
    assert s._fixed_length_on and s._fixed_length == 1
    pro_rig.tap(1, BOTTOM)
    assert s._fixed_length == 0.5
    pro_rig.tap(1, BOTTOM)
    pro_rig.tap(1, BOTTOM)
    assert s._fixed_length == 0.25
    assert pro_rig.messages[-1] == "Fixed length: ON: 1 Beat"
    pro_rig.tap(2, BOTTOM)
    pro_rig.tap(2, BOTTOM)
    pro_rig.tap(2, BOTTOM)
    assert s._fixed_length == 2
    assert pro_rig.messages[-1] == "Fixed length: ON: 2 Bars"
    pro_rig.tap(7, BOTTOM)  # 8 bars
    assert s._fixed_length == 8
    pro_rig.tap(7, BOTTOM)  # again: off
    assert not s._fixed_length_on
    pro_rig.release_side(DOUBLE)


def test_quantize_pad_message_names_the_grid(pro_rig):
    pro_rig.song.midi_recording_quantization = Rec_Q.rec_q_sixtenth
    held(pro_rig, QUANTIZE, lambda: pro_rig.tap(1, 1))
    assert "Clip quantized to 1/16" in pro_rig.messages


def test_live_quantization_changes_are_reported(pro_rig):
    pro_rig.song.clip_trigger_quantization = _Q.q_quarter
    assert pro_rig.messages[-1] == "Launch quantization: ON: 1/4"
    pro_rig.song.midi_recording_quantization = Rec_Q.rec_q_eight
    assert pro_rig.messages[-1] == "Record quantization: ON: 1/8"
    pro_rig.song.midi_recording_quantization = Rec_Q.rec_q_no_q
    assert pro_rig.messages[-1] == "Record quantization: OFF"


def test_modifiers_do_nothing_outside_pro_session(pro_rig):
    pro_rig.tap_top(SESSION)
    assert not pro_rig.selector._pro_session_on
    pro_rig.press_side(DELETE)
    assert not session(pro_rig).modifiers.delete.held
    pro_rig.release_side(DELETE)
