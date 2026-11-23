import time

from _Framework.ButtonElement import ButtonElement
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

from .ClipNotes import read_all_notes, write_all_notes


class NoteEditorComponent(ControlSurfaceComponent):

    def __init__(self, stepsequencer=None, matrix=None, control_surface=None):
        ControlSurfaceComponent.__init__(self)
        self.set_enabled(False)
        self._stepsequencer = stepsequencer
        self._control_surface = control_surface
        self._clip = None
        self._note_cache = None
        self._playhead = None

        # playback step indicator
        self.display_metronome = True
        self.metronome_color = "StepSequencer.NoteEditor.Metronome"

        # playback page indicator
        self._current_page = -1

        # Velocity color map. this must remain of length 3. WHY???
        self.velocity_map = [20, 50, 80, 105, 127]
        self.velocity_color_map = [
            "StepSequencer.NoteEditor.Velocity0",
            "StepSequencer.NoteEditor.Velocity1",
            "StepSequencer.NoteEditor.Velocity2",
            "StepSequencer.NoteEditor.Velocity3",
            "StepSequencer.NoteEditor.Velocity4",
        ]

        # other colors
        self.muted_note_color = "StepSequencer.NoteEditor.Muted"
        self.playing_note_color = "StepSequencer.NoteEditor.Playing"

        # hold button for 500 ms
        self.long_button_press = 0.500

        # buttons
        self._matrix = None
        self._mute_shift_button = None
        self._velocity_button = None
        self._velocity_shift_button = None

        # displayed page
        self._page = 0
        self._display_page = False
        self._display_page_time = time.time()

        # notes
        self._key_indexes = [36, 37, 38, 39, 40, 41, 42, 43]
        self._key_index_is_in_scale = [True, False, True, True, False, True, False, True]
        self._key_index_is_root_note = [True, False, False, False, False, False, False, False]
        self._number_of_lines_per_note = 1

        # clip
        self._force_update = True

        # quantization
        self._quantization = 16

        # velocity
        self._velocity_index = 3
        self._velocity = self.velocity_map[self._velocity_index]
        self._is_velocity_shifted = False
        self._velocity_notes_pressed = 0
        self._velocity_last_press = time.time()

        # modes
        self._is_mute_shifted = False
        self._is_mutlinote = False

        # matrix
        if matrix != None:
            self.set_matrix(matrix)

    def disconnect(self):
        self._matrix = None
        self._velocity_button = None
        self._clip = None

    @property
    def is_multinote(self):
        return self._is_mutlinote

    def set_multinote(self, is_mutlinote, number_of_lines_per_note):
        self._is_mutlinote = is_mutlinote
        self._number_of_lines_per_note = number_of_lines_per_note

    @property
    def quantization(self):
        return self._quantization

    def set_quantization(self, quantization):
        self._quantization = quantization

    def set_scale(self, scale):
        self._scale = scale

    def set_diatonic(self, diatonic):
        self._diatonic = diatonic

    @property
    def key_indexes(self):
        return self._key_indexes

    def set_key_indexes(self, key_indexes):
        self._key_indexes = key_indexes

    def set_key_index_is_in_scale(self, key_index_is_in_scale):
        self._key_index_is_in_scale = key_index_is_in_scale

    def set_key_index_is_root_note(self, key_index_is_root_note):
        self._key_index_is_root_note = key_index_is_root_note

    @property
    def height(self):
        return self._height

    def set_height(self, height):
        self._height = height

    @property
    def width(self):
        return self._width

    @property
    def number_of_lines_per_note(self):
        if self.is_multinote:
            return self._number_of_lines_per_note
        else:
            return self.height

    def set_page(self, block):
        # block: a loop selector block of 8 steps; a page shows number_of_lines_per_note
        # blocks (multinote: 1 or 2 lines per note; normal mode: the 4 rows of the editor)
        self._page = block // self.number_of_lines_per_note

    def set_clip(self, clip):
        self._clip = clip

    def set_note_cache(self, note_cache):
        self._note_cache = note_cache

    def set_playhead(self, playhead):  # Playing cursor
        self._playhead = playhead
        self._update_matrix()

    def update(self, force=False):
        if self.is_enabled():
            if force:
                self._force_update = True
            self._update_velocity_button()
            self._update_matrix()

    # Display the third amber column to show the current page in multinote mode OK
    def _display_selected_page(self):  # OK
        for i in range(0, self._height):
            self._grid_back_buffer[self._page % self.width][i] = "StepSequencer.NoteEditor.PageMarker"

    # Displays 3 buttons for the root of the scale and 1 for the in scale notes
    def _display_note_markers(self):  # (out of scale notes buttons are dark) OK
        for i in range(0, int(self.height / self.number_of_lines_per_note)):
            if self._key_index_is_root_note[i]:
                for j in range(0, self.number_of_lines_per_note):
                    self._grid_back_buffer[0][
                        self.height - i * self.number_of_lines_per_note - j - 1
                    ] = "StepSequencer.NoteEditor.NoteMarker"
                    self._grid_back_buffer[1][
                        self.height - i * self.number_of_lines_per_note - j - 1
                    ] = "StepSequencer.NoteEditor.NoteMarker"
                    self._grid_back_buffer[2][
                        self.height - i * self.number_of_lines_per_note - j - 1
                    ] = "StepSequencer.NoteEditor.NoteMarker"
            elif self._key_index_is_in_scale[i]:
                for j in range(0, self.number_of_lines_per_note):
                    self._grid_back_buffer[0][
                        self.height - i * self.number_of_lines_per_note - j - 1
                    ] = "StepSequencer.NoteEditor.NoteMarker"

    # *********************MATRIX*********************

    # Add listener and initialize note buffers OK
    def set_matrix(self, matrix):
        if matrix != self._matrix:
            if self._matrix != None:
                self._matrix.remove_value_listener(self._matrix_value)
            self._matrix = matrix
            if self._matrix != None:
                self._matrix.add_value_listener(self._matrix_value)
                self._width = self._matrix.width()
                # self._height = self._matrix.height()
                self._grid_buffer = [
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ]
                self._grid_back_buffer = [
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ]

    # Updates the LP LEDs OK
    def _update_matrix(self):
        if not self.is_enabled() or self._matrix == None:
            return
        for x in range(self.width):
            for y in range(self.height):
                self._grid_back_buffer[x][y] = "DefaultButton.Disabled"
        if self._clip != None and self._note_cache != None:
            play = self._play_cell()
            self._draw_playhead_and_markers(play)
            for note in self._note_cache:
                self._draw_note(note, play)
            # Display the column to show the page for half a second
            if self._display_page:
                if time.time() - self._display_page_time > 0.5:
                    self._display_page = False
                self._display_selected_page()
        self._flush_grid()

    def _play_cell(self):
        """(page, row, x, y) of the playing step, all -1 when not playing."""
        if self._playhead == None:
            return -1, -1, -1, -1
        position = self._playhead  # in beats
        page = int(position / self.quantization / self.width / self.number_of_lines_per_note)
        row = int(position / self.quantization / self.width) % self.number_of_lines_per_note
        x = int(position / self.quantization) % self.width
        y = int(position / self.quantization / self.width) % self.height
        return page, row, x, y

    def _draw_playhead_and_markers(self, play):
        play_page, _, play_x, play_y = play
        if self.display_metronome and self._clip.is_playing and self.song().is_playing:
            self._grid_back_buffer[play_x][play_y] = "StepSequencer.NoteEditor.Metronome"
        if self._display_page:
            self._display_selected_page()
            if self._display_page_time + 0.25 < time.time():
                self._display_page = False
        if self.is_multinote:
            self._display_note_markers()
            if self._current_page != play_page:
                self._current_page = play_page
                self._display_current_page()

    def _note_row_base(self, pitch):
        """The top row of the note's lane (multinote), 0 for the selected note (one-note
        mode), or -1 when the note has no row."""
        try:
            index = self.key_indexes.index(pitch)
        except ValueError:
            index = -1
        if not self.is_multinote:
            return 0 if index == 0 else -1
        base = index * self.number_of_lines_per_note
        if base >= 0:
            base = (7 - base) - (self.number_of_lines_per_note - 1)
        return base if base >= 0 else -1

    def _note_cell(self, note):
        """(x, y, row offset, page) of a cached note on the grid, or None when it has no pad."""
        position = note[1]  # in beats, like the playhead
        page = int(position / self.quantization / self.width / self.number_of_lines_per_note)
        x = int(position / self.quantization) % self.width
        offset = int(position / self.quantization / self.width) % self.number_of_lines_per_note
        base = self._note_row_base(note[0])
        if base == -1 or base >= self.height:
            return None
        return x, base + offset, offset, page

    def _velocity_color(self, velocity):
        color = self.velocity_color_map[0]
        for index in range(len(self.velocity_map)):
            if velocity >= self.velocity_map[index]:
                color = self.velocity_color_map[index]
        return color

    def _draw_note(self, note, play):
        cell = self._note_cell(note)
        if cell is None:
            return
        x, y, offset, page = cell
        play_page, play_row, play_x, play_y = play
        muted = note[4]
        on_playhead = play_y == y and not self.is_multinote or self.is_multinote and offset == play_row
        if (
            not muted
            and page == play_page
            and play_x == x
            and on_playhead
            and self.song().is_playing
            and self._clip.is_playing
        ):
            # highlight playing notes, even if they are from other pages
            self._grid_back_buffer[x][y] = self.playing_note_color
        elif page == self._page and self._grid_back_buffer[x][y] != self.playing_note_color:
            self._grid_back_buffer[x][y] = self.muted_note_color if muted else self._velocity_color(note[3])

    def _flush_grid(self):
        """Send only the pads that changed (all of them after a forced update)."""
        for x in range(self.width):
            for y in range(self.height):
                if self._grid_back_buffer[x][y] != self._grid_buffer[x][y] or self._force_update:
                    self._grid_buffer[x][y] = self._grid_back_buffer[x][y]
                    self._matrix.get_button(x, y).set_light(self._grid_buffer[x][y])
        self._force_update = False

    def request_display_page(self):  # Reset page column display timer
        self._display_page = True
        self._display_page_time = time.time()

    # matrix buttons listener OK
    def _matrix_value(self, value, x, y, is_momentary):
        if (
            self.is_enabled() and y < self.height
        ):  # Height value can be 8 (MULTINOTE/SCALE_EDIT) or 4 (STEPSEQ_MODE_NORMAL)
            if (value != 0) or (not is_momentary):  # if NOTE_ON or button is toggle
                self._stepsequencer._was_velocity_shifted = False  # Some previous state logic INVESTIGATE
                self._matrix_value_message([value, x, y, is_momentary])

    # Add/Delete/Mute notes in the cache for PL light management and in the Live's Clip OK
    def _matrix_value_message(self, values):  # (value=127/0, x=idx, y=idx, is_momentary=True)
        value = values[0]
        x = values[1]
        y = values[2]
        is_momentary = values[3]
        """(pitch, time, duration, velocity, mute state)"""
        assert self._matrix != None
        assert value in range(128)
        assert x in range(self._matrix.width())
        assert y in range(self._matrix.height())
        assert isinstance(is_momentary, bool)

        if self.is_enabled() and self._clip == None:
            self._stepsequencer.create_clip()

        elif self.is_enabled() and self._clip != None:
            if value != 0 or not is_momentary:  # if NOTE_ON or button is toggle
                if self._is_velocity_shifted:
                    self._velocity_notes_pressed = self._velocity_notes_pressed + 1  # Just changing some note velocity

                # note data

                if self.is_multinote:  # Calculate note pitch and time for notes
                    time = self.quantization * (
                        self._page * self.width * self.number_of_lines_per_note
                        + x
                        + (y % self.number_of_lines_per_note * self.width)
                    )
                    pitch = self._key_indexes[
                        8 // self.number_of_lines_per_note - 1 - y // self.number_of_lines_per_note
                    ]
                else:
                    time = self.quantization * (
                        self._page * self.width * self.number_of_lines_per_note + y * self.width + x
                    )
                    pitch = self._key_indexes[0]
                velocity = self._velocity  # setted by velocity button
                duration = self.quantization  # setted by quantization button in StepSequencerComponent

                note_cache = read_all_notes(self._clip)
                if self._note_cache != note_cache:
                    self._note_cache = note_cache

                note_cache = list(self._note_cache)
                for note in note_cache:
                    if pitch == note[0] and time == note[1]:
                        if self._is_velocity_shifted:
                            # update velocity of the note
                            new_velocity_index = 0
                            for index in range(len(self.velocity_map)):
                                if note[3] >= self.velocity_map[index]:
                                    new_velocity_index = (index + 1) % len(self.velocity_map)
                            note_cache.remove(note)
                            note_cache.append(
                                [note[0], note[1], note[2], self.velocity_map[new_velocity_index], note[4]]
                            )  # (pitch, time, duration, velocity, mute state)
                        elif not self._is_mute_shifted:
                            note_cache.remove(note)
                        else:
                            # mute / un mute note.
                            note_cache.remove(note)
                            note_cache.append(
                                [note[0], note[1], note[2], note[3], not note[4]]
                            )  # (pitch, time, duration, velocity, mute state)
                        break
                else:
                    note_cache.append(
                        [pitch, time, duration, velocity, self._is_mute_shifted]
                    )  # (pitch, time, duration, velocity, mute state)
                write_all_notes(self._clip, note_cache)

                note_cache = read_all_notes(self._clip)
                if self._note_cache != note_cache:
                    self._note_cache = note_cache

    # *********************VELOCITY/BTN_SHIFT*********************

    # Updates the velocity button light OK
    def _update_velocity_button(self):
        if self.is_enabled() and self._velocity_button != None:
            if self._clip != None:
                if self._is_velocity_shifted:
                    self._velocity_button.set_on_off_values("StepSequencer.NoteEditor.VelocityShifted")
                    self._velocity_button.turn_on()
                else:
                    self._velocity_button.set_light("StepSequencer.NoteEditor.Velocity" + str(self._velocity_index))
            else:
                self._velocity_button.set_light("DefaultButton.Disabled")

    # Refresh button and its listener OK
    def set_velocity_button(self, button):
        assert isinstance(button, (ButtonElement, type(None)))
        if button != self._velocity_button:
            if self._velocity_button != None:
                self._velocity_button.remove_value_listener(self._velocity_value)
            self._velocity_button = button
            if self._velocity_button != None:
                self._velocity_button.add_value_listener(self._velocity_value, identify_sender=True)

    # Handle button shifted and velocity selection OK
    def _velocity_value(self, value, sender):
        assert self._velocity_button != None
        assert value in range(128)
        if self.is_enabled():
            if (value == 0) or (not sender.is_momentary()):
                # button released, check if was used to modify notes or just to cycle thru velocity values
                if (
                    self._velocity_notes_pressed == 0
                    and time.time() - self._velocity_last_press < self.long_button_press
                ):
                    # cycle thru velocities
                    self._velocity_index = (len(self.velocity_map) + self._velocity_index + 1) % len(self.velocity_map)
                    self._velocity = self.velocity_map[self._velocity_index]
                self._stepsequencer._track_controller._implicit_arm = False
                if self._is_velocity_shifted:
                    self._stepsequencer._track_controller._do_implicit_arm(False)
                self._is_velocity_shifted = False
                self._update_velocity_button()
            if (value != 0) or (not sender.is_momentary()):
                # button pressed
                self._velocity_notes_pressed = 0
                self._is_velocity_shifted = True
                # While velocity is pressed, can play sounds using notes region
                self._stepsequencer._track_controller._implicit_arm = True  # Arm the track to force play MIDI notes
                self._stepsequencer._track_controller._do_implicit_arm(True)
                self._velocity_last_press = time.time()
                self._update_velocity_button()
            self._stepsequencer._note_selector.update()

    # *********************MUTE/BTN_SHIFT*********************

    # Mute all entries for a given MIDI note OK
    def mute_lane(self, pitch_to_mute):
        if self.is_enabled() and self._clip != None:
            note_cache = read_all_notes(self._clip)
            if self._note_cache != note_cache:
                self._note_cache = note_cache
            note_cache = list(self._note_cache)
            notes_changed = 0
            for note in self._note_cache:
                if note[0] == pitch_to_mute:
                    notes_changed = notes_changed + 1
                    note_to_mute = note
                    note_cache.remove(note)
                    note_cache.append(
                        [note_to_mute[0], note_to_mute[1], note_to_mute[2], note_to_mute[3], not note_to_mute[4]]
                    )
            if notes_changed > 0:
                write_all_notes(self._clip, note_cache)
            self.update()

    # Display the third red column to show the current page in multinote mode each time that the metronome goes to new pageOK
    def _display_current_page(self):  # OK
        for i in range(0, self._height):
            if self._page == self._current_page:
                self._grid_back_buffer[self._current_page % self.width][
                    i
                ] = "StepSequencer.NoteEditor.CurrentPageMarkerPlay"
            else:
                self._grid_back_buffer[self._current_page % self.width][
                    i
                ] = "StepSequencer.NoteEditor.CurrentPageMarker"
