"""Device controller mode (user 1 button, second sub mode): device selection and
navigation. The columns themselves are in test_device_sliders.py and test_device_slides.py."""

import Live
import pytest
from harness.rig import make_song

USER1 = 5


def song_with_device():
    song = make_song()
    device = Live.Device.Device(name="Fake Synth", class_name="FakeSynth", num_parameters=16)
    device.canonical_parent = song.tracks[0]
    song.tracks[0].devices = (device,)
    return song, device


@pytest.fixture
def device_rig(make_rig, model):
    song, device = song_with_device()
    rig = make_rig(model, song=song)
    rig.tap_top(USER1)
    rig.tap_top(USER1)
    rig.tick(2)
    assert rig.selector._mode_index == 5
    rig.device_under_test = device
    return rig


def test_device_mode_picks_the_first_device_of_the_selected_track(device_rig):
    rig = device_rig
    controller = rig.selector._device_controller
    assert controller._device is rig.device_under_test
    assert rig.song.appointed_device is rig.device_under_test
    assert "DEVICE CONTROLLER MODE" in rig.messages


def test_top_pad_of_a_column_raises_its_parameter(device_rig):
    rig = device_rig
    parameter = rig.device_under_test.parameters[1]
    assert parameter.value == 0.0
    # A short tap (Settings.ENABLE_TDC): the target is set on release and reached at the
    # fastest speed, at once.
    rig.press(0, 0)
    rig.release(0, 0)
    assert parameter.value == parameter.max
    rig.tap(0, 7)
    assert parameter.value == parameter.min


def test_device_mode_without_device_boots_and_leaves(make_rig, model):
    rig = make_rig(model)
    rig.tap_top(USER1)
    rig.tap_top(USER1)
    rig.tick(3)
    assert rig.selector._device_controller._device is None
    rig.tap_top(4)
    rig.tick(2)
    assert rig.selector._main_mode_index == 0


def rack_song(first_chain_devices=(), last_chain_devices=()):
    song = make_song()
    track = song.tracks[0]
    rack = Live.RackDevice.RackDevice(
        name="Rack",
        chains=(
            Live.Chain.Chain(name="A", devices=first_chain_devices),
            Live.Chain.Chain(name="B", devices=last_chain_devices),
        ),
    )
    after = Live.Device.Device(name="After")
    for device in (rack, after):
        device.canonical_parent = track
    track.devices = (rack, after)
    return song, rack, after


def test_rack_navigation_with_empty_chains(make_rig):
    from harness.devices import LaunchpadX

    song, rack, after = rack_song()
    rig = make_rig(LaunchpadX, song=song)
    controller = rig.selector._device_controller
    assert controller._get_next_device(rack) is after
    assert controller._get_previous_device(after) is rack


def test_device_track_name_walks_up_from_a_rack_chain(make_rig):
    from harness.devices import LaunchpadX

    inner = Live.Device.Device(name="Inner")
    song, rack, after = rack_song(first_chain_devices=(inner,))
    song.tracks[0].name = "Bass"
    rig = make_rig(LaunchpadX, song=song)
    assert rig.selector._device_controller.get_device_track_name(inner) == "Bass"


def test_device_change_outside_device_mode_leaves_the_detail_view(make_rig):
    from harness.devices import LaunchpadX

    song, device = song_with_device()
    rig = make_rig(LaunchpadX, song=song)
    view = Live.Application.get_application().view
    view.show_view("Detail/Clip")
    song.appointed_device = device
    rig.tick()
    assert view.is_view_visible("Detail/Clip")


def test_entering_device_mode_shows_the_device_chain(make_rig):
    from harness.devices import LaunchpadX

    song, device = song_with_device()
    rig = make_rig(LaunchpadX, song=song)
    song.appointed_device = device
    view = Live.Application.get_application().view
    view.show_view("Detail/Clip")
    rig.tap_top(USER1)
    rig.tap_top(USER1)
    rig.tick(2)
    assert view.is_view_visible("Detail/DeviceChain")
