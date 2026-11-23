"""Pro session side buttons. Each one is a modifier held while pads or the bottom row are
pressed, has its own press/release action (tap, double tap, long press) and its own LED.
SpecialProSessionComponent describes all eight in one table."""

import time
from types import SimpleNamespace

from _Framework.ButtonElement import ButtonElement

# Two releases closer than this are a double tap.
DOUBLE_TAP = 0.25
# A press held at least this long is a long press.
LONG_PRESS = 0.5


class ModifierButton:
    """One side button: listener, held state, press/release times and LED.

    ``is_active()`` gates everything (pro session on and enabled). ``on_press(modifier, now)``
    and ``on_release(modifier, now)`` run after the held state and press time are updated
    (unless ``tracks_held`` is False: then the callbacks manage them); ``released_at`` is
    updated after ``on_release``, so the callback can ask ``is_double_tap(now)``.
    ``refresh()`` runs after either. ``skin()`` and ``is_lit()`` give the LED.
    """

    def __init__(self, is_active, skin, is_lit, on_press, on_release, refresh, tracks_held=True):
        self._is_active = is_active
        self._skin = skin
        self._is_lit = is_lit
        self._on_press = on_press
        self._on_release = on_release
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
            self.button.turn_off()

    def is_double_tap(self, now):
        return now - self.released_at < DOUBLE_TAP

    def is_long_press(self, now):
        return now - self.pressed_at >= LONG_PRESS

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
        self._refresh()

    def update(self):
        if self._is_active() and self.button != None:
            self.button.set_on_off_values(self._skin())
            if self._is_lit():
                self.button.turn_on()
            else:
                self.button.turn_off()


def modifier_table(*names_and_buttons):
    """A namespace of ModifierButtons by name, which also iterates in table order."""
    table = SimpleNamespace(**dict(names_and_buttons))
    table.all = tuple(button for _, button in names_and_buttons)
    return table
