"""DeviceControllerStrip and ParameterSlides, driven directly."""

import Live
import pytest
from harness.devices import LaunchpadX


class _Parent:
    _osd = None


@pytest.fixture
def strip(make_rig):
    from Launchpad95.DeviceControllerStrip import DeviceControllerStrip
    from Launchpad95.ParameterSlides import ParameterSlides

    rig = make_rig(LaunchpadX)
    buttons = [rig.selector._matrix.get_button(0, y) for y in range(8)]
    with rig.surface.component_guard():  # controls are made inside the surface's context
        return DeviceControllerStrip(buttons, 0, _Parent(), ParameterSlides())


def test_nine_value_enum_is_a_big_enum(strip):
    from Launchpad95.DeviceControllerStrip import SLIDER_MODE_BIG_ENUM, SLIDER_MODE_SMALL_ENUM

    strip._parameter_to_map_to = Live.DeviceParameter.DeviceParameter(min=0, max=7, is_quantized=True)
    assert strip._mode == SLIDER_MODE_SMALL_ENUM  # 8 values, 8 buttons
    strip._parameter_to_map_to = Live.DeviceParameter.DeviceParameter(min=0, max=8, is_quantized=True)
    assert strip._mode == SLIDER_MODE_BIG_ENUM  # 9 values do not fit on 8 buttons


def test_slider_update_is_needed_only_when_the_lit_button_changes(strip):
    parameter = Live.DeviceParameter.DeviceParameter(min=0.0, max=100.0, value=50.0)
    strip._parameter_to_map_to = parameter
    strip.update()
    assert not strip._is_update_needed()
    parameter.value = 100.0
    assert strip._is_update_needed()


def test_strip_without_parameter_paints_its_pads_disabled(strip):
    strip.reset_if_no_parameter()
    assert all(button.states[True] == "DefaultButton.Disabled" for button in strip._buttons)
    assert strip.param_name() == "None"
    assert strip.param_value() == 0


def test_disabled_strip_ignores_pads_and_updates(strip):
    parameter = Live.DeviceParameter.DeviceParameter(min=0, max=3, is_quantized=True)
    strip._parameter_to_map_to = parameter
    strip.set_enabled(False)
    strip._button_value(127, strip._buttons[2])
    strip._button_value(0, strip._buttons[2])
    assert parameter.value == 0


def test_slide_is_dropped_when_something_else_moves_the_parameter(framework):
    from Launchpad95.ParameterSlides import ParameterSlides

    parameter = Live.DeviceParameter.DeviceParameter(min=0.0, max=1.0, value=0.0)
    slides = ParameterSlides()
    slides.start(parameter, 1.0, 1.0)  # 1 unit per second: first step is 50 ms
    assert parameter.value == pytest.approx(0.05)
    parameter.value = 0.5  # the mouse in Live
    slides.advance(0.1)
    assert parameter.value == 0.5
    assert not slides.is_sliding()


class _DeletableParameter(Live.DeviceParameter.DeviceParameter):
    """Once deleted, compares equal to None like a Live object whose C++ object is gone."""

    deleted = False

    def __eq__(self, other):
        return (other is None and self.deleted) or other is self

    __hash__ = object.__hash__


def test_slide_ends_when_its_parameter_is_deleted(framework):
    from Launchpad95.ParameterSlides import ParameterSlides

    parameter = _DeletableParameter(min=0.0, max=1.0, value=0.0)
    slides = ParameterSlides()
    slides.start(parameter, 1.0, 1.0)
    assert slides.is_sliding()
    parameter.deleted = True
    slides.advance(0.1)
    assert not slides.is_sliding()
    assert parameter.value == pytest.approx(0.05)


def test_slide_without_rate_jumps(framework):
    from Launchpad95.ParameterSlides import ParameterSlides

    parameter = Live.DeviceParameter.DeviceParameter(min=0.0, max=1.0, value=0.0)
    slides = ParameterSlides()
    slides.start(parameter, 0.75, None)
    assert parameter.value == 0.75
    assert not slides.is_sliding()
    assert slides.target(parameter) is None
