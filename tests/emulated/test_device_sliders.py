"""Device controller mode: what each column does for each kind of parameter, the mode toggle
(side button 3) and the four lock buttons (side buttons 4-7).

A column's bottom pad is its index 0, the top pad index 7. Every column paints its pads with
one skin name per pad (set as both the on and the off value), read back from the button.
These are main-thread paths (button presses, parameter listeners): no slide is involved,
except where a test says so.
"""

import time

import Live
import pytest
from harness.rig import make_song

USER1 = 5
MODE_TOGGLE = 3
LOCK1 = 4
DISABLED = "DefaultButton.Disabled"

TOGGLE, ENUM4, ENUM8, ENUM9, ENUM128, SLIDER, WIDE, SPARE = range(8)


def device_with_kinds(name="Kinds"):
    """One parameter kind per column (bank 0 maps parameters 1-8)."""
    param = Live.DeviceParameter.DeviceParameter
    parameters = [
        param("Device On", 1.0, 0.0, 1.0, is_quantized=True),
        param("Toggle", 0, 0, 1, is_quantized=True),
        param("Enum4", 0, 0, 3, is_quantized=True),
        param("Enum8", 0, 0, 7, is_quantized=True),
        param("Enum9", 0, 0, 8, is_quantized=True),
        param("Enum128", 64, 0, 127, is_quantized=True),
        param("Slider", 0.0, 0.0, 1.0),
        param("Wide", 0.0, 0.0, 100.0),
        param("Spare", 0.0, 0.0, 1.0),
    ]
    return Live.Device.Device(name=name, class_name="FakeKinds", parameters=parameters)


def song_with_devices(*devices_per_track):
    song = make_song()
    for track, devices in zip(song.tracks[: len(devices_per_track)], devices_per_track, strict=True):
        for device in devices:
            device.canonical_parent = track
        track.devices = tuple(devices)
    return song


def enter_device_mode(rig):
    rig.tap_top(USER1)
    rig.tap_top(USER1)
    rig.tick(2)
    assert rig.selector._mode_index == 5


@pytest.fixture
def kinds_rig(make_rig, model):
    device = device_with_kinds()
    rig = make_rig(model, song=song_with_devices([device]))
    enter_device_mode(rig)
    rig.device_under_test = device
    return rig


def param(rig, column):
    return rig.device_under_test.parameters[column + 1]


def pad(column, index):
    """(x, y) of a column's pad, index 0 at the bottom."""
    return column, 7 - index


def tap_pad(rig, column, index):
    rig.tap(*pad(column, index))


def names(rig, column):
    matrix = rig.selector._matrix
    return [matrix.get_button(*pad(column, index)).states[True] for index in range(8)]


def wait_for(condition, timeout=5.0):
    """The mode toggle reaches the strips asynchronously (strip threads): poll."""
    deadline = time.time() + timeout
    while not condition() and time.time() < deadline:
        time.sleep(0.01)
    return condition()


def strips(rig):
    return [proxy.server for proxy in rig.selector._device_controller._sliders]


def osd(rig):
    return rig.selector._device_controller._osd


def test_toggle_uses_the_bottom_pad(kinds_rig):
    rig = kinds_rig
    assert names(rig, TOGGLE) == ["Device.Toggle.Off"] + [DISABLED] * 7
    tap_pad(rig, TOGGLE, 0)
    assert param(rig, TOGGLE).value == 1
    assert names(rig, TOGGLE)[0] == "Device.Toggle.On"
    tap_pad(rig, TOGGLE, 5)  # the other pads do nothing
    assert param(rig, TOGGLE).value == 1
    tap_pad(rig, TOGGLE, 0)
    assert param(rig, TOGGLE).value == 0
    assert names(rig, TOGGLE)[0] == "Device.Toggle.Off"


def test_four_value_enum_has_one_pad_per_value(kinds_rig):
    rig = kinds_rig
    assert names(rig, ENUM4) == ["Device.Enum.On"] + ["Device.Enum.Off"] * 3 + [DISABLED] * 4
    tap_pad(rig, ENUM4, 2)
    assert param(rig, ENUM4).value == 2
    assert names(rig, ENUM4)[:4] == ["Device.Enum.Off", "Device.Enum.Off", "Device.Enum.On", "Device.Enum.Off"]


def test_eight_value_enum_fills_the_column(kinds_rig):
    rig = kinds_rig
    tap_pad(rig, ENUM8, 7)
    assert param(rig, ENUM8).value == 7
    assert names(rig, ENUM8) == ["Device.Enum.Off"] * 7 + ["Device.Enum.On"]


def test_nine_value_enum_steps_with_the_middle_pads(kinds_rig):
    rig = kinds_rig
    parameter = param(rig, ENUM9)
    assert names(rig, ENUM9) == [DISABLED] * 3 + ["Device.BigEnum.Off", "Device.BigEnum.On"] + [DISABLED] * 3
    tap_pad(rig, ENUM9, 4)  # +1
    assert parameter.value == 1
    tap_pad(rig, ENUM9, 6)  # +4
    assert parameter.value == 5
    tap_pad(rig, ENUM9, 7)  # +8, clamped
    assert parameter.value == 8
    assert names(rig, ENUM9)[3:5] == ["Device.BigEnum.On", "Device.BigEnum.Off"]
    tap_pad(rig, ENUM9, 3)  # -1
    assert parameter.value == 7
    tap_pad(rig, ENUM9, 1)  # -4
    assert parameter.value == 3
    tap_pad(rig, ENUM9, 0)  # -8, clamped
    assert parameter.value == 0


