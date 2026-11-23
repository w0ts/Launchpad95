"""Boot, handshake and disconnect of each Launchpad model."""

from harness.devices import LaunchpadMiniMK3, LaunchpadX


def _logged(rig, text):
    # The framework prefixes log lines with the script name, e.g. "(Launchpad) ...".
    return any(line.endswith(text) for line in rig.log)


def test_handshake_loads_the_right_model(rig):
    assert rig.device.answered_handshake
    assert _logged(rig, rig.device.loaded_log), rig.log
    for flag, value in rig.device.flags.items():
        assert getattr(rig.surface, flag) == value, flag


def test_boot_logs_no_errors(rig):
    problems = [line for line in rig.log if "Traceback" in line or "rror" in line or "xception" in line]
    assert problems == []


def test_boot_builds_the_main_selector_in_session_mode(rig):
    assert rig.selector is not None
    assert rig.selector._main_mode_index == 0
    assert rig.surface._init_done


def test_boot_lights_the_session_mode_button(rig):
    session_button = rig.selector._modes_buttons[0]
    assert rig.device.top_led(4).value == session_button._skin["Mode.Session.On"].midi_value


def test_programmer_mode_models_enter_programmer_mode(make_rig):
    for model in (LaunchpadX, LaunchpadMiniMK3):
        rig = make_rig(model)
        assert rig.device.in_programmer_mode
        assert (9, 1) in rig.device.sysex_commands  # sleep mode off


def test_disconnect_returns_programmer_mode_models_to_standalone(make_rig):
    for model in (LaunchpadX, LaunchpadMiniMK3):
        rig = make_rig(model)
        rig.disconnect()
        assert not rig.device.in_programmer_mode
        assert rig.device.sysex_commands[-1] == (16, 0)  # firmware standalone mode


def test_no_answer_means_no_components(make_rig, model):
    rig = make_rig(model, boot=False)
    rig.create()
    rig.device.answer = lambda midi: None  # an unplugged / silent device
    rig.tick(20)
    assert rig.selector is None
    assert not rig.surface._init_done


def test_second_identity_reply_does_not_reinit(rig):
    selector = rig.selector
    rig.surface._update_hardware()  # Live re-sends the challenge, e.g. after a port change
    rig.tick(5)
    assert rig.selector is selector
