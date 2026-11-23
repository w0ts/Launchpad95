import time

import Live
from _Framework import Task
from _Framework.ButtonElement import ButtonElement
from _Framework.DeviceComponent import DeviceComponent

from .DeviceControllerStrip import DeviceControllerStrip
from .DeviceNavigation import next_device, previous_device
from .ParameterSlides import ParameterSlides
from .Settings import Settings

# Longest time one tick may advance the slides by (Live can stall, e.g. while loading).
MAX_TICK_SECONDS = 0.5
# A lock button released this long after its press stores or clears its lock.
LOCK_LONG_PRESS = 0.4


class DeviceControllerComponent(DeviceComponent):
    __module__ = __name__
    __doc__ = ""

    def __init__(
        self,
        control_surface=None,
        name="device_component",
        is_enabled=False,
        matrix=None,
        side_buttons=None,
        top_buttons=None,
    ):
        self._control_surface = control_surface
        self.name = name
        self._slides = ParameterSlides()
        self._last_tick = None
        self._device = None
        self._matrix = matrix
        self._selected_track = None

        # Track navigation buttons
        self._prev_track_button = None
        self._next_track_button = None
        # Track Device navigation buttons
        self._prev_device_button = None
        self._next_device_button = None
        # Device Bank navigation buttons
        self._prev_bank_button = None
        self._next_bank_button = None

        # Precision/stepless logic
        self._mode_toggle_button = None
        self._last_mode_toggle_button_press = time.time()
        self._precision_mode = False
        self._stepless_mode = Settings.DEVICE_CONTROLLER__STEPLESS_MODE

        # Lock logic
        self._lock_button_slots = [None, None, None, None]
        self._lock_buttons = [None, None, None, None]
        self._locked_devices = [None, None, None, None]
        self._locked_device_index = None
        self._lock_buttons = [None, None, None, None]

        self._locked_device_bank = [0, 0, 0, 0]
        self._lock_button_press = [0, 0, 0, 0]
        self._locked_devices = [None, None, None, None]

        self._is_active = False
        self._force = True
        self._osd = None

        self._control_surface.application().view.add_is_view_visible_listener("Detail", self._on_detail_view_changed)
        self._control_surface.application().view.add_is_view_visible_listener("Detail/Clip", self._on_views_changed)

        # self._remaining_buttons = None UNUSED
        DeviceComponent.__init__(self)
        # Runs from Live's update_display while device mode is on: the component's task
        # group is paused while it is disabled and killed on disconnect.
        self._tasks.add(Task.FuncTask(self._on_tick))

        # Sliders
        self._sliders = []
        if matrix is not None:
            self.set_matrix(matrix)
        self.set_enabled(is_enabled)

        if top_buttons is not None:
            # device selection buttons
            self.set_prev_device_button(top_buttons[0])
            self.set_next_device_button(top_buttons[1])
            # track selection buttons
            self.set_prev_track_button(top_buttons[2])
            self.set_next_track_button(top_buttons[3])

        if side_buttons is not None:
            # on/off button
            self.set_on_off_button(side_buttons[0])

            # bank nav buttons
            self.set_bank_nav_buttons(side_buttons[1], side_buttons[2])
            self._prev_bank_button = side_buttons[1]
            self._next_bank_button = side_buttons[2]

            # precision
            self.set_mode_toggle_button(side_buttons[3])

            # lock buttons
            self.set_lock_button1(side_buttons[4])
            self.set_lock_button2(side_buttons[5])
            self.set_lock_button3(side_buttons[6])
            self.set_lock_button4(side_buttons[7])

        # selected device listener
        self.song().add_appointed_device_listener(self._on_device_changed)
        self._control_surface.set_device_component(self)

    def disconnect(self):
        self._control_surface.application().view.remove_is_view_visible_listener("Detail", self._on_detail_view_changed)
        self._control_surface.application().view.remove_is_view_visible_listener("Detail/Clip", self._on_views_changed)
        self._control_surface.set_device_component(None)
        self.song().remove_appointed_device_listener(self._on_device_changed)
        self._prev_track_button = None
        self._next_track_button = None
        self._prev_device_button = None
        self._next_device_button = None
        self._prev_bank_button = None
        self._next_bank_button = None
        self._mode_toggle_button = None
        self._precision_mode = None
        # self._remaining_buttons = None UNUSED
        self._device = None
        for slider in self._sliders:
            slider.release_parameter()
        self._slides.clear()
        # the strips are released: the framework must not call them again
        self._parameter_controls = None
        DeviceComponent.disconnect(self)

    def set_matrix(self, matrix):
        self._matrix = matrix
        if self._matrix:
            self._sliders = []
            for column in range(self._matrix.width()):
                buttons = tuple(
                    self._matrix.get_button(column, (self._matrix.height() - 1 - row))
                    for row in range(self._matrix.height())
                )
                self._sliders.append(DeviceControllerStrip(buttons, column, self, self._slides))
            self._sliders = tuple(self._sliders)
            self.set_parameter_controls(self._sliders)
        else:
            self._sliders = []

    @property
    def _is_locked_to_device(self):
        return self._locked_device_index is not None

    def set_enabled(self, active):
        if active:
            self._force = True
            self.on_selected_track_changed()
            if self._device is not None:
                self.set_device_view()
        else:
            # leaving device mode ends the running slides
            self._slides.clear()
            self._last_tick = None
        # disable matrix.
        for slider in self._sliders:
            slider.set_enabled(active)
            slider.set_stepless_mode(self._stepless_mode)
        # ping parent
        DeviceComponent.set_enabled(self, active)
        return True

    def _on_tick(self, delta):
        now = time.time()
        elapsed = delta if self._last_tick is None else min(max(now - self._last_tick, 0.0), MAX_TICK_SECONDS)
        self._last_tick = now
        self._slides.advance(elapsed)
        for slider in self._sliders:
            slider.tick(now)
        return Task.RUNNING

    def _on_detail_view_changed(self):
        self.update()

    def _on_views_changed(self):
        self.update()

    def set_osd(self, osd):
        self._osd = osd

    def _update_OSD(self):
        if self._osd is not None:
            self._osd.mode = "Device Controller"
            i = 0
            try:
                for slider in self._parameter_controls:
                    name = slider.param_name()
                    if name != "None":
                        self._osd.attribute_names[i] = str(name)
                        self._osd.attributes[i] = str(slider.param_value())
                    else:
                        self._osd.attribute_names[i] = " "
                        self._osd.attributes[i] = " "
                    i += 1
            except Exception:
                for i in range(8):
                    self._osd.attribute_names[i] = " "
                    self._osd.attributes[i] = " "

            if self._selected_track is not None:
                if self._is_locked_to_device:
                    if self._device is not None:
                        self._osd.info[0] = "track : " + self.get_device_track_name(self._device) + " (locked)"
                    else:
                        self._osd.info[0] = "track : " + self._selected_track.name
                else:
                    self._osd.info[0] = "track : " + self._selected_track.name
            else:
                self._osd.info[0] = " "
            try:
                name = self._device.name
                if name == "":
                    name = "(unamed device)"
                if self._is_locked_to_device:
                    self._osd.info[1] = "device : " + name + " (locked)"
                else:
                    self._osd.info[1] = "device : " + name
            except Exception:
                self._osd.info[1] = "no device selected"
            self._osd.update()

    # DEVICE SELECTION
    def _on_device_changed(self):
        if not self._is_locked_to_device:
            self._selected_track = self.song().view.selected_track
            self.set_device(self.song().appointed_device)
            # self.set_device(self._selected_track.view.selected_device)
            if self.is_enabled():
                self.update()

    def on_selected_track_changed(self):
        if not self._is_locked_to_device:
            self._selected_track = self.song().view.selected_track
            if self._selected_track.view.selected_device:
                self.set_device(self._selected_track.view.selected_device)
            else:
                self.select_first_device()
            if self.is_enabled():
                self.update()

    def select_first_device(self):
        track = self.song().view.selected_track
        if track.devices is not None and len(track.devices) > 0:
            device_to_select = track.devices[0]
            self.song().view.select_device(device_to_select)
            self.set_device(device_to_select)

    def set_device(self, device):
        if self._is_locked_to_device:
            locked = self._locked_devices[self._locked_device_index]
            if locked != None and device != locked:
                return  # the framework follows the appointed device: not while locked
        if device != self._device:
            if self._bank_index is None or self._number_of_parameter_banks() <= self._bank_index:
                self._bank_index = 0
            self._device = device
            if self.is_enabled():
                self.set_device_view()
            DeviceComponent.set_device(self, device)

    def set_device_view(self):
        view = self.application().view
        if not view.is_view_visible("Detail") or not view.is_view_visible("Detail/DeviceChain"):
            view.show_view("Detail")
            view.show_view("Detail/DeviceChain")

    # UPDATE
    def update(self):

        if self.is_enabled():
            if self._bank_index is None or self._number_of_parameter_banks() <= self._bank_index:
                self._bank_index = 0

            if not self._is_locked_to_device:
                if self._device is not None:
                    if (not self.application().view.is_view_visible("Detail")) or (
                        not self.application().view.is_view_visible("Detail/DeviceChain")
                    ):
                        self.application().view.show_view("Detail")
                        self.application().view.show_view("Detail/DeviceChain")
            # update bank buttons colors
            if self._device is not None:
                if self._prev_bank_button is not None:
                    self._prev_bank_button.set_on_off_values("Device.Bank.On", "Device.Bank.Off")
                if self._next_bank_button is not None:
                    self._next_bank_button.set_on_off_values("Device.Bank.On", "Device.Bank.Off")
            else:
                if self._prev_bank_button is not None:
                    self._prev_bank_button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
                if self._next_bank_button is not None:
                    self._next_bank_button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
            if self._matrix is not None:
                for x in range(self._matrix.width()):
                    for y in range(self._matrix.height()):
                        self._matrix.get_button(x, y).set_enabled(True)

            if self._device is None and self._matrix is not None:
                for x in range(self._matrix.width()):
                    for y in range(self._matrix.height()):
                        if self._force:
                            self._matrix.get_button(x, y).set_on_off_values(
                                "DefaultButton.Disabled", "DefaultButton.Disabled"
                            )
                            self._matrix.get_button(x, y).turn_off()

            # update parent
            DeviceComponent.update(self)
            if self._sliders is not None:
                for slider in self._sliders:
                    slider.reset_if_no_parameter()
            # additional updates :
            self.update_track_buttons()
            self.update_device_buttons()
            self.update_lock_buttons()
            self.update_on_off_button()
            self.update_mode_toggle_button()
            self._update_OSD()
            self._force = False

    # LOCK button
    def update_lock_buttons(self):
        # lock button
        if self.is_enabled():
            for index in range(len(self._locked_devices)):
                if self._lock_buttons[index] is not None:
                    if self._locked_devices[index] is not None:
                        self._lock_buttons[index].set_on_off_values("Device.Lock.Locked", "Device.Lock.Set")
                    else:
                        self._lock_buttons[index].set_on_off_values("Device.Lock.Empty", "Device.Lock.Empty")  # LED_OFF
                    if self._locked_device_index == index:
                        self._lock_buttons[index].turn_on()
                    else:
                        self._lock_buttons[index].turn_off()

    def set_lock_button1(self, button):
        self.set_lock_button(button, 1)

    def set_lock_button2(self, button):
        self.set_lock_button(button, 2)

    def set_lock_button3(self, button):
        self.set_lock_button(button, 3)

    def set_lock_button4(self, button):
        self.set_lock_button(button, 4)

    def set_lock_button(self, button, index):
        if len(self._lock_buttons) >= index:
            if self._lock_buttons[index - 1] is not None:
                self._lock_buttons[index - 1].remove_value_listener(self._lock_value)
            self._lock_buttons[index - 1] = button
            if self._lock_buttons[index - 1] is not None:
                assert isinstance(self._lock_buttons[index - 1], ButtonElement)
                self._lock_buttons[index - 1].add_value_listener(self._lock_value, identify_sender=True)

    # Lock buttons: a long press stores the device in (or clears) the lock, a tap locks to
    # (or unlocks from) the stored device.
    def _lock_value(self, value, sender):
        if not self.is_enabled():
            return
        index = self._lock_index(sender)
        if value != 0:
            self._lock_button_press[index] = time.time()
        elif time.time() - self._lock_button_press[index] > LOCK_LONG_PRESS:
            self._lock_long_press(index)
        else:
            self._lock_short_press(index)
        self.update_track_buttons()
        self.update_device_buttons()
        self._update_OSD()
        if self._is_locked_to_device:
            self.on_selected_track_changed()
        self.update_lock_buttons()

    def _lock_index(self, sender):
        index = 0
        for i, button in enumerate(self._lock_buttons):
            if button == sender:
                index = i
        return index

    def _lock_long_press(self, index):
        locked = self._locked_devices[index]
        if locked is not None:
            self._show_lock_message("REMOVING '", locked, "' FROM LOCK: " + str(index + 1))
            self._locked_devices[index] = None
            self._locked_device_index = None
        elif self._device is not None:
            self._store_lock(index)

    def _store_lock(self, index):
        stored_in = [i for i, device in enumerate(self._locked_devices) if device == self._device]
        if stored_in:
            self._show_lock_message(
                "*** WARNING *** '", self._device, "' IS ALREADY IN LOCK: " + str(stored_in[-1] + 1)
            )
            return
        self._locked_devices[index] = self._device
        self._show_lock_message(" '", self._device, "' STORED IN LOCK: " + str(index + 1))
        self._locked_device_index = index
        self.update()

    def _lock_short_press(self, index):
        locked = self._locked_devices[index]
        if self._locked_device_index == index:
            if locked is not None:
                self._show_lock_message("UNLOCKED FROM '", locked, "' (" + str(index + 1) + ")")
            self._locked_device_index = None
        elif locked is not None:
            self._locked_device_index = index
            self.set_device(locked)
            self._show_lock_message("LOCKED TO '", locked, " (" + str(index + 1) + ")")
            self.update()

    def _show_lock_message(self, prefix, device, suffix):
        name = self.get_device_track_name(device) + " - " + str(device.name)
        self._control_surface.show_message(prefix + name + suffix)

    def get_device_track_name(self, device):
        while device is not None and not isinstance(device, Live.Track.Track):
            device = getattr(device, "canonical_parent", None)
        return str(device.name) if device is not None else ""

    # Precision button
    def update_mode_toggle_button(self):
        if self._mode_toggle_button is not None and self.is_enabled():
            if self._mode_toggle_button is not None:
                if self._device is not None:
                    off_value = "Device.ModeToggle.Stepless" if self._stepless_mode else "Device.ModeToggle.Normal"
                    self._mode_toggle_button.set_on_off_values("Device.ModeToggle.Precision", off_value)
                    if self._precision_mode:
                        self._mode_toggle_button.turn_on()
                    else:
                        self._mode_toggle_button.turn_off()
                else:
                    self._mode_toggle_button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
                    self._mode_toggle_button.turn_off()

    def _mode_toggle_value(self, value, sender):
        assert self._mode_toggle_button is not None
        assert value in range(128)

        if self.is_enabled():
            if not sender.is_momentary() or value != 0:
                self._last_mode_toggle_button_press = time.time()
            else:
                if time.time() - self._last_mode_toggle_button_press > 0.5:
                    self._last_mode_toggle_button_press = time.time()
                    self._stepless_mode = not self._stepless_mode
                    self.update_mode_toggle_button()
                    if self._stepless_mode:
                        self._control_surface.show_message("stepless faders mode")
                    else:
                        self._control_surface.show_message("normal faders mode")
                    for slider in self._sliders:
                        slider.set_stepless_mode(self._stepless_mode)
                else:
                    self._precision_mode = not self._precision_mode
                    self.update_mode_toggle_button()
                    for slider in self._sliders:
                        slider.set_precision_mode(self._precision_mode)

    def set_mode_toggle_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._mode_toggle_button != button:
            if self._mode_toggle_button is not None:
                self._mode_toggle_button.remove_value_listener(self._mode_toggle_value)
            self._mode_toggle_button = button
            if self._mode_toggle_button is not None:
                assert isinstance(button, ButtonElement)
                self._mode_toggle_button.add_value_listener(self._mode_toggle_value, identify_sender=True)
                self.update()

    # ON OFF button
    def update_on_off_button(self):
        # on/off button
        if self._on_off_button is not None and self.is_enabled():
            if self._on_off_button is not None:
                parameter = self._on_off_parameter()
                if parameter is not None:
                    self._on_off_button.set_on_off_values("Mode.Device.On", "Mode.Device.Off")
                    if parameter.is_enabled and parameter.value > 0:
                        self._on_off_button.turn_on()
                    else:
                        self._on_off_button.turn_off()
                else:
                    self._on_off_button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
                    self._on_off_button.turn_off()

    def _on_off_value(self, value):
        if self._on_off_button is not None and self.is_enabled():
            DeviceComponent._on_off_value(self, value)
            self.update_on_off_button()

    def set_on_off_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._on_off_button != button:
            if self._on_off_button is not None:
                self._on_off_button.remove_value_listener(self._on_off_value)
            self._on_off_button = button
            if self._on_off_button is not None:
                assert isinstance(button, ButtonElement)
                self._on_off_button.add_value_listener(self._on_off_value)

    # TRACKS Buttons
    def update_track_buttons(self):
        # tracks
        if self.is_enabled():
            if self._prev_track_button is not None:
                self._prev_track_button.set_on_off_values("Mode.Track.On", "Mode.Track.Off")

                if (
                    self.selected_track_idx is not None
                    and self.selected_track_idx > 0
                    and not self._is_locked_to_device
                ):
                    self._prev_track_button.turn_on()
                else:
                    self._prev_track_button.turn_off()

            if self._next_track_button is not None:
                self._next_track_button.set_on_off_values("Mode.Track.On", "Mode.Track.Off")

                if (
                    self.selected_track_idx is not None
                    and self.selected_track_idx < len(self.song().tracks) - 1
                    and not self._is_locked_to_device
                ):
                    self._next_track_button.turn_on()
                else:
                    self._next_track_button.turn_off()

    def set_next_track_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._next_track_button != button:
            if self._next_track_button is not None:
                self._next_track_button.remove_value_listener(self._next_track_value)
            self._next_track_button = button
            if self._next_track_button is not None:
                assert isinstance(button, ButtonElement)
                self._next_track_button.add_value_listener(self._next_track_value, identify_sender=True)

    def _next_track_value(self, value, sender):
        assert self._next_track_button is not None
        assert value in range(128)
        if self.is_enabled():
            if (not sender.is_momentary()) or (value != 0):
                if (
                    self.selected_track_idx is not None
                    and self.selected_track_idx < len(self.song().tracks) - 1
                    and not self._is_locked_to_device
                ):
                    for offset in range(1, len(self.song().tracks) - self.selected_track_idx):
                        if self.song().tracks[self.selected_track_idx + offset].is_visible:
                            self.song().view.selected_track = self.song().tracks[self.selected_track_idx + offset]
                            self.update()
                            break

    def set_prev_track_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._prev_track_button != button:
            if self._prev_track_button is not None:
                self._prev_track_button.remove_value_listener(self._prev_track_value)
            self._prev_track_button = button
            if self._prev_track_button is not None:
                assert isinstance(button, ButtonElement)
                self._prev_track_button.set_on_off_values("Mode.Device.On", "Mode.Device.Off")
                self._prev_track_button.add_value_listener(self._prev_track_value, identify_sender=True)

    def _prev_track_value(self, value, sender):
        assert self._prev_track_button is not None
        assert value in range(128)
        if (not sender.is_momentary()) or (value != 0):
            if self.is_enabled():
                if (
                    self.selected_track_idx is not None
                    and self.selected_track_idx > 0
                    and not self._is_locked_to_device
                ):
                    for offset in range(1, self.selected_track_idx + 1):
                        if self.song().tracks[self.selected_track_idx - offset].is_visible:
                            self.song().view.selected_track = self.song().tracks[self.selected_track_idx - offset]
                            self.update()
                            break

    @property
    def selected_track_idx(self):
        tracks = list(self.song().tracks)
        result = tracks.index(self.song().view.selected_track) if self.song().view.selected_track in tracks else None
        return result

    # return self.tuple_idx(self.song().tracks, self.song().view.selected_track)

    def selected_track(self):
        return self.song().view.selected_track

    # DEVICES

    def update_device_buttons(self):

        if self.is_enabled():
            if self._prev_device_button is not None:
                self._prev_device_button.set_on_off_values("Mode.Device.On", "Mode.Device.Off")
                if self.song().appointed_device:
                    if self._get_previous_device(self.song().appointed_device):
                        self._prev_device_button.turn_on()
                    else:
                        self._prev_device_button.turn_off()
                else:
                    self._prev_device_button.turn_off()

            if self._next_device_button is not None:
                self._next_device_button.set_on_off_values("Mode.Device.On", "Mode.Device.Off")
                if self.song().appointed_device:
                    if self._get_next_device(self.song().appointed_device):
                        self._next_device_button.turn_on()
                    else:
                        self._next_device_button.turn_off()
                else:
                    self._next_device_button.turn_off()

    # DEVICE NAVIGATION LISTENERES
    def set_next_device_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._next_device_button != button:
            if self._next_device_button is not None:
                self._next_device_button.remove_value_listener(self._next_device_value)
            self._next_device_button = button
            if self._next_device_button is not None:
                assert isinstance(button, ButtonElement)
                self._next_device_button.add_value_listener(self._next_device_value, identify_sender=True)

    def _next_device_value(self, value, sender):
        assert self._next_device_button is not None
        assert value in range(128)
        if self.is_enabled():
            if (not sender.is_momentary()) or (value != 0):
                if self.selected_track() is not None:
                    device = self._get_next_device(self.song().appointed_device)
                    if device:
                        self.song().view.select_device(device)
                        self.update()

    def set_prev_device_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._prev_device_button != button:
            if self._prev_device_button is not None:
                self._prev_device_button.remove_value_listener(self._prev_device_value)
            self._prev_device_button = button
            if self._prev_device_button is not None:
                assert isinstance(button, ButtonElement)
                self._prev_device_button.add_value_listener(self._prev_device_value, identify_sender=True)

    def _prev_device_value(self, value, sender):
        assert self._prev_device_button is not None
        assert value in range(128)
        if self.is_enabled():
            if (not sender.is_momentary()) or (value != 0):
                if self.selected_track() is not None:
                    device = self._get_previous_device(self.song().appointed_device)
                    if device:
                        self.song().view.select_device(device)
                        self.update()

    def _get_next_device(self, device):
        return next_device(device, self.selected_track())

    def _get_previous_device(self, device):
        return previous_device(device, self.selected_track())

    # DEVICE BANK BUTTONS
    def set_prev_bank_button(self, button):
        self._prev_bank_button = button
        if (
            self._prev_bank_button is not None
            and self._next_bank_button is not None
            or self._prev_bank_button is None
            and self._next_bank_button is None
        ):
            self.set_bank_nav_buttons(self._prev_bank_button, self._next_bank_button)

    def set_next_bank_button(self, button):
        self._next_bank_button = button
        if (
            self._prev_bank_button is not None
            and self._next_bank_button is not None
            or self._prev_bank_button is None
            and self._next_bank_button is None
        ):
            self.set_bank_nav_buttons(self._prev_bank_button, self._next_bank_button)
