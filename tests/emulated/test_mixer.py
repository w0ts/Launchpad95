"""Mixer mode (mixer button). Overview: rows 4-7 of each column are stop/mute/solo/arm of
its track; side buttons 0-3 open the volume, pan, send A and send B sliders."""

import pytest

MIXER = 7
VOLUME, PAN, SEND_A, SEND_B = 0, 1, 2, 3


@pytest.fixture
def mixer_rig(rig):
    rig.tap_top(MIXER)
    rig.tick(2)
    assert rig.selector._mode_index == 3
    return rig


def track(rig, index):
    return rig.song.tracks[index]


def test_overview_mute_solo_arm_pads(mixer_rig):
    rig = mixer_rig
    rig.tap(2, 5)
    assert track(rig, 2).mute
    rig.tap(3, 6)
    assert track(rig, 3).solo
    rig.tap(1, 7)
    assert track(rig, 1).arm


def test_volume_sliders_set_track_volume(mixer_rig):
    rig = mixer_rig
    rig.tap_side(VOLUME)
    rig.tick()
    volume = track(rig, 0).mixer_device.volume
    rig.tap(0, 0)  # top pad: loudest level (+6 dB)
    assert volume.value == pytest.approx(1.0)
    rig.tap(0, 7)  # bottom pad: -inf
    assert volume.value == 0.0
    rig.tap(0, 1)  # 0 dB is the second pad from the top
    assert volume.value == pytest.approx(0.85)


def test_volume_slider_lights_follow_the_volume(mixer_rig):
    rig = mixer_rig
    rig.tap_side(VOLUME)
    rig.tick()
    off = rig.device.led(4, 0)
    track(rig, 4).mixer_device.volume.value = 1.0
    rig.tick()
    assert rig.device.led(4, 0) != off


def test_pan_slider(mixer_rig):
    rig = mixer_rig
    rig.tap_side(PAN)
    rig.tick()
    panning = track(rig, 1).mixer_device.panning
    rig.tap(1, 7)  # bottom: hard left
    assert panning.value == pytest.approx(-1.0)
    rig.tap(1, 0)  # top: hard right
    assert panning.value == pytest.approx(1.0)


def test_send_sliders(mixer_rig):
    rig = mixer_rig
    rig.tap_side(SEND_A)
    rig.tick()
    rig.tap(2, 0)
    assert track(rig, 2).mixer_device.sends[0].value == pytest.approx(1.0)
    rig.tap_side(SEND_B)
    rig.tick()
    rig.tap(2, 0)
    assert track(rig, 2).mixer_device.sends[1].value == pytest.approx(1.0)


def test_mixer_channels(mixer_rig):
    rig = mixer_rig
    assert rig.selector.channel_for_current_mode() == 6
    rig.tap_side(VOLUME)
    assert rig.selector.channel_for_current_mode() == 7


def test_mixer_overview_sets_up_each_side_button_once(mixer_rig, monkeypatch):
    rig = mixer_rig
    sub_modes = rig.selector._sub_modes
    calls = []
    for index, button in enumerate(sub_modes._side_buttons):
        monkeypatch.setattr(button, "set_on_off_values", lambda *a, index=index: calls.append(("values", index)))
        monkeypatch.setattr(button, "turn_off", lambda index=index: calls.append(("off", index)))
    sub_modes._setup_mixer_overview()
    assert [i for kind, i in calls if kind == "values"] == [0, 1, 2, 3]  # once each
    last = dict((i, kind) for kind, i in calls)
    assert last == dict((i, "off") for i in range(len(sub_modes._side_buttons)))  # each one sent with its new values
