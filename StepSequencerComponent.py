import Live
from _Framework.ButtonElement import ButtonElement
from _Framework.CompoundComponent import CompoundComponent

from .ClipNotes import read_all_notes
from .DrumRack import drum_rack_of
from .LoopSelectorComponent import LoopSelectorComponent
from .NoteEditorComponent import NoteEditorComponent
from .NoteSelectorComponent import NoteSelectorComponent
from .PressButton import PressButton, ignore
from .ScaleComponent import KEY_NAMES, MUSICAL_MODES, ScaleComponent
from .Settings import Settings
from .SongScaleListener import SongScaleListener
from .TrackControllerComponent import TrackControllerComponent

# quantization button colours. this must remain of length 4.
QUANTIZATION_MAP = [1, 0.5, 0.25, 0.125]  # 1/4 1/8 1/16 1/32
QUANTIZATION_NAMES = ["1/4", "1/8", "1/16", "1/32"]

STEPSEQ_MODE_NORMAL = 1
STEPSEQ_MODE_MULTINOTE = 2
STEPSEQ_MODE_SCALE_EDIT = 10

LONG_BUTTON_PRESS = 1.0
# Side buttons: a release this long after the press is a long press; two releases closer
# than MUTE_LATCH latch the mute shift.
MODE_LONG_PRESS = 0.25
QUANTIZE_LONG_PRESS = 0.5
LOCK_LONG_PRESS = 0.5
MUTE_LATCH = 0.25

# Scrolls the regions in Multinote Mode


