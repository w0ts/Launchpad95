"""DeviceControllerStripServer and its proxy, driven directly (no strip thread unless a test
starts one)."""

import queue
import threading
import time

import Live
import pytest
from harness.devices import LaunchpadX


@pytest.fixture
def server(make_rig):
    from Launchpad95.DeviceControllerStripServer import DeviceControllerStripServer

    rig = make_rig(LaunchpadX)
    buttons = [rig.selector._matrix.get_button(0, y) for y in range(8)]
    with rig.surface.component_guard():  # controls are made inside the surface's context
        return DeviceControllerStripServer(
            buttons, rig.surface, 0, request_queue=queue.Queue(), response_queue=queue.Queue()
        )


def test_nine_value_enum_is_a_big_enum(server):
    from Launchpad95.DeviceControllerStripServer import SLIDER_MODE_BIG_ENUM, SLIDER_MODE_SMALL_ENUM

    server._parameter_to_map_to = Live.DeviceParameter.DeviceParameter(min=0, max=7, is_quantized=True)
    assert server._mode == SLIDER_MODE_SMALL_ENUM  # 8 values, 8 buttons
    server._parameter_to_map_to = Live.DeviceParameter.DeviceParameter(min=0, max=8, is_quantized=True)
    assert server._mode == SLIDER_MODE_BIG_ENUM  # 9 values do not fit on 8 buttons


def test_slider_update_is_needed_only_when_the_lit_button_changes(server):
    parameter = Live.DeviceParameter.DeviceParameter(min=0.0, max=100.0, value=50.0)
    server._parameter_to_map_to = parameter
    server._update_slider()
    assert not server._is_update_needed()
    parameter.value = 100.0
    assert server._is_update_needed()


def test_run_loop_error_is_reported_to_the_proxy(server, monkeypatch):
    monkeypatch.setattr(threading, "excepthook", lambda args: None)  # the loop re-raises
    server._request_queue.put(("set_precision_mode", 1, ("one", "too many"), {}))
    thread = threading.Thread(target=server.run)
    thread.start()
    thread.join(timeout=5)
    assert server._response_queue.get(timeout=1) == (0, "ERROR")


class _Proxy:
    """A DeviceControllerStripProxy without its server thread."""

    @staticmethod
    def make():
        from Launchpad95.DeviceControllerStripProxy import DeviceControllerStripProxy

        proxy = object.__new__(DeviceControllerStripProxy)
        proxy._request_queue = queue.Queue()
        proxy._response_queue = queue.Queue()
        proxy.failed = False
        proxy.column = 0
        proxy.request_id = 0
        return proxy


def test_proxy_stops_waiting_when_the_server_reports_an_error(framework):
    proxy = _Proxy.make()
    proxy._response_queue.put((0, "ERROR"))
    start = time.time()
    assert proxy.param_name() is None
    assert time.time() - start < 1.0
    assert proxy.failed


def test_failed_proxy_raises_instead_of_returning_none(framework):
    proxy = _Proxy.make()
    proxy.failed = True
    with pytest.raises(AttributeError):
        proxy.update()


def test_failed_proxy_can_still_be_shut_down(framework):
    proxy = _Proxy.make()
    proxy.failed = True
    proxy.shutdown()
    assert proxy._request_queue.get_nowait()[0] == "shutdown"
