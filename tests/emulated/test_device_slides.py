"""Device controller stepless slides, advanced by Live's ticks (rig.tick: 100 ms each).

With Settings.ENABLE_TDC (the default) the time a pad is held picks the speed: a short tap
lands at once, longer presses slide over Settings.TDC_MAP seconds for the full range. With
it off, the pad velocity picks the speed. Slides run only while device mode is on.
"""

import pytest
from harness.device_mode import (
    BANK_UP,
    MODE_TOGGLE,
    SLIDER,
    USER1,
    device_with_kinds,
    enter_device_mode,
    names,
    pad,
    param,
    song_with_devices,
    tap_pad,
)

SESSION = 4


def _device_mode_rig(make_rig, model):
    device = device_with_kinds(second_bank=True)
    rig = make_rig(model, song=song_with_devices([device]))
    enter_device_mode(rig)
    rig.device_under_test = device
    return rig


@pytest.fixture
def slide_rig(make_rig, model):
    return _device_mode_rig(make_rig, model)


def slides(rig):
    return rig.selector._device_controller._slides


def hold_pad(rig, column, index, seconds):
    rig.press(*pad(column, index))
    rig.wait(seconds)
    rig.release(*pad(column, index))


def test_short_tap_lands_at_once(slide_rig):
    rig = slide_rig
    tap_pad(rig, SLIDER, 7)
    assert param(rig, SLIDER).value == 1.0
    assert not slides(rig).is_sliding()
    assert names(rig, SLIDER) == ["Device.DefaultSlider.On"] * 8


def test_held_pad_shows_the_press_time_colours(slide_rig):
    rig = slide_rig
    rig.press(*pad(SLIDER, 6))
    rig.tick()
    assert names(rig, SLIDER)[6] == "Device.ColorSteps.Step0"
    rig.wait(0.5)  # 0.6 s held: step 3 of 0.2 s
    assert names(rig, SLIDER)[6] == "Device.ColorSteps.Step3"
    rig.wait(3.0)
    assert names(rig, SLIDER)[6] == "Device.ColorSteps.Step9"
    assert param(rig, SLIDER).value == 0.0  # nothing moves before the release
    rig.release(*pad(SLIDER, 6))
    assert names(rig, SLIDER)[6] == "Device.DefaultSlider.Off"


def test_half_second_press_slides_the_full_range_in_one_and_a_half_seconds(slide_rig):
    rig = slide_rig
    parameter = param(rig, SLIDER)
    hold_pad(rig, SLIDER, 7, 0.5)  # TDC_MAP[2]: 1.5 s for the full range
    assert parameter.value == pytest.approx(0.05 / 1.5)  # the first step is taken at once
    rig.tick()
    assert parameter.value == pytest.approx(0.15 / 1.5)
    rig.wait(0.7)
    assert parameter.value == pytest.approx(0.85 / 1.5)
    assert names(rig, SLIDER) == ["Device.DefaultSlider.On"] * 4 + ["Device.DefaultSlider.Off"] * 4
    rig.wait(0.7)
    assert parameter.value == 1.0
    assert not slides(rig).is_sliding()
    assert names(rig, SLIDER) == ["Device.DefaultSlider.On"] * 8
    assert rig.selector._device_controller._osd.attributes[SLIDER] == "1.0"


def test_slide_to_a_target_float32_cannot_hold_ends(slide_rig):
    """Live keeps parameter values as 32-bit floats, so 6/7 reads back as 0.857142865...
    The slide must end there instead of rewriting the parameter on every tick."""
    rig = slide_rig
    parameter = param(rig, SLIDER)
    hold_pad(rig, SLIDER, 6, 0.5)
    rig.wait(2.0)
    assert parameter.value == pytest.approx(6 / 7)
    assert not slides(rig).is_sliding()
    writes = []
    parameter.add_value_listener(lambda: writes.append(parameter.value))
    rig.wait(1.0)
    assert writes == []


