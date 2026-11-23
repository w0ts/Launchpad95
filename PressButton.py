"""A side button with its own press/release actions (tap, double tap, long press, held as a
modifier) and its own LED: the one listener/timing pattern the pro session and the step
sequencers use for their side buttons."""

import time

from _Framework.ButtonElement import ButtonElement

# Two releases closer than this are a double tap (pro session).
DOUBLE_TAP = 0.25
# A press held at least this long is a long press (pro session).
LONG_PRESS = 0.5


class PressButton:
    """One button: its listener, held state, press/release times and LED.

    ``is_active()`` gates the presses. ``on_press(press_button, now)`` and
    ``on_release(press_button, now)`` run after ``held`` and ``pressed_at`` are updated
    (unless ``tracks_held`` is False: then the callbacks manage them); ``released_at`` is
    updated after ``on_release``, so a callback can compare ``now`` with the previous
    release. ``refresh()`` runs after either; ``paint(button)`` draws the LED on update().
    """

    def __init__(self, is_active, on_press, on_release, paint=None, refresh=None, tracks_held=True):
        self._is_active = is_active
        self._on_press = on_press
        self._on_release = on_release
        self._paint = paint
        self._refresh = refresh
        self._tracks_held = tracks_held
        self.button = None
        self.held = False
        self.pressed_at = time.time()
        self.released_at = time.time()

    def set_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self.button != None:
            self.button.remove_value_listener(self._on_value)
        self.button = button
        if self.button != None:
            self.button.add_value_listener(self._on_value, identify_sender=True)

    def held_for(self, now):
        """Seconds since the last press."""
        return now - self.pressed_at

    def since_release(self, now):
        """Seconds since the previous release."""
        return now - self.released_at

    def is_double_tap(self, now):
        return self.since_release(now) < DOUBLE_TAP

    def is_long_press(self, now):
        return self.held_for(now) >= LONG_PRESS

    def _on_value(self, value, sender):
        assert value in range(128)
        if not self._is_active() or self.button == None:
            return
        now = time.time()
        if value != 0 or not sender.is_momentary():
            if self._tracks_held:
                self.held = True
                self.pressed_at = now
            self._on_press(self, now)
        else:
            if self._tracks_held:
                self.held = False
            self._on_release(self, now)
            if self._tracks_held:
                self.released_at = now
        if self._refresh is not None:
            self._refresh()

    def update(self):
        if self._paint is not None and self.button != None:
            self._paint(self.button)


def ignore(press_button, now):
    """For a press (or release) that only starts (or ends) the timing."""


def lit_painter(is_active, skin, is_lit):
    """paint() for a button with one skin, lit while ``is_lit()``; only while ``is_active()``."""

    def paint(button):
        if is_active():
            button.set_on_off_values(skin())
            if is_lit():
                button.turn_on()
            else:
                button.turn_off()

    return paint
