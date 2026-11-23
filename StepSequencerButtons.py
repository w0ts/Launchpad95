"""The drum step sequencer's buttons: side buttons 0-3 and 7 and the left/right top
buttons. Mixin for StepSequencerComponent."""

from _Framework.ButtonElement import ButtonElement

from .PressButton import PressButton, ignore
from .StepSequencerSettings import (
    QUANTIZATION_MAP,
    QUANTIZATION_NAMES,
    STEPSEQ_MODE_MULTINOTE,
    STEPSEQ_MODE_NORMAL,
    STEPSEQ_MODE_SCALE_EDIT,
)

# A release this long after the press is a long press; two releases closer than
# MUTE_LATCH latch the mute shift.
MODE_LONG_PRESS = 0.25
QUANTIZE_LONG_PRESS = 0.5
LOCK_LONG_PRESS = 0.5
MUTE_LATCH = 0.25


class StepSequencerButtons:
    # side buttons (PressButton): 1 lock, 2 quantization, 3 mode, 7 mute shift
    def _side_button(self, index, on_press, on_release, paint, refresh=None):
        """A side button that acts while there is a clip (see PressButton)."""
        press_button = PressButton(self._has_clip, on_press, on_release, paint, refresh)
        press_button.set_button(self._side_buttons[index])
        return press_button

    def _has_clip(self):
        return self.is_enabled() and self._clip != None

    def _set_mode_function(self):  # Change the resolution of the sequencer
        self._mode_button = self._side_button(3, ignore, self._on_mode_release, self._paint_mode_button)  # SndB
        self._number_of_lines_per_note = 1

    def _set_lock_function(self):
        self._is_locked = False
        self._lock_to_track = False
        self._lock_button = self._side_button(1, ignore, self._on_lock_release, self._paint_lock_button)  # Pan
        self._selected_track = None

    def _set_mute_shift_function(self):  # Allow to mute notes in the grid or all notes if selecting on Note Selector
        self._is_mute_shifted = False
        self._mute_shift_button = self._side_button(
            7,
            self._on_mute_shift_press,
            self._on_mute_shift_release,
            self._paint_mute_shift_button,
            refresh=self._on_mute_shift_changed,
        )  # Arm

    def _set_quantization_function(self):
        self._quantization_index = 2
        self.set_quantization(QUANTIZATION_MAP[self._quantization_index])
        self._quantization_button = self._side_button(
            2, ignore, self._on_quantization_release, self._paint_quantization_button
        )  # SndA

    # SCALE button (0): held, the scale editor
    def _update_scale_selector_button(self):
        if self.is_enabled():
            if self._scale_selector_button != None:
                if self._clip != None:
                    self._scale_selector_button.set_on_off_values("StepSequencer.Scale")
                else:
                    self._scale_selector_button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
                if self._mode == STEPSEQ_MODE_SCALE_EDIT:
                    self._scale_selector_button.turn_on()
                    if self._osd != None:
                        self._osd.set_mode("Scale")
                else:
                    self._scale_selector_button.turn_off()

    def set_scale_selector_button(self, button):  # remove old scale button listener and adds new one
        assert isinstance(button, (ButtonElement, type(None)))
        if self._scale_selector_button != button:
            if self._scale_selector_button != None:
                self._scale_selector_button.remove_value_listener(self._scale_selector_button_value)
            self._scale_selector_button = button
            if self._scale_selector_button != None:
                assert isinstance(button, ButtonElement)
                self._scale_selector_button.add_value_listener(self._scale_selector_button_value)

    def _scale_selector_button_value(self, value):
        assert value in range(128)
        if self.is_enabled():

            if value > 0:
                self._mode_backup = self._mode
                if self._scale_selector != None and self._note_selector != None:
                    self._scale_selector.set_octave(int(self._note_selector._root_note / 12))
                    self._scale_selector.set_key(self._note_selector._key)
                    self.set_mode(STEPSEQ_MODE_SCALE_EDIT)
            else:
                if self._scale_selector != None and self._note_selector != None:
                    self._note_selector.set_scale(self._scale_selector.notes, self._scale_selector._key)
                    self._note_selector.set_selected_note(self._scale_selector._octave * 12 + self._scale_selector._key)
                    self._scale_updated()
                self.set_mode(self._mode_backup)

    # MUTE SHIFT button (7): held, pads add or mute notes muted; double tap latches it
    def _update_mute_shift_button(self):
        if self._mute_shift_button is not None:
            self._mute_shift_button.update()

    def _paint_mute_shift_button(self, button):
        if self.is_enabled():
            if self._clip != None and self._clip.is_midi_clip:
                button.set_on_off_values("StepSequencer.Mute")
                if self._is_mute_shifted:
                    button.turn_on()
                else:
                    button.turn_off()
            else:
                button.set_light("DefaultButton.Disabled")

    def _on_mute_shift_press(self, press_button, now):
        self._is_mute_shifted = not self._is_mute_shifted

    def _on_mute_shift_release(self, press_button, now):
        if press_button.since_release(now) > MUTE_LATCH:
            self._is_mute_shifted = not self._is_mute_shifted  # held: momentary
        elif self._is_mute_shifted:
            self._control_surface.show_message("Mute mode locked ON (double-tap mute to unlock)")
        else:
            self._control_surface.show_message("Mute mode unlocked")

    def _on_mute_shift_changed(self):
        self._note_editor._is_mute_shifted = self._is_mute_shifted
        self._update_mute_shift_button()

    # MODE button (3): normal / multinote; long press in multinote: one or two rows per note
    def _update_mode_button(self):
        if self._mode_button is not None:
            self._mode_button.update()

    def _paint_mode_button(self, button):
        if self.is_enabled():
            if self._clip != None:
                button.set_on_off_values("StepSequencer.Mode")
                if self._mode == STEPSEQ_MODE_MULTINOTE:
                    button.turn_on()
                else:
                    button.turn_off()
                if self._osd != None:
                    self._osd.update()
            else:
                button.set_light("DefaultButton.Disabled")

    def _on_mode_release(self, press_button, now):
        if self._mode == STEPSEQ_MODE_MULTINOTE and press_button.held_for(now) > MODE_LONG_PRESS:
            number_of_lines_per_note = 2 if self._number_of_lines_per_note == 1 else 1
            self.set_mode(STEPSEQ_MODE_MULTINOTE, number_of_lines_per_note)
        elif self._mode != STEPSEQ_MODE_MULTINOTE:
            self.set_mode(STEPSEQ_MODE_MULTINOTE, self._number_of_lines_per_note)
        else:
            self.set_mode(STEPSEQ_MODE_NORMAL, self._number_of_lines_per_note)
        self._scale_updated()

    # QUANTIZE button (2): tap the next step length; long press duplicates the clip
    def _update_quantization_button(self):
        if self._quantization_button is not None:
            self._quantization_button.update()

    def _paint_quantization_button(self, button):
        if self.is_enabled():
            if self._clip != None:
                button.set_light(self.QUANTIZATION_COLOR_MAP[self._quantization_index])
            else:
                button.set_light("DefaultButton.Disabled")

    def _on_quantization_release(self, press_button, now):
        if press_button.held_for(now) > QUANTIZE_LONG_PRESS:
            self._control_surface.show_message("Step Sequencer: duplicate clip")
            self.duplicate_clip()
            return
        step = -1 if self._mode == STEPSEQ_MODE_SCALE_EDIT else 1
        self._quantization_index = (self._quantization_index + step) % len(QUANTIZATION_MAP)
        self.set_quantization(QUANTIZATION_MAP[self._quantization_index])
        self._control_surface.show_message("QUANTIZATION : " + QUANTIZATION_NAMES[self._quantization_index])
        self._update_quantization_button()

    def updateQuantizationButton(self):
        if self.is_enabled() and self._quantization_button.button != None and self._playhead != None:
            if self._beat == int(self._playhead):
                self._quantization_button.button.set_light(self.QUANTIZATION_COLOR_MAP_LOW[self._quantization_index])
            else:
                self._beat = int(self._playhead)
                self._update_quantization_button()

    # LOCK button (1): tap locks to (or unlocks from) the clip; long press locks to the track
    def _update_lock_button(self):
        if self._lock_button is not None:
            self._lock_button.update()

    def _paint_lock_button(self, button):
        if self.is_enabled():
            if self._clip != None:
                button.set_on_off_values(
                    "StepSequencer.Lock.ToTrack" if self._lock_to_track else "StepSequencer.Lock.ToClip"
                )
                if self._is_locked:
                    button.turn_on()
                else:
                    button.turn_off()
            else:
                button.set_light("DefaultButton.Disabled")

    def _on_lock_release(self, press_button, now):
        if press_button.held_for(now) > LOCK_LONG_PRESS:
            self._lock_to_track = not self._lock_to_track
            if not self._is_locked:
                self._control_surface.show_message("stepseq : locked to clip '" + str(self._clip.name) + "'")
                self._is_locked = True
            self._update_lock_button()
        else:
            self._is_locked = not self._is_locked
            if self._is_locked:
                self._control_surface.show_message("stepseq : locked to clip '" + str(self._clip.name) + "'")
            self._update_lock_button()
            self._update_OSD()

    # LEFT / RIGHT buttons: scroll the loop pages
    def _update_right_button(self):
        if self.is_enabled():
            if self._right_button != None:
                if self._clip != None:
                    self._right_button.set_on_off_values("DefaultButton")
                    if self._loop_selector.can_scroll(1):
                        self._right_button.turn_on()
                    else:
                        self._right_button.turn_off()
                else:
                    self._right_button.set_light("DefaultButton.Disabled")

    def set_right_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if button != self._right_button:
            if self._right_button != None:
                self._right_button.remove_value_listener(self._right_value)
            self._right_button = button
            if self._right_button != None:
                self._right_button.add_value_listener(self._right_value, identify_sender=True)

    def _right_value(self, value, sender):
        assert self._right_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None:
            if (value != 0) or (not sender.is_momentary()):
                self._loop_selector.scroll(1)
                self._note_editor.request_display_page()
                self.update()

    def _update_left_button(self):
        if self.is_enabled():
            if self._left_button != None:
                if self._clip != None:
                    self._left_button.set_on_off_values("DefaultButton")
                    if self._loop_selector.can_scroll(-1):
                        self._left_button.turn_on()
                    else:
                        self._left_button.turn_off()
                else:
                    self._left_button.set_light("DefaultButton.Disabled")

    def set_left_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if button != self._left_button:
            if self._left_button != None:
                self._left_button.remove_value_listener(self._left_value)
            self._left_button = button
            if self._left_button != None:
                self._left_button.add_value_listener(self._left_value, identify_sender=True)

    def _left_value(self, value, sender):
        assert self._left_button != None
        assert value in range(128)
        if self.is_enabled() and self._clip != None:
            if (value != 0) or (not sender.is_momentary()):
                self._loop_selector.scroll(-1)
                self._note_editor.request_display_page()
                self.update()