def test_slide_goes_down_too(slide_rig):
    rig = slide_rig
    parameter = param(rig, SLIDER)
    parameter.value = 1.0
    hold_pad(rig, SLIDER, 0, 0.5)
    rig.wait(1.5)
    assert parameter.value == 0.0


def test_a_new_press_retargets_the_running_slide(slide_rig):
    rig = slide_rig
    parameter = param(rig, SLIDER)
    hold_pad(rig, SLIDER, 7, 0.5)
    rig.tick(3)
    tap_pad(rig, SLIDER, 0)  # fast: straight back down
    assert parameter.value == 0.0
    rig.tick(3)
    assert parameter.value == 0.0


def test_moving_the_parameter_elsewhere_stops_the_slide(slide_rig):
    rig = slide_rig
    parameter = param(rig, SLIDER)
    hold_pad(rig, SLIDER, 7, 0.5)
    rig.tick()
    parameter.value = 0.5  # the mouse in Live
    rig.tick(5)
    assert parameter.value == 0.5
    assert not slides(rig).is_sliding()


def test_leaving_device_mode_stops_the_slide(slide_rig):
    rig = slide_rig
    parameter = param(rig, SLIDER)
    hold_pad(rig, SLIDER, 7, 0.5)
    rig.tick()
    rig.tap_top(SESSION)
    rig.tick()
    stopped_at = parameter.value
    rig.wait(2.0)
    assert parameter.value == stopped_at < 1.0
    rig.tap_top(USER1)  # back to device mode (user 1 remembers its sub mode)
    rig.tick()
    assert rig.selector._mode_index == 5
    rig.wait(2.0)
    assert parameter.value == stopped_at


def test_slide_keeps_going_after_a_bank_change(slide_rig):
    rig = slide_rig
    parameter = param(rig, SLIDER)
    hold_pad(rig, SLIDER, 7, 0.5)
    rig.tap_side(BANK_UP)
    controller = rig.selector._device_controller
    assert controller._sliders[SLIDER]._parameter_to_map_to is rig.device_under_test.parameters[9 + SLIDER]
    rig.wait(1.5)
    assert parameter.value == 1.0


def test_stepless_off_moves_at_once(slide_rig):
    rig = slide_rig
    rig.press_side(MODE_TOGGLE)
    rig.wait(0.6)
    rig.release_side(MODE_TOGGLE)
    hold_pad(rig, SLIDER, 7, 0.5)
    assert param(rig, SLIDER).value == 1.0


def test_disconnect_during_a_slide(slide_rig):
    rig = slide_rig
    hold_pad(rig, SLIDER, 7, 0.5)
    controller = rig.selector._device_controller
    rig.disconnect()
    assert not controller._slides.is_sliding()


@pytest.fixture
def velocity_rig(make_rig, model, monkeypatch):
    from Launchpad95.Settings import Settings

    monkeypatch.setattr(Settings, "ENABLE_TDC", False)
    return _device_mode_rig(make_rig, model)


def test_without_tdc_a_hard_press_jumps(velocity_rig):
    rig = velocity_rig
    rig.press(*pad(SLIDER, 7), velocity=127)
    assert param(rig, SLIDER).value == 1.0
    rig.release(*pad(SLIDER, 7))


def test_without_tdc_a_soft_press_slides_at_its_velocity_speed(velocity_rig):
    from Launchpad95.Settings import Settings

    rig = velocity_rig
    rate = 64**3 / (Settings.VELOCITY_FACTOR * 127.0) / 0.05  # units per second
    rig.press(*pad(SLIDER, 7), velocity=64)
    rig.release(*pad(SLIDER, 7))
    assert param(rig, SLIDER).value == pytest.approx(rate * 0.05)
    rig.wait(1.0)
    assert param(rig, SLIDER).value == pytest.approx(rate * 1.05)
