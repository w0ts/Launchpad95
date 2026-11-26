"""Settings.SESSION__CLIP_COLOR_WHEN_PLAYING (issue #98): on the RGB Launchpads a triggered clip
blinks and a playing clip pulses in its own clip colour instead of the skin's green. Off by
default; the MK1 models have no clip colours and keep the skin colours."""

import sys

import pytest
from harness.rig import make_song

PINK, BLUE = 16726484, 1698303  # Live clip colours
SESSION = 4


def is_rgb(rig):
    return rig.surface._mk2_rgb or rig.surface._mk3_rgb or rig.surface._lpx


def colour_value(clip):
    """The pad value of a clip's colour on the RGB models."""
    colors = sys.modules["Launchpad95.ColorsMK2"]
    from _Framework.ClipSlotComponent import find_nearest_color

    return colors.CLIP_COLOR_TABLE.get(clip.color) or find_nearest_color(colors.RGB_COLOR_TABLE, clip.color)


def skin_value(rig, key):
    return rig.surface._skin[key].midi_value


@pytest.fixture
def clip_colours(monkeypatch):
    settings = sys.modules["Launchpad95.Settings"].Settings
    monkeypatch.setattr(settings, "SESSION__CLIP_COLOR_WHEN_PLAYING", True)


@pytest.fixture
def colour_rig(make_rig, model):
    rig = make_rig(model, song=make_song(clips=[(0, 0), (1, 0)]))
    rig.song.tracks[1].clip_slots[0].clip.color = PINK
    rig.tick()
    return rig


def launch(rig, x, y):
    """Tap a pad; return its LED while triggered and once playing."""
    rig.tap(x, y)
    rig.tick()
    triggered = rig.device.grid_led(x, y)
    triggered = (triggered.flash, triggered.pulse)
    rig.song.advance(1.0)
    rig.tick()
    playing = rig.device.grid_led(x, y)
    return triggered, (playing.flash, playing.pulse)


def test_playing_clip_blinks_then_pulses_in_its_colour(colour_rig, clip_colours):
    rig = colour_rig
    clip = rig.song.tracks[1].clip_slots[0].clip
    triggered, playing = launch(rig, 1, 0)
    assert clip.is_playing
    if is_rgb(rig):
        assert triggered == (colour_value(clip), None)
        assert playing == (None, colour_value(clip))
    else:
        assert rig.device.led(1, 0) == skin_value(rig, "Session.ClipStarted")


def test_option_off_keeps_the_skin_green(colour_rig):
    rig = colour_rig
    triggered, playing = launch(rig, 1, 0)
    if is_rgb(rig):
        assert triggered == (skin_value(rig, "Session.ClipTriggeredPlay"), None)
        assert playing == (None, skin_value(rig, "Session.ClipStarted"))
    else:
        assert rig.device.led(1, 0) == skin_value(rig, "Session.ClipStarted")


def test_recolouring_a_playing_clip_updates_its_pulse(colour_rig, clip_colours, model):
    rig = colour_rig
    launch(rig, 1, 0)
    clip = rig.song.tracks[1].clip_slots[0].clip
    clip.color = BLUE
    rig.tick()
    if is_rgb(rig):
        assert rig.device.grid_led(1, 0).pulse == colour_value(clip)
        assert colour_value(clip) != rig.device.led(0, 0)  # not the other clip's colour by chance


def test_stopping_brings_back_the_static_colour(colour_rig, clip_colours):
    rig = colour_rig
    launch(rig, 1, 0)
    rig.tap(1, 5)  # an empty pad stops the track
    rig.song.advance(1.0)
    rig.tick()
    led = rig.device.grid_led(1, 0)
    if is_rgb(rig):
        clip = rig.song.tracks[1].clip_slots[0].clip
        assert (led.static, led.flash, led.pulse) == (colour_value(clip), None, None)


def test_pro_session_pads_pulse_in_their_colour(colour_rig, clip_colours):
    rig = colour_rig
    rig.tap_top(SESSION)
    rig.tick()
    assert rig.selector._pro_session_on
    clip = rig.song.tracks[1].clip_slots[0].clip
    triggered, playing = launch(rig, 1, 0)
    if is_rgb(rig):
        assert triggered == (colour_value(clip), None)
        assert playing == (None, colour_value(clip))
    else:
        assert rig.device.led(1, 0) == skin_value(rig, "ProSession.ClipStarted")
