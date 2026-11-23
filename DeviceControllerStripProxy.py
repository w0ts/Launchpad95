import queue
import traceback
from functools import partial
from threading import Thread

from .DeviceControllerStripServer import DeviceControllerStripServer
from .Log import log

non_returns = ["set_precision_mode", "set_stepless_mode", "shutdown",
               "update", "reset_if_no_parameter", "_button_value", "connect_to",
               "release_parameter", "set_parent", ]

returning = ["set_enabled", "param_name", "param_value","__ne__"]


class DeviceControllerStripProxy:
    def __init__(self, buttons, control_surface, column, parent=None):
        self._request_queue = queue.Queue()
        self._response_queue = queue.Queue()
        self.failed = False
        self.column = column
        self.request_id = 0
        self.server = DeviceControllerStripServer(buttons, control_surface,
                                                  column,
                                                  request_queue=self._request_queue,
                                                  response_queue=self._response_queue,
                                                  parent=parent)
        self._server_process = Thread(target=self.server.run)
        self._server_process.start()

    def __getattr__(self, item):
        #log(f'Proxy{self.column}: __getattr__ {item}')
        if self.failed:
            raise AttributeError("device strip %s failed: no %s" % (self.column, item))
        if item in non_returns:
            return partial(self._call_non_return_handler, item)
        elif item in returning:
            return partial(self._call_return_handler, item)
        else:
            #log(f'Proxy{self.column}: __getattr__ {item} not found !!!!!!!!!')
            return partial(self._call_non_return_handler, item)

    def shutdown(self):
        # also for a failed strip: its thread may still be running
        self._call_non_return_handler("shutdown")

    def _call_non_return_handler(self, name, *args, **kwargs):
        self.request_id += 1
        self._request_queue.put((name, self.request_id, args, kwargs))

    def _call_return_handler(self, name, *args, **kwargs):
        self.request_id += 1
        current_id = self.request_id
        self._request_queue.put((name, current_id, args, kwargs))
        try:
            while True:
                token, response = self._response_queue.get(timeout=10)
                if response == "ERROR":
                    # the strip's run loop died: it will never answer
                    self.failed = True
                    return None
                if token == current_id:
                    break
                # else: an old response, keep waiting for ours
            if response == 'None' and False:
                return None
            return response
        except queue.Empty:
            self.failed = True
            #log(f'Proxy{self.column}: _call_return_handler {name} {args} {kwargs} failed')
            log(traceback.format_stack())
            return
