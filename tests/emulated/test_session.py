"""Session mode: clip launch pads, scene launch buttons, navigation."""

import sys

import pytest
from harness.rig import make_song

UP, DOWN, LEFT, RIGHT = 0, 1, 2, 3


def skin_value(rig, key):
    return rig.surface._skin[key].midi_value


def stopped_clip_value(rig, clip):
    """RGB models show a stopped clip in its own colour, MK1 in the skin colour."""
    if rig.surface._mk2_rgb or rig.surface._mk3_rgb or rig.surface._lpx:
        colors = sys.modules["Launchpad95.ColorsMK2"]
        from _Framework.ClipSlotComponent import find_nearest_color

        return find_nearest_color(colors.RGB_COLOR_TABLE, clip.color)
    return skin_value(rig, "Session.ClipStopped")


@pytest.fixture
def session_rig(make_rig, model):
    song = make_song(clips=[(0, 0), (1, 0), (2, 3), (7, 7)], num_tracks=16, num_scenes=16)
    rig = make_rig(model, song=song)
    rig.tick()
    return rig


def test_pads_show_stopped_clips_and_empty_slots(session_rig):
    rig = session_rig
    for x, y in [(0, 0), (1, 0), (2, 3), (7, 7)]:
        clip = rig.song.tracks[x].clip_slots[y].clip
        assert rig.device.led(x, y) == stopped_clip_value(rig, clip), (x, y)
    assert rig.device.led(3, 3) != rig.device.led(0, 0)
    assert rig.device.led(3, 3) in (0, skin_value(rig, "DefaultButton.Disabled"))


def test_pressing_a_pad_fires_its_clip(session_rig):
    rig = session_rig
    slot = rig.song.tracks[1].clip_slots[0]
    rig.press(1, 0)
    rig.tick()
    assert slot.fire_count == 1
    assert slot.clip.is_triggered
    assert rig.device.led(1, 0) == skin_value(rig, "Session.ClipTriggeredPlay")
    rig.release(1, 0)
    rig.song.advance(1.0)
    rig.tick()
    assert slot.clip.is_playing
    assert rig.device.led(1, 0) == skin_value(rig, "Session.ClipStarted")


def test_pressing_an_empty_pad_stops_the_track(session_rig):
    rig = session_rig
    rig.tap(0, 0)
    rig.song.advance(1.0)
    assert rig.song.tracks[0].clip_slots[0].is_playing
    rig.tap(0, 5)
    rig.song.advance(1.0)
    rig.tick()
    assert not rig.song.tracks[0].clip_slots[0].is_playing
    assert rig.device.led(0, 0) == stopped_clip_value(rig, rig.song.tracks[0].clip_slots[0].clip)


def test_scene_button_launches_the_scene(session_rig):
    rig = session_rig
    rig.tap_side(0)
    rig.song.advance(1.0)
    rig.tick()
    assert rig.song.scenes[0].fire_count == 1
    assert rig.song.tracks[0].clip_slots[0].is_playing
    assert rig.song.tracks[1].clip_slots[0].is_playing


def test_arrows_move_the_session_box(session_rig):
    rig = session_rig
    session = rig.selector.session_component()
    assert (session.track_offset(), session.scene_offset()) == (0, 0)
    rig.tap_top(RIGHT)
    rig.tick()
    assert session.track_offset() == 1
    rig.tap_top(DOWN)
    rig.tick()
    assert session.scene_offset() == 1
    # The clip at track 2 / scene 3 now shows on pad (1, 2).
    assert rig.device.led(1, 2) == stopped_clip_value(rig, rig.song.tracks[2].clip_slots[3].clip)
    assert rig.c_instance.session_highlight[:4] == (1, 1, 8, 8)
    rig.tap_top(LEFT)
    rig.tap_top(UP)
    rig.tick()
    assert (session.track_offset(), session.scene_offset()) == (0, 0)


def test_arrows_stop_at_the_session_edges(session_rig):
    rig = session_rig
    session = rig.selector.session_component()
    rig.tap_top(LEFT)
    rig.tap_top(UP)
    assert (session.track_offset(), session.scene_offset()) == (0, 0)
    for _ in range(20):
        rig.tap_top(RIGHT)
        rig.tap_top(DOWN)
    assert session.track_offset() == 15  # the last track may scroll to the left edge
    assert session.scene_offset() == 15


def test_new_clip_lights_its_pad(session_rig):
    rig = session_rig
    rig.song.tracks[5].clip_slots[5].create_clip(4.0)
    rig.tick()
    assert rig.device.led(5, 5) == stopped_clip_value(rig, rig.song.tracks[5].clip_slots[5].clip)


def test_pro_session_last_row_stops_tracks(session_rig):
    rig = session_rig
    rig.tap_top(4)  # short press on Session while in session mode: pro session
    assert rig.selector._pro_session_on
    rig.tap(0, 0)
    rig.song.advance(1.0)
    assert rig.song.tracks[0].clip_slots[0].is_playing
    rig.tap(0, 7)  # bottom row: stop clip buttons
    rig.song.advance(1.0)
    assert not rig.song.tracks[0].clip_slots[0].is_playing


def test_boot_leaves_the_framework_scene_component_alone(make_rig, model):
    """Other control surfaces in Live share _Framework: the script must not patch it."""
    from _Framework.ClipSlotComponent import ClipSlotComponent
    from _Framework.SceneComponent import SceneComponent

    make_rig(model)
    assert SceneComponent.clip_slot_component_type is ClipSlotComponent