def test_big_enum_steps_by_powers_of_two(kinds_rig):
    rig = kinds_rig
    tap_pad(rig, ENUM128, 5)
    assert param(rig, ENUM128).value == 66
    tap_pad(rig, ENUM128, 2)
    assert param(rig, ENUM128).value == 64


def test_slider_pads_follow_the_parameter(kinds_rig):
    rig = kinds_rig
    assert names(rig, SLIDER) == ["Device.DefaultSlider.On"] + ["Device.DefaultSlider.Off"] * 7
    param(rig, SLIDER).value = 0.5  # moved in Live: 0.5 >= 3/7, < 4/7
    assert names(rig, SLIDER) == ["Device.DefaultSlider.On"] * 4 + ["Device.DefaultSlider.Off"] * 4
    param(rig, SLIDER).value = 1.0
    assert names(rig, SLIDER) == ["Device.DefaultSlider.On"] * 8


def test_osd_shows_the_parameter_of_each_column(kinds_rig):
    rig = kinds_rig
    assert osd(rig).mode == "Device Controller"
    assert osd(rig).attribute_names[:3] == ["Toggle", "Enum4", "Enum8"]
    tap_pad(rig, ENUM4, 3)
    assert osd(rig).attributes[ENUM4] == "3"
    assert osd(rig).info[1] == "device : Kinds"


def test_short_tap_on_mode_toggle_switches_precision(kinds_rig):
    rig = kinds_rig
    controller = rig.selector._device_controller
    rig.tap_side(MODE_TOGGLE)
    assert controller._precision_mode
    precision = [DISABLED] * 3 + ["Device.PrecisionSlider.Off", "Device.PrecisionSlider.On"] + [DISABLED] * 3
    assert wait_for(lambda: names(rig, WIDE) == precision), names(rig, WIDE)
    tap_pad(rig, WIDE, 4)  # range 100: 100/128 rounds up to 1
    assert param(rig, WIDE).value == 1
    tap_pad(rig, WIDE, 7)  # 1 * 2**3
    assert param(rig, WIDE).value == 9
    tap_pad(rig, WIDE, 2)  # -2
    assert param(rig, WIDE).value == 7
    tap_pad(rig, SLIDER, 5)  # range 1: steps of 1/128
    assert param(rig, SLIDER).value == pytest.approx(2 / 128)
    rig.tap_side(MODE_TOGGLE)
    assert not controller._precision_mode


def test_long_press_on_mode_toggle_switches_stepless_off(kinds_rig):
    rig = kinds_rig
    controller = rig.selector._device_controller
    assert controller._stepless_mode
    rig.press_side(MODE_TOGGLE)
    rig.wait(0.6)
    rig.release_side(MODE_TOGGLE)
    assert not controller._stepless_mode
    assert "normal faders mode" in rig.messages
    assert wait_for(lambda: not any(s._stepless_mode for s in strips(rig)))
    tap_pad(rig, SLIDER, 7)  # not stepless: jumps at once
    assert param(rig, SLIDER).value == 1.0
    tap_pad(rig, SLIDER, 0)
    assert param(rig, SLIDER).value == 0.0


@pytest.fixture
def two_track_rig(make_rig, model):
    first, second = device_with_kinds("First"), device_with_kinds("Second")
    rig = make_rig(model, song=song_with_devices([first], [second]))
    enter_device_mode(rig)
    rig.devices = (first, second)
    return rig


def long_tap_side(rig, index):
    rig.press_side(index)
    rig.wait(0.5)
    rig.release_side(index)


def test_long_press_on_a_lock_button_stores_and_locks_the_device(two_track_rig):
    rig = two_track_rig
    controller = rig.selector._device_controller
    first = rig.devices[0]
    long_tap_side(rig, LOCK1)
    assert controller._locked_devices[0] is first
    assert controller._locked_device_index == 0
    assert any("STORED IN LOCK: 1" in m for m in rig.messages)
    assert controller._device is first
    assert osd(rig).info[1] == "device : First (locked)"


def test_short_press_unlocks_then_relocks(two_track_rig):
    rig = two_track_rig
    controller = rig.selector._device_controller
    first, second = rig.devices
    long_tap_side(rig, LOCK1)
    rig.tap_side(LOCK1)
    assert controller._locked_device_index is None
    assert any(m.startswith("UNLOCKED FROM") for m in rig.messages)
    rig.song.view.selected_track = rig.song.tracks[1]
    rig.song.appointed_device = second
    rig.tick()
    assert controller._device is second
    rig.tap_side(LOCK1)  # back to the stored device
    assert controller._locked_device_index == 0
    assert controller._device is first
    assert any(m.startswith("LOCKED TO") for m in rig.messages)


def test_same_device_cannot_be_stored_twice(two_track_rig):
    rig = two_track_rig
    controller = rig.selector._device_controller
    long_tap_side(rig, LOCK1)
    long_tap_side(rig, LOCK1 + 1)
    assert controller._locked_devices[1] is None
    assert any("IS ALREADY IN LOCK: 1" in m for m in rig.messages)


def test_long_press_on_a_used_lock_clears_it(two_track_rig):
    rig = two_track_rig
    controller = rig.selector._device_controller
    long_tap_side(rig, LOCK1)
    long_tap_side(rig, LOCK1)
    assert controller._locked_devices[0] is None
    assert controller._locked_device_index is None
    assert any(m.startswith("REMOVING") for m in rig.messages)
