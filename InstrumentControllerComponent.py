from _Framework.ButtonElement import ButtonElement
from _Framework.CompoundComponent import CompoundComponent
from _Framework.SubjectSlot import subject_slot
from _Framework.Util import clamp

from .DrumRack import drum_rack_of
from .InstrumentPads import InstrumentPads
from .ScaleComponent import KEY_NAMES, MUSICAL_MODES, ScaleComponent
from .SongScaleListener import SongScaleListener
from .TrackControllerComponent import TrackControllerComponent


class InstrumentControllerComponent(SongScaleListener, InstrumentPads, CompoundComponent):

    def __init__(self, matrix, side_buttons, top_buttons, control_surface, note_repeat):
        super().__init__()
        self._control_surface = control_surface
        self._note_repeat = note_repeat
        self._osd = None
        self._matrix = None
        self._side_buttons = side_buttons
        self._remaining_buttons = []
        self._track_controller = None
        self.base_channel = 11
        self._quick_scales = [0, 1, 2, 3, 4, 5, 6, 7, 10, 13, 14, 15, 17, 18, 24]
        self._quick_scale_root = 0
        self._normal_feedback_velocity = int(self._control_surface._skin["Note.Feedback"])
        self._recordind_feedback_velocity = int(self._control_surface._skin["Note.FeedbackRecord"])
        self._drum_group_device = None
        self._octave_up_button = None
        self._octave_down_button = None
        self._scales_toggle_button = None
        self.set_scales_toggle_button(side_buttons[0])  # Enable scale selecting mode
        self.set_octave_up_button(side_buttons[2])  # Shift octave up
        self.set_octave_down_button(side_buttons[3])  # Shift octave down

        self._osd_mode_backup = "Instrument"

        self._track_controller = self.register_component(
            TrackControllerComponent(control_surface=control_surface, implicit_arm=True)
        )
        self._track_controller.set_enabled(False)

        # Clip navigation buttons
        self._track_controller.set_prev_scene_button(top_buttons[0])
        self._track_controller.set_next_scene_button(top_buttons[1])
        self._track_controller.set_prev_track_button(top_buttons[2])
        self._track_controller.set_next_track_button(top_buttons[3])

        # Clip edition buttons
        self._track_controller.set_undo_button(side_buttons[1])
        self._track_controller.set_start_stop_button(side_buttons[4])
        self._track_controller.set_lock_button(side_buttons[5])
        self._track_controller.set_solo_button(side_buttons[6])
        self._track_controller.set_session_record_button(side_buttons[7])

        self._scales = self.register_component(ScaleComponent(self._control_surface))
        # self._scales.set_enabled(False)
        self._scales.set_matrix(matrix)
        self._scales.set_osd(self._osd)

        self.set_matrix(matrix)

        self._on_session_record_changed.subject = self.song()
        self._on_swing_amount_changed_in_live.subject = self.song()
        self._note_repeat_selector = False
        self._note_repeat.set_enabled(False)

    def disconnect(self):
        self._remove_scale_listeners()
        super().disconnect()

    def set_enabled(self, enabled):
        CompoundComponent.set_enabled(self, enabled)
        if self._track_controller != None:
            self._track_controller.set_enabled(enabled)
        feedback_channels = [self.base_channel, self.base_channel + 1, self.base_channel + 2, self.base_channel + 3]
        # non_feedback_channel = self.base_channel + 4
        self._set_feedback_velocity()
        self._control_surface.set_feedback_channels(feedback_channels)
        if not enabled:
            self._control_surface.release_controlled_track()
            self._note_repeat.set_enabled(False)
            self._remove_scale_listeners()
        else:
            self._control_surface.set_controlled_track(self._track_controller.selected_track)
            self._register_scale_listeners()

        if self._track_controller != None:
            self._track_controller._do_implicit_arm(enabled)
            self._track_controller.set_enabled(enabled)

        if enabled:
            self._update_OSD()
            self.on_selected_track_changed()

    def _set_feedback_velocity(self):
        if self.song().session_record:
            self._control_surface._c_instance.set_feedback_velocity(self._recordind_feedback_velocity)
        else:
            self._control_surface._c_instance.set_feedback_velocity(self._normal_feedback_velocity)

    @subject_slot("session_record")
    def _on_session_record_changed(self):
        self._set_feedback_velocity()

    @subject_slot("swing_amount")
    def _on_swing_amount_changed_in_live(self):
        self.update()

    def _change_swing_amount_value(self, value):
        self._set_swing_amount_value(clamp(self.song().swing_amount + value * 0.025, 0.0, 0.99))

    def _set_swing_amount_value(self, value):
        self.song().swing_amount = value
        self._control_surface.show_message("REPEATER Swing amount: " + str(int(self._swing_amount() * 100)) + "%")

    def _swing_amount(self):
        return self.song().swing_amount

    def _toggle_note_repeat_selector(self):
        self._note_repeat_selector = not self._note_repeat_selector

    def _toggle_note_repeater(self):
        self._note_repeat.set_enabled(not self._note_repeat.is_enabled())

    # Refresh button and its listener
    def set_scales_toggle_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._scales_toggle_button != None:
            self._scales_toggle_button.remove_value_listener(self._scales_toggle)
        self._scales_toggle_button = button
        if self._scales_toggle_button != None:
            self._scales_toggle_button.add_value_listener(self._scales_toggle, identify_sender=True)
            self._scales_toggle_button.turn_off()

    # Refresh button and its listener
    def set_octave_up_button(self, button=None):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._octave_up_button != None:
            self._octave_up_button.remove_value_listener(self._scroll_octave_up)
        self._octave_up_button = button
        if self._octave_up_button != None:
            self._octave_up_button.add_value_listener(self._scroll_octave_up, identify_sender=True)
            self._octave_up_button.turn_off()

    # Refresh button and its listener
    def set_octave_down_button(self, button=None):
        assert isinstance(button, (ButtonElement, type(None)))
        if self._octave_down_button != None:
            self._octave_down_button.remove_value_listener(self._scroll_octave_down)
        self._octave_down_button = button
        if self._octave_down_button != None:
            self._octave_down_button.add_value_listener(self._scroll_octave_down, identify_sender=True)
            self._octave_down_button.turn_off()

    # Enables scale selection mode
    def _scales_toggle(self, value, sender):
        if self.is_enabled():
            if value != 0:
                self._get_drumrack_device()
                if self._scales.is_drumrack and self._drum_group_device != None:
                    self._toggle_note_repeat_selector()
                    self._scales_toggle_button.turn_on()
                else:
                    self._scales.set_enabled(True)
                    self._osd_mode_backup = self._osd.mode
                    self._osd.mode = self._osd_mode_backup + " - Scale"
                    self._scales_toggle_button.turn_on()
                    self._scales.update()
            else:
                self._scales_toggle_button.turn_off()
                self._scales.set_enabled(False)
                self._osd.mode = self._osd_mode_backup
                if not self._scales.is_quick_scale:
                    self._note_repeat.set_enabled(False)
                self.set_enabled(True)
                self.update()

    # Transposes key one octave up
    def _scroll_octave_up(self, value, sender):
        if self.is_enabled():
            if (not sender.is_momentary()) or (value != 0):
                if self._can_scroll_octave_up():
                    self._scales._octave += 1
                    self.update()

    def _can_scroll_octave_up(self):
        if self._scales.is_drumrack:
            if self._note_repeat_selector:
                return self._scales._octave < 6
            else:
                return self._scales._octave < 5
        else:
            return self._scales._octave < 10

    # Transposes key one octave down
    def _scroll_octave_down(self, value, sender):
        if self.is_enabled():
            if (not sender.is_momentary()) or (value != 0):
                if self._can_scroll_octave_down():
                    self._scales._octave -= 1
                    self.update()

    def _can_scroll_octave_down(self):
        if self._scales.is_drumrack:
            return self._scales._octave > 0
        else:
            return self._scales._octave > -2

    def setup_quick_scale_mode(self):

        self._quick_scale_root = (self._quick_scale_root + 1) % 3

        if self._quick_scale_root == 0:
            self._control_surface.show_message("quick scale : root")
        elif self._quick_scale_root == 1:
            self._control_surface.show_message("quick scale : modes")
        else:
            self._control_surface.show_message("quick scale : REPEATER")

    def update(self):
        if self.is_enabled():
            if self._track_controller != None:
                self._track_controller.set_enabled(True)

            self._update_matrix()

            for button in self._remaining_buttons:
                button.set_light("DefaultButton.Disabled")

            if self._scales_toggle_button != None:
                self._scales_toggle_button.set_on_off_values("Note.Scale")
                self._scales_toggle_button.turn_off()

            if self._octave_up_button != None:
                self._octave_up_button.set_on_off_values("Note.Octave")
                if self._can_scroll_octave_up():
                    self._octave_up_button.turn_on()
                else:
                    self._octave_up_button.turn_off()

            if self._octave_down_button != None:
                self._octave_down_button.set_on_off_values("Note.Octave")
                if self._can_scroll_octave_down():
                    self._octave_down_button.turn_on()
                else:
                    self._octave_down_button.turn_off()

            self._update_OSD()
            # self._control_surface.log_message("Swing Amount: " + str(self._swing_amount()))

    def set_osd(self, osd):
        self._osd = osd

    def _update_OSD(self):
        if self._osd != None:
            if self._scales.is_quick_scale:
                self._osd.mode = "Instrument (quick scale)"
            else:
                self._osd.mode = "Instrument"
            self._osd.attributes[0] = MUSICAL_MODES[self._scales._modus * 2]
            self._osd.attribute_names[0] = "Scale"
            self._osd.attributes[1] = KEY_NAMES[self._scales._key % 12]
            self._osd.attribute_names[1] = "Root Note"
            self._osd.attributes[2] = self._scales._octave
            self._osd.attribute_names[2] = "Octave"
            self._osd.attributes[3] = " "
            self._osd.attribute_names[3] = " "
            self._osd.attributes[4] = " "
            self._osd.attribute_names[4] = " "
            self._osd.attributes[5] = " "
            self._osd.attribute_names[5] = " "
            self._osd.attributes[6] = " "
            self._osd.attribute_names[6] = " "
            self._osd.attributes[7] = " "
            self._osd.attribute_names[7] = " "

            if self._track_controller.selected_track != None:
                self._osd.info[0] = "track : " + self._track_controller.selected_track.name
            else:
                self._osd.info[0] = " "

            self._osd.info[1] = " "
            self._osd.update()

    # Refresh matrix and its listener
    def set_matrix(self, matrix):
        self._matrix = matrix
        if matrix:
            matrix.reset()
        if matrix != self._matrix:
            if self._matrix != None:
                self._matrix.remove_value_listener(self._matrix_value_quickscale)
        self._matrix = matrix
        if self._matrix != None:
            self._matrix.add_value_listener(self._matrix_value_quickscale)
        self._update_matrix()

    # Listener, setup drumrack scale mode and load the selected scale for Track/Cip (Disabled)
    def on_selected_track_changed(self):
        if self._track_controller._implicit_arm:
            self._get_drumrack_device()
            if self._drum_group_device != None:
                self._scales.set_drumrack(True)
            else:
                self._scales.set_drumrack(False)

            self._note_repeat.set_enabled(False)
            self.update()

    def on_selected_scene_changed(self):
        if self._track_controller._implicit_arm:
            self.update()

    def _followed_scale(self):
        return self._scales

    # Set the drum rack instrument to _drum_group_device variable, if it exists
    def _get_drumrack_device(self):
        self._drum_group_device = drum_rack_of(self._track_controller.selected_track)

    def _update_matrix(self):
        if not self.is_enabled() or not self._matrix or self._scales.is_enabled():
            self._control_surface.release_controlled_track()
            return
        non_feedback_channel = self.base_channel + 4
        self._get_drumrack_device()
        scales = self._scales
        scales.set_drumrack(scales.is_drumrack and not scales.is_diatonic and not scales.is_chromatic)
        for button, _ in self._matrix.iterbuttons():
            button.use_default_message()
            button.set_channel(non_feedback_channel)
        if scales.is_drumrack:
            self._paint_drum_pads(non_feedback_channel)
        else:
            if scales.is_quick_scale:
                self._paint_quick_scale_page()
            self._paint_note_pads(non_feedback_channel)
        for button in self._side_buttons:
            button.use_default_message()
            button.set_channel(non_feedback_channel)
            button.set_enabled(True)
            button.force_next_send()