class StepSequencerComponent(SongScaleListener, CompoundComponent):

    def __init__(self, matrix, side_buttons, top_buttons, control_surface):
        self._osd = None
        super().__init__()
        self._control_surface = control_surface
        self._number_of_lines_per_note = 1
        self.QUANTIZATION_COLOR_MAP = [
            "StepSequencer.Quantization.One",
            "StepSequencer.Quantization.Two",
            "StepSequencer.Quantization.Three",
            "StepSequencer.Quantization.Four",
        ]
        self.QUANTIZATION_COLOR_MAP_LOW = [
            "StepSequencer.QuantizationLow.One",
            "StepSequencer.QuantizationLow.Two",
            "StepSequencer.QuantizationLow.Three",
            "StepSequencer.QuantizationLow.Four",
        ]
        self._name = "drum step sequencer"
        # clip
        self._clip = None
        self._clip_slot = None
        self._note_cache = []
        self._playhead = 0
        # mode
        self._mode = -1
        self._mode_backup = self._mode
        # buttons
        self._height = matrix.height()
        self._width = matrix.width()
        self._matrix = matrix
        self._top_buttons = top_buttons
        self._side_buttons = side_buttons
        self._left_button = None
        self._right_button = None
        self._mode_button = None
        self._lock_button = None
        self._mute_shift_button = None
        self._quantization_button = None
        # scale
        self._root_note = 36
        self._chromatic_scale = []
        self._diatonic_scale = []

        self._beat = 0
        # setup
        self._set_loop_selector()
        self._set_note_editor()
        self._set_note_selector()
        self._set_track_controller()
        self._set_scale_selector()
        self._set_quantization_function()
        self._set_mute_shift_function()
        self._set_lock_function()
        self._set_mode_function()
        self._scale_updated()
        # TODO: maybe clean this... this should be done on enable.
        # self.on_clip_slot_changed()

    def disconnect(self):
        self._remove_scale_listeners()
        if self._clip_slot != None and self._clip_slot.has_clip_has_listener(self.on_clip_slot_has_clip_changed):
            self._clip_slot.remove_has_clip_listener(self.on_clip_slot_has_clip_changed)
        self._clip_slot = None
        self._remove_clip_listeners(self._clip)
        self._clip = None

        for press_button in (self._mode_button, self._lock_button, self._mute_shift_button, self._quantization_button):
            if press_button is not None:
                press_button.set_button(None)
        self._mode_button = self._lock_button = self._mute_shift_button = self._quantization_button = None
        self._top_buttons = None
        self._side_buttons = None
        self._matrix = None

        self._loop_selector = None
        self._note_editor = None
        self._note_selector = None
        self._scale_selector = None
        self._track_controller = None
        super().disconnect()

    def _remove_clip_listeners(self, clip):
        if clip != None and clip.is_midi_clip:
            if clip.notes_has_listener(self._on_notes_changed):
                clip.remove_notes_listener(self._on_notes_changed)
            if clip.playing_status_has_listener(self._on_playing_status_changed):
                clip.remove_playing_status_listener(self._on_playing_status_changed)
            if clip.playing_position_has_listener(self._on_playing_position_changed):
                clip.remove_playing_position_listener(self._on_playing_position_changed)
            if clip.loop_start_has_listener(self._on_loop_changed):
                clip.remove_loop_start_listener(self._on_loop_changed)
            if clip.loop_end_has_listener(self._on_loop_changed):
                clip.remove_loop_end_listener(self._on_loop_changed)

    # SET FUNCTIONS
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

    # Set 4x4 lower right matrix section that manages the loop range OK
    def _set_loop_selector(self):
        self._loop_selector = self.register_component(
            LoopSelectorComponent(
                self,
                [
                    self._matrix.get_button(4, 4),
                    self._matrix.get_button(5, 4),
                    self._matrix.get_button(6, 4),
                    self._matrix.get_button(7, 4),
                    self._matrix.get_button(4, 5),
                    self._matrix.get_button(5, 5),
                    self._matrix.get_button(6, 5),
                    self._matrix.get_button(7, 5),
                    self._matrix.get_button(4, 6),
                    self._matrix.get_button(5, 6),
                    self._matrix.get_button(6, 6),
                    self._matrix.get_button(7, 6),
                    self._matrix.get_button(4, 7),
                    self._matrix.get_button(5, 7),
                    self._matrix.get_button(6, 7),
                    self._matrix.get_button(7, 7),
                ],
                self._control_surface,
            )
        )

    # Allow to manipulate the LP grid and Live's Clip notes (add/del, velocity, mute, etc)
    # In charge of refreshing the notes LED matrix
    # Display page indicator for multinote mode
    def _set_note_editor(self):
        self._note_editor = self.register_component(NoteEditorComponent(self, self._matrix, self._control_surface))
        self._note_editor.set_velocity_button(self._side_buttons[6])  # Solo

    # Set 4x4 lower left matrix section that allows note selection in Normal Mode
    def _set_note_selector(self):
        self._note_selector = self.register_component(
            NoteSelectorComponent(
                self,
                [
                    self._matrix.get_button(0, 7),
                    self._matrix.get_button(1, 7),
                    self._matrix.get_button(2, 7),
                    self._matrix.get_button(3, 7),
                    self._matrix.get_button(0, 6),
                    self._matrix.get_button(1, 6),
                    self._matrix.get_button(2, 6),
                    self._matrix.get_button(3, 6),
                    self._matrix.get_button(0, 5),
                    self._matrix.get_button(1, 5),
                    self._matrix.get_button(2, 5),
                    self._matrix.get_button(3, 5),
                    self._matrix.get_button(0, 4),
                    self._matrix.get_button(1, 4),
                    self._matrix.get_button(2, 4),
                    self._matrix.get_button(3, 4),
                ],
                self._control_surface,
            )
        )
        self._note_selector.set_up_button(self._side_buttons[4])  # Stop
        self._note_selector.set_down_button(self._side_buttons[5])  # Trk On

    def _set_track_controller(self):  # Navigation buttons
        self._track_controller = self.register_component(
            TrackControllerComponent(self._control_surface, implicit_arm=False)
        )
        self._track_controller.set_enabled(False)
        self._track_controller.set_prev_scene_button(self._top_buttons[0])
        self._track_controller.set_next_scene_button(self._top_buttons[1])
        self._track_controller.set_prev_track_button(self._top_buttons[2])
        self._track_controller.set_next_track_button(self._top_buttons[3])

    def _set_scale_selector(self):
        self._scale_selector = self.register_component(ScaleComponent(self._control_surface))
        self._scale_selector.set_osd(self._osd)
        self._scale_selector.set_enabled(False)
        self._scale_selector.set_matrix(self._matrix)
        self._scale_selector._mode = "chromatic"
        self._scale_selector._drumrack = False
        self._scale_selector_button = None
        self.set_scale_selector_button(self._side_buttons[0])

    def set_osd(self, osd):
        self._osd = osd
        self._scale_selector.set_osd(osd)

    def _osd_mode(self):
        if self._mode == STEPSEQ_MODE_MULTINOTE:
            return "Drum Step Sequencer (multinote)"
        return "Drum Step Sequencer"

    def _osd_extra_attributes(self):
        """(name, value) pairs shown after Scale, Root Note, Octave and Quantisation."""
        return ()

    def _followed_scale(self):
        return self._scale_selector

    def _update_OSD(self):
        if self._osd == None:
            return
        self._osd.set_mode(self._osd_mode())
        attributes = []
        if self._clip != None:
            scale = self._scale_selector
            attributes = [
                ("Scale", MUSICAL_MODES[scale._modus * 2]),
                ("Root Note", KEY_NAMES[scale._key % 12]),
                ("Octave", scale._octave),
                ("Quantisation", QUANTIZATION_NAMES[self._quantization_index]),
                *self._osd_extra_attributes(),
            ]
        for index in range(8):
            name, value = attributes[index] if index < len(attributes) else (" ", " ")
            self._osd.attribute_names[index] = name
            self._osd.attributes[index] = value
        self._osd.info[0] = self._osd_track_line()
        self._osd.info[1] = self._osd_clip_line()
        self._osd.update()

    def _osd_track_line(self):
        if self._selected_track == None:
            return " "
        locked = " (locked)" if self._lock_to_track and self._is_locked else ""
        return "track : " + self._selected_track.name + locked

    def _osd_clip_line(self):
        if self._clip == None:
            return "no clip selected"
        name = self._clip.name or "(unamed clip)"
        locked = " (locked)" if not self._lock_to_track and self._is_locked else ""
        return "clip : " + name + locked

    @property
    def _is_velocity_shifted(self):
        return self._note_editor._is_velocity_shifted

    def index_of(self, pad_list, pad):
        for i in range(0, len(pad_list)):
            if pad_list[i] == pad:
                return i
        return -1

    # enabled
    def set_enabled(self, enabled):
        if enabled:
            if self._mode == STEPSEQ_MODE_SCALE_EDIT:
                self.set_mode(self._mode_backup)
            # clear note editor cache
            self._note_editor._force_update = True

            # todo: find a better way to init?
            if self._mode == -1:
                self._mode = STEPSEQ_MODE_NORMAL
                self._detect_scale_mode()

            # sync to selected pad
            self._update_drum_group_device()
            if self._drum_group_device:  # Select the note
                self._note_selector.set_selected_note(
                    self.index_of(self._drum_group_device.drum_pads, self._drum_group_device.view.selected_drum_pad)
                )  # FIX set view again

            self._track_controller.set_enabled(enabled)
            self._note_editor.set_enabled(enabled)
            # update clip notes as they might have changed while we were sleeping
            self.on_clip_slot_changed()
            # call super.set_enabled()
            CompoundComponent.set_enabled(self, enabled)
            if self._clip != None and self._is_locked:
                self._control_surface.show_message("stepseq : clip '" + str(self._clip.name) + "'")
            self._on_notes_changed()
            self._update_OSD()

        else:
            self._track_controller.set_enabled(enabled)
            self._loop_selector.set_enabled(enabled)
            self._note_selector.set_enabled(enabled)
            self._note_editor.set_enabled(enabled)
            CompoundComponent.set_enabled(self, enabled)
        if not enabled:
            self._remove_scale_listeners()
        else:
            self._register_scale_listeners()

    def set_mode(self, mode, number_of_lines_per_note=1):
        if self._mode != mode or number_of_lines_per_note != self._number_of_lines_per_note:
            self._number_of_lines_per_note = number_of_lines_per_note
            self._note_editor.set_multinote(mode == STEPSEQ_MODE_MULTINOTE, number_of_lines_per_note)
            if mode == STEPSEQ_MODE_NORMAL:
                if self._mode != mode:
                    # self._loop_selector._block = self._loop_selector._block * self._number_of_lines_per_note
                    self._note_editor.set_page(self._loop_selector._block)
                self.set_left_button(None)
                self.set_right_button(None)
                self._track_controller.set_prev_track_button(self._top_buttons[2])
                self._track_controller.set_next_track_button(self._top_buttons[3])
            else:
                if self._mode != mode:
                    # self._loop_selector._block = self._loop_selector._block / self._number_of_lines_per_note
                    self._note_editor.set_page(self._loop_selector._block)
                self._track_controller.set_prev_track_button(None)
                self._track_controller.set_next_track_button(None)
                self.set_left_button(self._top_buttons[2])
                self.set_right_button(self._top_buttons[3])
            self._mode = mode
            self._note_editor._force_update = True
            self.update()

    def set_page(self, block):
        self._note_editor.set_page(block)
        self._note_editor.update()

    # SCALE
    def _scale_updated(self):
        keys = [0, 0, 0, 0, 0, 0, 0, 0]
        key_is_root_note = [False, False, False, False, False, False, False, False]
        key_is_in_scale = [False, False, False, False, False, False, False, False]
        if self._note_selector.is_drumrack:
            for i in range(8):
                keys[i] = self._note_selector.selected_note + i
                key_is_root_note[i] = (keys[i] + 12 + 16) % 16 == 0
                key_is_in_scale[i] = (keys[i] + 12 + 16) % 4 == 0
        elif self._note_selector.is_diatonic:
            self._note_selector._scale_length = len(self._note_selector._scale)
            try:
                idx = self._note_selector._scale.index(self._note_selector._offset)
            except ValueError:
                idx = -1
            if idx == -1:
                self._control_surface.log_message(
                    "not found : " + str(self._note_selector._offset) + " in " + str(self._note_selector._scale)
                )
                for i in range(8):
                    keys[i] = self._note_selector._root_note + self._note_selector._offset + i
            else:
                for i in range(8):
                    keys[i] = (
                        self._note_selector._root_note
                        + self._note_selector._scale[(i + idx) % self._note_selector._scale_length]
                        + int((i + idx) / self._note_selector._scale_length) * 12
                    )
                    key_is_root_note[i] = (keys[i] + 12) % 12 == self._note_selector._key
                    key_is_in_scale[i] = True
        else:
            for i in range(8):
                keys[i] = self._note_selector.selected_note + i
                key_is_root_note[i] = (keys[i] + 12) % 12 == self._note_selector._key
                key_is_in_scale[i] = (keys[i] - self._note_selector._key + 12) % 12 in self._note_selector._scale

        self._note_editor.set_key_indexes(keys)
        self._note_editor.set_key_index_is_in_scale(key_is_in_scale)
        self._note_editor.set_key_index_is_root_note(key_is_root_note)
        self._update_note_editor()
        self._update_note_selector()

    # UPDATE
    def update(self):
        if self.is_enabled():
            self._update_track_controller()
            self._update_scale_selector()
            self._update_loop_selector()
            self._update_note_selector()
            self._update_buttons()
            self._update_note_editor()
            self._update_OSD()
            # show clip !
            if not self._is_locked and self._clip != None:
                if (not self.application().view.is_view_visible("Detail")) or (
                    not self.application().view.is_view_visible("Detail/Clip")
                ):
                    self.application().view.show_view("Detail")
                    self.application().view.show_view("Detail/Clip")

    def _update_track_controller(self):
        if self._track_controller != None:
            self._track_controller.set_enabled(True)

    def _update_scale_selector(self):
        self._scale_selector.set_enabled(self._mode == STEPSEQ_MODE_SCALE_EDIT)
        self._scale_selector.update()

    def _update_loop_selector(self):
        self._loop_selector.set_enabled(self._mode == STEPSEQ_MODE_NORMAL)
        self._loop_selector.update()

    def _update_note_selector(self):
        self._note_selector._enable_offset_button = self._mode == STEPSEQ_MODE_NORMAL
        self._note_selector.set_enabled(self._mode != STEPSEQ_MODE_SCALE_EDIT)
        self._note_selector.update()

    def _update_note_editor(self):
        self._note_editor.set_multinote(self._mode == STEPSEQ_MODE_MULTINOTE, self._number_of_lines_per_note)
        if self._mode == STEPSEQ_MODE_NORMAL:
            self._note_editor.set_height(self._height - 4)
        else:
            self._note_editor.set_height(self._height)
        self._note_editor.set_enabled(self._mode != STEPSEQ_MODE_SCALE_EDIT)
        self._note_editor.update()

    def _update_buttons(self):
        self._update_quantization_button()
        self._update_lock_button()
        self._update_mode_button()
        self._update_mute_shift_button()
        self._update_scale_selector_button()
        self._update_left_button()
        self._update_right_button()

    # CLIP CALLBACKS
    def on_track_list_changed(self):
        self.on_selected_track_changed()

    def on_scene_list_changed(self):
        self.on_selected_scene_changed()

    def on_selected_scene_changed(self):
        self.on_clip_slot_changed()
        self.update()

    def on_selected_track_changed(self):
        if not self._is_locked or self._clip == None:
            self._detect_scale_mode()
            self.on_clip_slot_changed()
            self.update()

    def _on_loop_changed(self):
        if self.is_enabled() and self._clip != None:
            self._loop_selector._get_clip_loop()

    def on_clip_slot_has_clip_changed(self):
        # the clip was deleted. unlock.
        if not self._clip_slot.has_clip:
            self._is_locked = False
        self.on_clip_slot_changed()
        self.update()

    def on_clip_slot_changed(self, scheduled=False):
        # get old reference to clipslot
        clip_slot = self._clip_slot

        # update track if not track locked
        if not self._is_locked or self._selected_track == None:
            self._selected_track = self.song().view.selected_track

        # update scene
        if self._selected_track != None:
            idx = -1
            if self._lock_to_track and self._is_locked:
                # track locked mode

                # schedule a refresh as scene fire happens after scene selection
                # so that we can catch the clip scheduled for playing
                if not scheduled:
                    self._control_surface.schedule_message(5, self.on_clip_slot_changed, (True))

                # locate with clip pending fire
                for i in range(len(self.song().scenes)):
                    if (
                        self._selected_track.clip_slots[i].has_clip
                        and self._selected_track.clip_slots[i].clip.is_triggered
                    ):
                        idx = i
                # no tirggered clip, locate with playing clip
                if idx == -1:
                    for i in range(len(self.song().scenes)):
                        if (
                            self._selected_track.clip_slots[i].has_clip
                            and self._selected_track.clip_slots[i].clip.is_playing
                        ):
                            idx = i
                # fallback: use scene selection
                if idx == -1:
                    try:
                        idx = list(self.song().scenes).index(self.song().view.selected_scene)
                    except ValueError:
                        idx = -1

            # unlocked mode
            if not self._is_locked:
                try:
                    idx = list(self.song().scenes).index(self.song().view.selected_scene)
                except ValueError:
                    idx = -1
            if idx != -1 and idx < len(list(self._selected_track.clip_slots)):
                clip_slot = self._selected_track.clip_slots[idx]

        # update clip slot
        if clip_slot != self._clip_slot or self._clip_slot == None:
            if self._clip_slot != None and self._clip_slot.has_clip_has_listener(self.on_clip_slot_has_clip_changed):
                self._clip_slot.remove_has_clip_listener(self.on_clip_slot_has_clip_changed)
            self._clip_slot = clip_slot
            if self._clip_slot != None:
                if self._clip_slot.has_clip_has_listener(self.on_clip_slot_has_clip_changed):
                    self._clip_slot.remove_has_clip_listener(self.on_clip_slot_has_clip_changed)
                self._clip_slot.add_has_clip_listener(self.on_clip_slot_has_clip_changed)

        if (
            self._clip_slot != None
            and self._clip_slot.has_clip
            and self._clip_slot.clip != None
            and self._clip_slot.clip.is_midi_clip
        ):
            if self._clip == None or self._clip != self._clip_slot.clip:
                # unlink
                self._remove_clip_listeners(self._clip)

                # link new clip
                self._clip_slot.clip.add_notes_listener(self._on_notes_changed)
                self._clip_slot.clip.add_playing_status_listener(self._on_playing_status_changed)
                self._clip_slot.clip.add_playing_position_listener(self._on_playing_position_changed)
                self._clip_slot.clip.add_loop_start_listener(self._on_loop_changed)
                self._clip_slot.clip.add_loop_end_listener(self._on_loop_changed)

                # publish
                self._clip = self._clip_slot.clip

                # update
                # if scheduled:
                self._clip_changed()
                # else:
                # self._control_surface.schedule_message(1, self._clip_changed)
            else:
                # same clip...
                pass

        else:
            # unlink
            self._remove_clip_listeners(self._clip)

            # publish
            self._clip = None
            self._clip_changed()

    def _clip_changed(self):  # triggered by _on_clip_slot_changed() or manually on enable.
        self._note_editor.set_clip(self._clip)
        self._note_selector.set_clip(self._clip)
        self._loop_selector.set_clip(self._clip)
        self._note_editor.set_playhead(None)
        self._note_selector.set_playhead(None)
        self._loop_selector.set_playhead(None)
        # reload notes (also when the new clip has the same notes, e.g. a duplicate)
        self._note_cache = None
        self._on_notes_changed()

    def _on_notes_changed(self):  # trigger by callback on clip or via _clip_changed.
        if self.is_enabled():
            # get notes
            if self._clip == None:
                note_cache = []
            else:
                note_cache = read_all_notes(self._clip)

            # update if needed
            if note_cache != self._note_cache:
                self._note_cache = note_cache
                self._note_editor.set_note_cache(self._note_cache)
                self._note_selector.set_note_cache(self._note_cache)
                self._loop_selector.set_note_cache(self._note_cache)
                self._note_editor.update()

    # PLAY POSITION
    def _on_playing_status_changed(self):  # playing status changed listener
        if self.is_enabled():
            self._on_playing_position_changed()

    def _on_playing_position_changed(self):  # playing position changed listener
        if self.is_enabled():
            if self._clip != None and self._clip.is_playing and self.song().is_playing:
                self._playhead = self._clip.playing_position
            else:
                self._playhead = None
            self._loop_selector.set_playhead(self._playhead, Settings.STEPSEQ__AUTO_SCROLL)
            self._note_selector.set_playhead(self._playhead)
            self._note_editor.set_playhead(self._playhead)
            self.updateQuantizationButton()

    # DRUM_GROUP_DEVICE
    def _update_drum_group_device(self):
        self._drum_group_device = drum_rack_of(self.song().view.selected_track)

    def _detect_scale_mode(self):
        if not self._is_locked:
            self._update_drum_group_device()
            self._scale_selector.set_drumrack(self._drum_group_device != None)

    # SCALE Selector Button
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

    # MUTE SHIFT Button
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

    # MODE
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

    # QUANTIZE
    def _update_quantization_button(self):
        if self._quantization_button is not None:
            self._quantization_button.update()

    def _paint_quantization_button(self, button):
        if self.is_enabled():
            if self._clip != None:
                button.set_light(self.QUANTIZATION_COLOR_MAP[self._quantization_index])
            else:
                button.set_light("DefaultButton.Disabled")

    # Long press duplicates the clip, a tap selects the next quantization
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

    # Refresh button and its listener OK
    # Handle button holded and quantization resolution selection OK
    def updateQuantizationButton(self):
        if self.is_enabled() and self._quantization_button.button != None and self._playhead != None:
            if self._beat == int(self._playhead):
                self._quantization_button.button.set_light(self.QUANTIZATION_COLOR_MAP_LOW[self._quantization_index])
            else:
                self._beat = int(self._playhead)
                self._update_quantization_button()

    def set_quantization(self, quantization):
        self._quantization = quantization
        if self._note_editor != None:
            self._note_editor.set_quantization(self._quantization)
        if self._loop_selector != None:
            self._update_loop_selector()
        if self._note_selector != None:
            self._update_note_selector()
        if self._note_editor != None:
            self._update_note_editor()
        self._update_OSD()

    # LOCK Button
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

    # Tap: lock to (or unlock from) the clip; long press: lock to the track instead
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

    # RIGHT Button
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

    # LEFT Button
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

    # UTILS
    def create_clip(self):
        if self.song().view.highlighted_clip_slot != None:
            clip_slot = self.song().view.highlighted_clip_slot
            if not clip_slot.has_clip:
                if self._mode == STEPSEQ_MODE_NORMAL:
                    clip_slot.create_clip(QUANTIZATION_MAP[self._quantization_index] * 8 * 4)
                else:
                    clip_slot.create_clip(QUANTIZATION_MAP[self._quantization_index] * 8)
                self._detect_scale_mode()
                clip_slot.fire()
                self.on_clip_slot_changed()
                self.update()

    def duplicate_clip(self):
        if self._clip_slot and self._clip_slot.has_clip:
            try:
                if not self._is_locked or self._lock_to_track:
                    track = self._clip_slot.canonical_parent
                    newIdx = track.duplicate_clip_slot(list(track.clip_slots).index(self._clip_slot))
                    self.song().view.selected_scene = self.song().scenes[newIdx]
                    # if track.clip_slots[newIdx] != None:
                    # track.clip_slots[newIdx].fire()
                    self.on_clip_slot_changed()
                    self.update()
            except Live.Base.LimitationError:
                pass
            except RuntimeError:
                pass
