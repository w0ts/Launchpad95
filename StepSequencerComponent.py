import Live
from _Framework.CompoundComponent import CompoundComponent

from .ClipNotes import read_all_notes
from .DrumRack import drum_rack_of
from .LoopSelectorComponent import LoopSelectorComponent
from .NoteEditorComponent import NoteEditorComponent
from .NoteSelectorComponent import NoteSelectorComponent
from .ScaleComponent import KEY_NAMES, MUSICAL_MODES, ScaleComponent
from .Settings import Settings
from .SongScaleListener import SongScaleListener
from .StepSequencerButtons import StepSequencerButtons
from .StepSequencerSettings import (
    QUANTIZATION_MAP,
    QUANTIZATION_NAMES,
    STEPSEQ_MODE_MULTINOTE,
    STEPSEQ_MODE_NORMAL,
    STEPSEQ_MODE_SCALE_EDIT,
)
from .TrackControllerComponent import TrackControllerComponent

LONG_BUTTON_PRESS = 1.0

# Scrolls the regions in Multinote Mode


class StepSequencerComponent(SongScaleListener, StepSequencerButtons, CompoundComponent):

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
        """Follow the clip slot the sequencer should edit (see _followed_clip_slot)."""
        if not self._is_locked or self._selected_track == None:
            self._selected_track = self.song().view.selected_track
        self._watch_clip_slot(self._followed_clip_slot(scheduled))
        slot = self._clip_slot
        if slot != None and slot.has_clip and slot.clip != None and slot.clip.is_midi_clip:
            if self._clip == None or self._clip != slot.clip:
                self._follow_clip(slot.clip)
        else:
            self._follow_clip(None)

    def _followed_clip_slot(self, scheduled):
        """Unlocked: the selected scene's slot. Locked to the clip: the same slot. Locked to
        the track: its triggered clip, else its playing clip, else the selected scene."""
        clip_slot = self._clip_slot
        track = self._selected_track
        if track == None:
            return clip_slot
        index = -1
        if self._lock_to_track and self._is_locked:
            if not scheduled:
                # scenes fire after they are selected: look again for the triggered clip
                self._control_surface.schedule_message(5, self.on_clip_slot_changed, True)
            index = self._track_clip_index(lambda clip: clip.is_triggered)
            if index == -1:
                index = self._track_clip_index(lambda clip: clip.is_playing)
            if index == -1:
                index = self._selected_scene_index()
        if not self._is_locked:
            index = self._selected_scene_index()
        if index != -1 and index < len(list(track.clip_slots)):
            clip_slot = track.clip_slots[index]
        return clip_slot

    def _track_clip_index(self, condition):
        """The last scene index whose clip on the selected track meets ``condition``, or -1."""
        index = -1
        slots = self._selected_track.clip_slots
        for i in range(len(self.song().scenes)):
            if slots[i].has_clip and condition(slots[i].clip):
                index = i
        return index

    def _selected_scene_index(self):
        try:
            return list(self.song().scenes).index(self.song().view.selected_scene)
        except ValueError:
            return -1

    def _watch_clip_slot(self, clip_slot):
        """Listen to the slot's has_clip (a deleted clip unlocks the sequencer)."""
        if clip_slot == self._clip_slot and self._clip_slot != None:
            return
        listener = self.on_clip_slot_has_clip_changed
        if self._clip_slot != None and self._clip_slot.has_clip_has_listener(listener):
            self._clip_slot.remove_has_clip_listener(listener)
        self._clip_slot = clip_slot
        if self._clip_slot != None:
            if self._clip_slot.has_clip_has_listener(listener):
                self._clip_slot.remove_has_clip_listener(listener)
            self._clip_slot.add_has_clip_listener(listener)

    def _follow_clip(self, clip):
        """Move the clip listeners to ``clip`` (or None) and reload it."""
        self._remove_clip_listeners(self._clip)
        if clip != None:
            clip.add_notes_listener(self._on_notes_changed)
            clip.add_playing_status_listener(self._on_playing_status_changed)
            clip.add_playing_position_listener(self._on_playing_position_changed)
            clip.add_loop_start_listener(self._on_loop_changed)
            clip.add_loop_end_listener(self._on_loop_changed)
        self._clip = clip
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
