"""Melodic step sequencer (user 2, second sub mode): the drum sequencer's clip handling
with the MelodicNoteEditorComponent grid."""

from .LoopSelectorComponent import LoopSelectorComponent
from .MelodicNoteEditorComponent import PAGE_NAMES, MelodicNoteEditorComponent
from .NoteSelectorComponent import NoteSelectorComponent
from .StepSequencerComponent import StepSequencerComponent
from .TrackControllerComponent import TrackControllerComponent


class StepSequencerComponent2(StepSequencerComponent):

    def __init__(self, matrix, side_buttons, top_buttons, control_surface):
        super().__init__(matrix, side_buttons, top_buttons, control_surface)
        self._name = "melodic step sequencer"

    def _set_scale_selector(self):
        super()._set_scale_selector()
        self._scale_selector._mode = "diatonic"
        self._scale_selector._drumrack = False

    def _set_track_controller(self):
        self._track_controller = self.register_component(
            TrackControllerComponent(self._control_surface, implicit_arm=False)
        )
        self._track_controller.set_prev_scene_button(self._top_buttons[0])
        self._track_controller.set_next_scene_button(self._top_buttons[1])
        self._track_controller.set_prev_track_button(self._top_buttons[2])
        self._track_controller.set_next_track_button(self._top_buttons[3])

    def _set_note_editor(self):
        self._note_editor = self.register_component(
            MelodicNoteEditorComponent(self, self._matrix, self._side_buttons, self._control_surface)
        )

    def _set_mute_shift_function(self):
        self._is_mute_shifted = False

    def _set_note_selector(self):
        self._note_selector = self.register_component(NoteSelectorComponent(self, [], self._control_surface))

    def _set_loop_selector(self):
        self._loop_selector = self.register_component(
            LoopSelectorComponent(
                self,
                [
                    self._matrix.get_button(0, 7),
                    self._matrix.get_button(1, 7),
                    self._matrix.get_button(2, 7),
                    self._matrix.get_button(3, 7),
                    self._matrix.get_button(4, 7),
                    self._matrix.get_button(5, 7),
                    self._matrix.get_button(6, 7),
                    self._matrix.get_button(7, 7),
                ],
                self._control_surface,
            )
        )
        self.set_left_button(self._top_buttons[2])
        self.set_right_button(self._top_buttons[3])

    def _update_buttons(self):
        self._update_quantization_button()
        self._update_lock_button()
        self._update_scale_selector_button()
        self._update_left_button()
        self._update_right_button()

    def _update_drum_group_device(self):
        # no drum rack mode for me. i am a melodic step seq.
        self._drum_group_device = None

    def _osd_mode(self):
        return "Melodic Step Sequencer"

    def _osd_extra_attributes(self):
        editor = self._note_editor
        page = PAGE_NAMES.get(editor._mode, " ")
        return (("Polyphony", "Mono" if editor._is_monophonic else "Poly"), ("Page", page))

    def _paint_mode_button(self, button):
        if self.is_enabled():
            # side button 3 is the melodic editor's random button
            button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")

    def _on_mode_release(self, press_button, now):
        pass
