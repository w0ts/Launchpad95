"""Stepless parameter slides of the device controller, advanced on Live's main thread.

A slide moves one device parameter towards a target at a speed given in parameter units
per second. The device controller advances every running slide from its tick (Live's
update_display, about every 100 ms) by the real time elapsed since the previous tick.

Timing: the old strip threads moved the parameters every ~5 ms and expressed every speed
per 50 ms period (RATE_PERIOD). The speeds below keep those per-second rates, so a slide
takes the same real time as before; it moves in ~100 ms steps instead of ~5 ms ones.

A slide stops when it reaches its target, when its parameter is gone (device deleted), or
when the parameter was moved by something else meanwhile (mouse, automation, another
controller), as before. Slides keep running when their column is remapped (bank or device
change), so a slow slide still ends where it was sent.
"""

from .Settings import Settings

# The period the speed settings are expressed in (the old ROUNDTRIP_TARGET).
RATE_PERIOD = 0.05
# Rounding used to tell our own writes from changes made by something else.
VALUE_DIGITS = 5


def timed_rate(value_range, press_seconds):
    """Speed (units/s) for a press of ``press_seconds`` (Settings.ENABLE_TDC): the longer
    the press, the slower the slide; TDC_MAP gives the seconds a full-range slide takes."""
    factor = min(1.0, press_seconds / Settings.TDC_MAX_TIME)
    full_range_seconds = Settings.TDC_MAP[int((len(Settings.TDC_MAP) - 1) * factor)]
    return value_range / max(full_range_seconds, RATE_PERIOD)


def velocity_rate(velocity):
    """Speed (units/s) for a pad velocity (ENABLE_TDC off); None means jump at once."""
    if velocity > Settings.VELOCITY_THRESHOLD_MAX:
        return None
    velocity = max(velocity, Settings.VELOCITY_THRESHOLD_MIN) ** 3
    return velocity / (Settings.VELOCITY_FACTOR * 127.0) / RATE_PERIOD


class _Slide:
    def __init__(self, parameter, target, rate):
        self.parameter = parameter
        self.target = target
        self.rate = rate
        self.last_value = parameter.value

    def advance(self, elapsed):
        """Move by ``elapsed`` seconds; False when the slide is over."""
        parameter = self.parameter
        if parameter == None:  # a deleted Live object compares equal to None
            return False
        value = parameter.value
        if round(value, VALUE_DIGITS) != round(self.last_value, VALUE_DIGITS):
            return False  # moved by something else: drop
        distance = abs(self.target - value)
        if round(distance, VALUE_DIGITS) == 0:
            return False  # there (Live keeps 32-bit floats: 6/7 never reads back exactly)
        offset = distance if self.rate is None else min(self.rate * elapsed, distance)
        new_value = value + offset if value < self.target else value - offset
        parameter.value = max(min(new_value, parameter.max), parameter.min)
        self.last_value = parameter.value
        return round(abs(self.target - self.last_value), VALUE_DIGITS) != 0


class ParameterSlides:
    """The running slides, one per parameter."""

    def __init__(self):
        self._slides = {}

    def start(self, parameter, target, rate):
        """Slide ``parameter`` to ``target``, replacing its running slide; the first step
        (one RATE_PERIOD) is taken at once, so a fast tap lands without waiting a tick."""
        slide = _Slide(parameter, target, rate)
        if slide.advance(RATE_PERIOD):
            self._slides[parameter._live_ptr] = slide
        else:
            self.stop(parameter)

    def stop(self, parameter):
        self._slides.pop(parameter._live_ptr, None)

    def target(self, parameter):
        """The target of the parameter's running slide, or None."""
        slide = self._slides.get(parameter._live_ptr)
        return None if slide is None else slide.target

    def is_sliding(self):
        return bool(self._slides)

    def advance(self, elapsed):
        for key, slide in list(self._slides.items()):
            if not slide.advance(elapsed):
                del self._slides[key]

    def clear(self):
        self._slides.clear()
