"""Switching between the main modes with the four mode buttons (top buttons 4..7)."""

import pytest

SESSION, USER1, USER2, MIXER = 4, 5, 6, 7

# (taps of a mode button from session mode, expected main mode index, sub mode, script message)
MODES = [
    ((USER1,), 1, 0, "INSTRUMENT MODE"),
    ((USER1, USER1), 1, 1, "DEVICE CONTROLLER MODE"),
    ((USER2,), 2, 0, "DRUM STEP SEQUENCER MODE"),
    ((USER2, USER2), 2, 1, "MELODIC SEQUENCER MODE"),
    ((MIXER,), 3, None, "MIXER MODE"),
    ((USER1, SESSION), 0, None, "SESSION MODE"),
]


@pytest.mark.parametrize("taps,main_mode,sub_mode,message", MODES, ids=[m[3] for m in MODES])
def test_mode_buttons_switch_modes(rig, taps, main_mode, sub_mode, message):
    for button in taps:
        rig.tap_top(button)
        rig.tick()
    selector = rig.selector
    assert selector._main_mode_index == main_mode
    if sub_mode is not None:
        assert selector._sub_mode_list[main_mode] == sub_mode
    assert rig.messages[-1] == message


def test_sub_modes_cycle_back(rig):
    for _ in range(3):
        rig.tap_top(USER1)
    assert rig.selector._sub_mode_list[1] == 0  # instrument, device, instrument
    for _ in range(3):
        rig.tap_top(USER2)
    assert rig.selector._sub_mode_list[2] == 0


def test_mode_button_leds_follow_the_mode(rig):
    skin = rig.surface._skin
    expected = {
        SESSION: ("Mode.Session.On", "Mode.Session.Off"),
        USER1: ("Mode.Note.On", "Mode.Note.Off"),
        USER2: ("Mode.StepSequencer.On", "Mode.StepSequencer.Off"),
        MIXER: ("Mode.Mixer.On", "Mode.Mixer.Off"),
    }
    for active in (USER1, USER2, MIXER, SESSION):
        rig.tap_top(active)
        rig.tick()
        for button, (on, off) in expected.items():
            wanted = skin[on if button == active else off].midi_value
            assert rig.device.top_led(button).value == wanted, (active, button)


def test_every_mode_reachable_without_errors(rig):
    for button in (USER1, USER1, USER2, USER2, MIXER, SESSION, USER1, USER2, MIXER, SESSION):
        rig.tap_top(button)
        rig.tick(3)
    assert [line for line in rig.log if "rror" in line or "xception" in line] == []


def test_midi_channel_per_mode(rig):
    """User modes move the grid to their own MIDI channel (instrument 11, device 3, ...)."""
    expected = [((), 0), ((USER1,), 11), ((USER1,), 3), ((USER2,), 1), ((USER2,), 2), ((MIXER,), 6)]
    for taps, channel in expected:
        for button in taps:
            rig.tap_top(button)
        assert rig.selector.channel_for_current_mode() == channel


def test_short_session_press_toggles_pro_session_and_long_press_does_not(rig):
    assert not rig.selector._pro_session_on
    rig.tap_top(SESSION)  # short press while in session mode
    assert rig.selector._pro_session_on
    assert rig.messages[-1] == "PRO SESSION MODE"
    rig.tap_top(SESSION)
    assert not rig.selector._pro_session_on
    rig.press_top(SESSION)
    rig.wait(1.0)  # held: session overview (zoom), no toggle
    rig.release_top(SESSION)
    assert not rig.selector._pro_session_on


def test_returning_to_session_quickly_keeps_pro_session_state(rig):
    rig.tap_top(SESSION)  # short tap in session mode: pro session on
    assert rig.selector._pro_session_on
    rig.tap_top(USER1)
    rig.tap_top(SESSION)  # back to session within 0.5 s of the first tap
    assert rig.selector._main_mode_index == 0
    assert rig.selector._pro_session_on


@pytest.mark.parametrize(
    "taps,channel", [((USER1,), 11), ((USER1, USER1), 3), ((USER2,), 1), ((USER2, USER2), 2), ((), 0)]
)
def test_default_mode_channels(rig, taps, channel):
    for button in taps:
        rig.tap_top(button)
        rig.tick()
    assert rig.selector.channel_for_current_mode() == channel


def test_mode_channels_follow_the_mode_not_its_position(make_rig, monkeypatch):
    from harness.devices import LaunchpadX
    from Launchpad95.Settings import Settings

    monkeypatch.setattr(Settings, "USER_MODES_1", ["device", "instrument"])
    monkeypatch.setattr(Settings, "USER_MODES_2", ["melodic stepseq", "drum stepseq"])
    rig = make_rig(LaunchpadX)
    rig.tap_top(USER1)
    rig.tick()
    assert rig.messages[-1] == "DEVICE CONTROLLER MODE"
    assert rig.selector.channel_for_current_mode() == 3
    rig.tap_top(USER2)
    rig.tick()
    assert rig.messages[-1] == "MELODIC SEQUENCER MODE"
    assert rig.selector.channel_for_current_mode() == 2
