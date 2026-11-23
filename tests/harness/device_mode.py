"""Device controller mode helpers: a device with one parameter kind per column, and the
pads of a column (index 0 at the bottom, 7 at the top)."""

import Live

from .rig import make_song

USER1 = 5
MODE_TOGGLE = 3
LOCK1 = 4
DISABLED = "DefaultButton.Disabled"

TOGGLE, ENUM4, ENUM8, ENUM9, ENUM128, SLIDER, WIDE, SPARE = range(8)
BANK_UP = 2


def device_with_kinds(name="Kinds", second_bank=False):
    """One parameter kind per column (bank 0 maps parameters 1-8); ``second_bank`` adds
    eight more sliders (bank 1)."""
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
    if second_bank:
        parameters += [param(f"Bank2 P{i + 1}", 0.0, 0.0, 1.0) for i in range(8)]
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
