"""One column of the device controller: eight pads that control one device parameter.

Everything runs on Live's main thread: pad presses and parameter changes arrive as
listener calls, and the device controller calls tick() from Live's update_display while
device mode is on (stepless slides, the press-time colours of Settings.ENABLE_TDC).
"""

import time

from .ButtonSliderElement import ButtonSliderElement
from .ParameterSlides import timed_rate, velocity_rate
from .Settings import Settings

SLIDER_MODE_OFF = 0
SLIDER_MODE_TOGGLE = 1
SLIDER_MODE_SLIDER = 2
SLIDER_MODE_PRECISION_SLIDER = 3
SLIDER_MODE_SMALL_ENUM = 4
SLIDER_MODE_BIG_ENUM = 5

DISABLED = "DefaultButton.Disabled"
# Pads 0-3 step down, pads 4-7 step up (big enums and the precision slider).
FIRST_UP_PAD = 4
MAX_TIMED_STEP = 9


def _step_size(index):
    """1, 2, 4, 8 from the middle pads outwards."""
    return 2 ** (index - FIRST_UP_PAD) if index >= FIRST_UP_PAD else 2 ** (FIRST_UP_PAD - 1 - index)


class DeviceControllerStrip(ButtonSliderElement):
    def __init__(self, buttons, column, parent, slides):
        ButtonSliderElement.__init__(self, buttons)
        self._column = column
        self._parent = parent
        self._slides = slides
        self._num_buttons = len(buttons)
        self._value_map = tuple(float(index) / (self._num_buttons - 1) for index in range(self._num_buttons))
        self._last_value_map_index = -1
        self._precision_mode = False
        self._stepless_mode = False
        self._enabled = True
        self._update_primed = False
        self._timed_mode = Settings.ENABLE_TDC
        self._timed_start = 0
        self._timed_step = 0
        self._timed_step_size = Settings.TDC_MAX_TIME / len(Settings.TDC_MAP)
        self._last_pressed_index = -1
        self._primed_target_value = None

    # -- settings from the device controller
    def set_enabled(self, enabled):
        self._enabled = enabled
        if not enabled:
            self._end_timed_press()

    def set_precision_mode(self, precision_mode):
        self._precision_mode = precision_mode
        self.update()

    def set_stepless_mode(self, stepless_mode):
        self._stepless_mode = stepless_mode
        self.update()

    # -- the mapped parameter
    @property
    def _parameter(self):
        return self._parameter_to_map_to

    @property
    def _value(self):
        return self._parameter.value if self._parameter is not None else 0

    @property
    def _max(self):
        return self._parameter.max if self._parameter is not None else 0

    @property
    def _min(self):
        return self._parameter.min if self._parameter is not None else 0

    @property
    def _range(self):
        return self._max - self._min

    @property
    def _mode(self):
        parameter = self._parameter
        if parameter is None:
            return SLIDER_MODE_OFF
        if parameter.is_quantized:
            if self._range == 1:
                return SLIDER_MODE_TOGGLE
            if self._range < self._num_buttons:  # range + 1 values, one per button
                return SLIDER_MODE_SMALL_ENUM
            return SLIDER_MODE_BIG_ENUM
        return SLIDER_MODE_PRECISION_SLIDER if self._precision_mode else SLIDER_MODE_SLIDER

    def param_name(self):
        return self._parameter.name if self._parameter is not None else "None"

    def param_value(self):
        return self._parameter.value if self._parameter is not None else 0

    def release_parameter(self):
        self._end_timed_press()  # a pad held while the column is remapped does nothing
        ButtonSliderElement.release_parameter(self)

    # -- LEDs
    def update(self):
        if not self._enabled:
            return
        painters = {
            SLIDER_MODE_TOGGLE: self._toggle_names,
            SLIDER_MODE_SMALL_ENUM: self._small_enum_names,
            SLIDER_MODE_BIG_ENUM: self._up_down_names,
            SLIDER_MODE_SLIDER: self._slider_names,
            SLIDER_MODE_PRECISION_SLIDER: self._up_down_names,
        }
        painter = painters.get(self._mode)
        self._update_buttons(painter() if painter is not None else self._off_names())

    def reset(self):
        self._update_buttons(self._off_names())

    def reset_if_no_parameter(self):
        if self._parameter is None:
            self.reset()
        else:
            self._update_primed = True

    def _off_names(self):
        return [DISABLED] * self._num_buttons

    def _toggle_names(self):
        names = self._off_names()
        names[0] = "Device.Toggle.On" if self._value == self._max else "Device.Toggle.Off"
        return names

    def _small_enum_names(self):
        names = self._off_names()
        for index in range(int(self._range + 1)):
            names[index] = "Device.Enum.On" if self._value == index + self._min else "Device.Enum.Off"
        return names

    def _up_down_names(self):
        """Big enums and the precision slider: one pad down, one pad up."""
        prefix = "Device.BigEnum" if self._mode == SLIDER_MODE_BIG_ENUM else "Device.PrecisionSlider"
        names = self._off_names()
        names[FIRST_UP_PAD - 1] = prefix + (".On" if self._value > self._min else ".Off")
        names[FIRST_UP_PAD] = prefix + (".On" if self._value < self._max else ".Off")
        return names

    def _slider_names(self):
        names = self._off_names()
        update_index = 0
        for index in range(self._num_buttons):
            name, lit = self._slider_pad(index)
            names[index] = name
            if lit:
                update_index = index
            if self._timed_start > 0 and self._stepless_mode and index == self._last_pressed_index:
                names[index] = "Device.ColorSteps.Step" + str(self._timed_step)
        self._last_value_map_index = update_index
        return names

    def _slider_pad(self, index):
        """(skin name, whether the value reaches into the pad) of one slider pad."""
        current = self._value_map[index]
        previous = self._value_map[max(0, index - 1)]
        third = (current - previous) / 3
        window = current * self._range + self._min
        one_third = (previous + third) * self._range + self._min
        two_thirds = (previous + third * 2) * self._range + self._min
        custom = "Device.CustomSlider" + str(self._column)
        if self._value >= window:
            return (custom if Settings.USE_CUSTOM_DEVICE_CONTROL_COLORS else "Device.DefaultSlider") + ".On", True
        if not Settings.USE_CUSTOM_DEVICE_CONTROL_COLORS:
            return "Device.DefaultSlider.Off", False
        if one_third <= self._value < two_thirds:
            return custom + ".Third", True
        if two_thirds <= self._value < window:
            return custom + ".Half", True
        return custom + ".Off", False

    def _update_buttons(self, names):
        assert len(names) == len(self._buttons)
        for button, name in zip(self._buttons, names, strict=True):
            button.set_on_off_values(name, name)
            if name.endswith("On"):
                button.turn_on()
            else:
                button.turn_off()

    def _is_update_needed(self):
        if self._update_primed:
            self._update_primed = False
            return True
        if self._last_value_map_index == -1:
            return True
        # same window test as _slider_names, on the normalized value
        normalized = (self._value - self._min) / self._range if self._range else 0.0
        index = 0
        for i, threshold in enumerate(self._value_map):
            if normalized >= threshold:
                index = i
        return index != self._last_value_map_index

    # -- pads
    def _button_value(self, value, sender):
        assert isinstance(value, int)
        assert sender in self._buttons
        self._last_sent_value = -1
        if self._parameter is None or not self._enabled:
            return
        index = list(self._buttons).index(sender)
        if value != 0 or not sender.is_momentary():
            self._pad_pressed(index, value)
        elif self._timed_mode and index == self._last_pressed_index:
            self._pad_released()

    def _pad_pressed(self, index, velocity):
        target = self._target_for_pad(index)
        if self._timed_mode:
            self._primed_target_value = target
            self._timed_step = 0
            self._timed_start = time.time()
            self._last_pressed_index = index
        else:
            self._move_to(target, velocity_rate(velocity))
        self._refresh()

    def _pad_released(self):
        press_seconds = time.time() - self._timed_start
        target = self._primed_target_value
        self._end_timed_press()
        self._move_to(target, timed_rate(self._range, press_seconds))
        self._refresh()

    def _end_timed_press(self):
        self._timed_start = 0
        self._last_pressed_index = -1
        self._primed_target_value = None
        self._timed_step = 0

    def _target_for_pad(self, index):
        mode = self._mode
        if mode == SLIDER_MODE_TOGGLE:
            if index != 0:
                return self._value
            return self._min if self._value == self._max else self._max
        if mode == SLIDER_MODE_SMALL_ENUM:
            return index + self._min
        if mode == SLIDER_MODE_SLIDER:
            return self._value_map[index] * self._range + self._min
        if mode == SLIDER_MODE_BIG_ENUM:
            return self._stepped(index, 1)
        if mode == SLIDER_MODE_PRECISION_SLIDER:
            unit = float(self._range) / 128
            if self._range > 7 and unit < 1:
                unit = 1
            return self._stepped(index, unit)
        return self._value

    def _stepped(self, index, unit):
        """The value one press of an up/down pad leads to, clamped to the range."""
        if index >= FIRST_UP_PAD:
            return min(self._value + unit * _step_size(index), self._max)
        return max(self._value - unit * _step_size(index), self._min)

    def _move_to(self, target, rate):
        parameter = self._parameter
        if self._stepless_mode and self._mode == SLIDER_MODE_SLIDER:
            self._slides.start(parameter, target, rate)
        else:
            self._slides.stop(parameter)
            parameter.value = target

    def _refresh(self):
        self.update()
        self._custom_update_OSD()

    # -- device controller tick
    def tick(self, now):
        """Advance the press-time colour of a held pad (Settings.ENABLE_TDC)."""
        if self._timed_start > 0 and self._enabled:
            step = min(MAX_TIMED_STEP, int((now - self._timed_start) // self._timed_step_size))
            if step != self._timed_step:
                self._timed_step = step
                self._refresh()

    # -- parameter listener (connect_to calls it with trigger_osd=False)
    def _on_parameter_changed(self, trigger_osd=True):
        if self._enabled:
            assert self._parameter is not None
            if self._is_update_needed():
                self.update()
            self._custom_update_OSD(trigger_osd)

    def _custom_update_OSD(self, trigger_osd=True):
        osd = self._parent._osd
        if osd is None:
            return
        osd.mode = "Device Controller"
        name = self.param_name()
        if name != "None":
            osd.attribute_names[self._column] = str(name)
            osd.attributes[self._column] = str(self.param_value())
        else:
            osd.attribute_names[self._column] = " "
            osd.attributes[self._column] = " "
        if trigger_osd:
            osd.update()
