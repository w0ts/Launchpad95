"""Melodic step sequencer grid: one column per step, rows 0-6 the scale degrees (or the
octave, velocity or length of each step on the other pages)."""

from random import randrange

from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

from .ClipNotes import write_all_notes
from .PressButton import PressButton, ignore

STEPSEQ_MODE_NOTES = 1
STEPSEQ_MODE_NOTES_OCTAVES = 2
STEPSEQ_MODE_NOTES_VELOCITIES = 3
STEPSEQ_MODE_NOTES_LENGTHS = 4
PAGE_NAMES = {
    STEPSEQ_MODE_NOTES: "Notes",
    STEPSEQ_MODE_NOTES_OCTAVES: "Octave",
    STEPSEQ_MODE_NOTES_VELOCITIES: "Velocity",
    STEPSEQ_MODE_NOTES_LENGTHS: "Length",
}

# Value pages: the list each edits, its skin, and whether a value lights a bar (velocity,
# length) or a single pad (octave).
VALUE_PAGES = {
    STEPSEQ_MODE_NOTES_OCTAVES: ("_notes_octaves", "StepSequencer2.Octave", False),
    STEPSEQ_MODE_NOTES_VELOCITIES: ("_notes_velocities", "StepSequencer2.Velocity", True),
    STEPSEQ_MODE_NOTES_LENGTHS: ("_notes_lengths", "StepSequencer2.Length", True),
}
TOP_VALUE = 6  # values 0-6, one per row (row 0 = 6)

LONG_BUTTON_PRESS = 1.0
# Two releases of the pitch button closer than this toggle mono/poly.
MONO_DOUBLE_TAP = 0.5

LANES = 7  # scale degrees shown, one per row
OCTAVES = 7  # octave index 0..6 = octave offset -2..+4
MIN_STEPS = 128  # the step lists grow past this when the clip needs more

# TODO :
# extend / clear region (possible via drum step seq for now)
# not even clip lengths (using shift notes ?)
# store scale settings per clip or track ?
# display current scale mode in osd


class MelodicNoteEditorComponent(ControlSurfaceComponent):

    def __init__(self, step_sequencer, matrix, side_buttons, control_surface):
        ControlSurfaceComponent.__init__(self)
        self._control_surface = control_surface
        self.set_enabled(False)

        self._step_sequencer = step_sequencer

        self._clip = None
        self._playhead = None

        self._matrix = matrix
        self._side_buttons = side_buttons

        # buttons
        self._matrix = None

        # matrix
        self.set_matrix(matrix)
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

        # clip
        self._clip = None
        self._note_cache = []
        self._force_update = True
        self._init_data()

        self._velocity_map = [0, 30, 60, 80, 100, 115, 127]
        self._length_map = [1, 2, 3, 4, 8, 16, 32]

        # time
        self._playhead = 0
        self._page = 0

        # notes
        self._key_indexes = [36, 37, 38, 39, 40, 41, 42, 43]
        self._key_index_is_in_scale = [True, False, True, True, False, True, False, True]
        self._key_index_is_root_note = [True, False, False, False, False, False, False, False]
        self._is_monophonic = False

        # quantization
        self._quantization = 16

        # MODE
        self._mode = STEPSEQ_MODE_NOTES

        # side buttons: 3 random; 4-7 pages (held: edit every step of the loop at once)
        self._is_velocity_shifted = False
        self._is_mute_shifted = False
        self._random_button = self._side_button(
            3, self._on_random_press, self._on_random_release, self._paint_random_button
        )
        self._lengths_button = self._page_button(4, STEPSEQ_MODE_NOTES_LENGTHS, "StepSequencer2.Length", "length")
        self._octaves_button = self._page_button(5, STEPSEQ_MODE_NOTES_OCTAVES, "StepSequencer2.Octave", "octave")
        self._velocities_button = self._page_button(
            6,
            STEPSEQ_MODE_NOTES_VELOCITIES,
            "StepSequencer2.Velocity",
            "velocity",
            on_press=self._on_velocities_press,
            refresh=self._on_velocities_changed,
        )
        self._pitches_button = self._page_button(
            7, STEPSEQ_MODE_NOTES, "StepSequencer2.Pitch", "pitch", on_press=self._on_pitches_press
        )

    def disconnect(self):
        self._step_sequencer = None
        self._matrix = None
        for press_button in self._side_press_buttons():
            press_button.set_button(None)
        self._notes_pitches = None
        self._notes_velocities = None
        self._notes_octaves = None
        self._notes_lengths = None
        self._clip = None

    # The song's root note and scale are followed by the step sequencer (SongScaleListener).

    def _init_data(self):
        self._notes_pitches = [0] * (LANES * MIN_STEPS)
        self._notes_velocities = [4] * MIN_STEPS
        self._notes_octaves = [2] * MIN_STEPS
        self._notes_lengths = [3] * MIN_STEPS
        # Notes of the clip that light a pad, by step; notes the grid cannot show (muted,
        # extra notes in mono mode, before time 0, off the scale lanes or octaves) are kept untouched.
        self._shown_notes = {}
        self._kept_notes = []
        # What the grid gave, by step, when the clip was last read or written: a step whose
        # grid notes did not change keeps the clip's own notes.
        self._grid_steps = {}

    def _ensure_steps(self, count):
        """Grow the per-step lists so that steps 0..count-1 exist."""
        missing = count - len(self._notes_velocities)
        if missing > 0:
            self._notes_pitches.extend([0] * (LANES * missing))
            self._notes_velocities.extend([4] * missing)
            self._notes_octaves.extend([2] * missing)
            self._notes_lengths.extend([3] * missing)

    def set_mode(self, mode):
        self._mode = mode
        self._force_update = True
        self.update()

    def set_clip(self, clip):
        if self._clip != clip:
            self._init_data()
            self._clip = clip
            # a new clip with the same notes (a duplicate) must still be parsed
            self._note_cache = None

    def set_note_cache(self, note_cache):
        if self._note_cache != note_cache:
            self._note_cache = note_cache
            self._parse_notes()

    def set_playhead(self, playhead):
        self._playhead = playhead
        self._update_matrix()

    def set_multinote(self, x=0, y=0):
        pass

    @property
    def quantization(self):
        return self._quantization

    def set_quantization(self, quantization):
        old_quantize = self._quantization
        self._quantization = quantization
        # update loop point
        if self._clip != None and old_quantize != self._quantization:
            self._loop_start = self._clip.loop_start * self._quantization / old_quantize
            self._loop_end = self._clip.loop_end * self._quantization / old_quantize
            if self._loop_start >= self._clip.loop_end:
                self._clip.loop_end = self._loop_end
                self._clip.loop_start = self._loop_start
                self._clip.end_marker = self._loop_end
                self._clip.start_marker = self._loop_start
            else:
                self._clip.loop_start = self._loop_start
                self._clip.loop_end = self._loop_end
                self._clip.start_marker = self._loop_start
                self._clip.end_marker = self._loop_end
        # update clip notes
        self._update_clip_notes()

    def set_diatonic(self, diatonic):
        self._diatonic = diatonic

    def set_key_indexes(self, key_indexes):
        if self._key_indexes != key_indexes:
            self._key_indexes = key_indexes
            self._update_clip_notes()

    def set_key_index_is_in_scale(self, key_index_is_in_scale):
        self._key_index_is_in_scale = key_index_is_in_scale

    def set_key_index_is_root_note(self, key_index_is_root_note):
        self._key_index_is_root_note = key_index_is_root_note

    def set_page(self, page):
        self._page = page
        self._ensure_steps((page + 1) * 8)

    def _step_of(self, time):
        """The step a note time falls in, or None before time 0."""
        if time < 0:
            return None
        return int(time // self._quantization)

    def _lane_of(self, pitch, octave):
        """The lane (scale degree row) showing pitch in the given octave index, or None."""
        for lane in range(min(LANES, len(self._key_indexes))):
            if pitch == self._key_indexes[lane] + 12 * (octave - 2):
                return lane
        return None

    def _lane_and_octave_of(self, pitch):
        for lane in range(min(LANES, len(self._key_indexes))):
            for octave in range(OCTAVES):
                if pitch == self._key_indexes[lane] + 12 * (octave - 2):
                    return lane, octave
        return None

    def _set_step_from_note(self, step, note):
        """The first note of a step sets the step's velocity and length."""
        velocity, length = note[3], note[2]
        for x in range(7):
            if velocity >= self._velocity_map[x]:
                self._notes_velocities[step] = x
        for x in range(7):
            if length * 4 >= self._length_map[x] * self._quantization:
                self._notes_lengths[step] = x

    def _parse_notes(self):
        notes = list(self._note_cache or ())
        steps = [self._step_of(note[1]) for note in notes]
        self._ensure_steps(max([s + 1 for s in steps if s is not None] + [0]))
        self._notes_pitches = [0] * len(self._notes_pitches)

        # the first unmuted note of a step that fits a lane sets the step's octave
        first = {}
        for index, note in enumerate(notes):
            step = steps[index]
            if step is None or note[4] or step in first:
                continue
            found = self._lane_and_octave_of(note[0])
            if found is not None:
                first[step] = index
                self._notes_octaves[step] = found[1]
                self._set_step_from_note(step, note)

        # a note is shown when it is on a lane in its step's octave; the others are kept
        shown = {}
        kept = []
        for index, note in enumerate(notes):
            step = steps[index]
            lane = None if step is None else self._lane_of(note[0], self._notes_octaves[step])
            if lane is None or note[4] or (self._is_monophonic and first.get(step) != index):
                kept.append(note)
                continue
            self._notes_pitches[step * LANES + lane] = 1
            shown.setdefault(step, []).append(note)
        self._shown_notes = shown
        self._kept_notes = kept
        self._grid_steps = self._notes_from_grid()
        self._update_matrix()

    def _notes_from_grid(self):
        """step -> the (pitch, time, length, velocity) notes the grid gives for that step."""
        steps = {}
        for x in range(len(self._notes_velocities)):
            for note_index in range(LANES):
                if self._notes_pitches[x * LANES + note_index] == 1:
                    time = x * self._quantization
                    velocity = self._velocity_map[self._notes_velocities[x]]
                    length = self._length_map[self._notes_lengths[x]] * self._quantization / 4.0
                    pitch = self._key_indexes[note_index] + 12 * (self._notes_octaves[x] - 2)
                    if pitch >= 0 and pitch < 128 and velocity >= 0 and velocity < 128 and length >= 0:
                        steps.setdefault(x, []).append((pitch, time, length, velocity))
        return steps

    def _update_clip_notes(self):
        """Write the grid to the clip. Only the steps the grid changed are rewritten: other
        steps keep the clip's notes as they are, and notes the grid cannot show are kept."""
        if self._clip != None and self._step_sequencer.is_enabled():
            grid = self._notes_from_grid()
            note_cache = list(self._kept_notes)
            shown = {}
            for step in sorted(set(grid) | set(self._shown_notes)):
                if grid.get(step) == self._grid_steps.get(step):
                    step_notes = self._shown_notes.get(step, [])
                else:
                    step_notes = [
                        (pitch, time, length, velocity, False) for (pitch, time, length, velocity) in grid.get(step, ())
                    ]
                if step_notes:
                    shown[step] = step_notes
                note_cache.extend(step_notes)
            # before writing: Live may call the notes listener (and parse) during the write
            self._shown_notes = shown
            self._grid_steps = grid
            write_all_notes(self._clip, note_cache)

    def update(self, force=False):
        if force:
            self._force_update = True
        if self.is_enabled():
            for press_button in self._side_press_buttons():
                press_button.update()
            self._update_matrix()

    def request_display_page(self):
        pass

    def set_height(self, height):
        pass

    # MATRIX

    def set_matrix(self, matrix):
        assert isinstance(matrix, (ButtonMatrixElement, type(None)))
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
        if matrix != self._matrix:
            if self._matrix != None:
                self._matrix.remove_value_listener(self._matrix_value)
            self._matrix = matrix
            if self._matrix != None:
                self._matrix.add_value_listener(self._matrix_value)

    def _update_matrix(self):  # step grid LEDs are updated here
        if not self.is_enabled() or self._matrix == None:
            return
        for x in range(8):
            for y in range(8):
                self._grid_back_buffer[x][y] = 0
        if self._clip != None:
            self._ensure_steps((self._page + 1) * 8)
            if self._playhead != None:
                self._ensure_steps(int(self._playhead / self.quantization) + 1)
            for x in range(8):
                self._draw_step(x)
            if self._playhead != None:
                self._draw_playhead()
        else:
            for x in range(8):
                for y in range(LANES):
                    self._grid_back_buffer[x][y] = "DefaultButton.Disabled"
        # send only the pads that changed (all of them after a forced update)
        for x in range(8):
            for y in range(LANES):
                if self._grid_back_buffer[x][y] != self._grid_buffer[x][y] or self._force_update:
                    self._grid_buffer[x][y] = self._grid_back_buffer[x][y]
                    self._matrix.get_button(x, y).set_light(self._grid_buffer[x][y])
        self._force_update = False

    def _pitch_index(self, step, y):
        """Index in _notes_pitches of the lane shown on row ``y`` (row 0 is the top lane)."""
        return step * LANES + TOP_VALUE - y

    def _step_has_note(self, step):
        return any(self._notes_pitches[self._pitch_index(step, y)] == 1 for y in range(LANES))

    def _draw_step(self, x):
        step = x + 8 * self._page
        if self._mode == STEPSEQ_MODE_NOTES:
            for y in range(LANES):
                lit = self._notes_pitches[self._pitch_index(step, y)] == 1
                self._grid_back_buffer[x][y] = "StepSequencer2.Pitch.On" if lit else "StepSequencer2.Pitch.Off"
            return
        page = VALUE_PAGES.get(self._mode)
        if page is None:
            return
        values, skin, bar = page
        value = getattr(self, values)[step]
        lit_skin = skin + (".On" if self._step_has_note(step) else ".Dim")
        for y in range(LANES):
            lit = value >= TOP_VALUE - y if bar else value == TOP_VALUE - y
            self._grid_back_buffer[x][y] = lit_skin if lit else skin + ".Off"

    def _draw_playhead(self):
        """The playing step: its bottom pad, and its notes on the pitch page."""
        step = int(self._playhead / self.quantization)
        x = int(self._playhead / self.quantization) % 8
        where = "InPage" if int(self._playhead / self.quantization / 8) == self._page else "InOtherPage"
        self._grid_back_buffer[x][6] = "StepSequencer2.NoteEditor.Metronome" + where
        if self._mode == STEPSEQ_MODE_NOTES:
            for y in range(LANES):
                if self._notes_pitches[self._pitch_index(step, y)] == 1:
                    self._grid_back_buffer[x][y] = "StepSequencer2.NoteEditor.Play" + where

    def _matrix_value(self, value, x, y, is_momentary):  # matrix buttons listener
        if not self.is_enabled() or self._matrix == None:
            return
        if self._clip == None:
            self._step_sequencer.create_clip()
            return
        start, end = self._edit_range()
        self._ensure_steps(max(end, (self._page + 1) * 8))
        if (value == 0 and is_momentary) or y >= LANES:
            return
        if self._mode == STEPSEQ_MODE_NOTES:
            self._edit_pitch(x, y, start, end)
        elif self._mode in VALUE_PAGES:
            values = getattr(self, VALUE_PAGES[self._mode][0])
            self._edit_values(values, self._value_page_buttons()[self._mode].held, x, y, start, end)
        self._update_matrix()
        self._update_clip_notes()

    def _edit_range(self):
        """The steps a held page button edits: the clip loop, or this page when the loop is
        not on it."""
        start = int(self._clip.loop_start / self._quantization)
        end = int(self._clip.loop_end / self._quantization)
        if (self._page + 1) * 8 > end or self._page * 8 < start:
            start = self._page * 8
            end = (self._page + 1) * 8
        return max(start, 0), end

    def _value_page_buttons(self):
        return {
            STEPSEQ_MODE_NOTES_OCTAVES: self._octaves_button,
            STEPSEQ_MODE_NOTES_VELOCITIES: self._velocities_button,
            STEPSEQ_MODE_NOTES_LENGTHS: self._lengths_button,
        }

    def _edit_pitch(self, x, y, start, end):
        if self._pitches_button.held:  # every step of the loop gets this lane only
            for step in range(start, end):
                for lane_row in range(LANES):
                    self._notes_pitches[self._pitch_index(step, lane_row)] = 0
                self._notes_pitches[self._pitch_index(step, y)] = 1
            return
        index = self._pitch_index(x + 8 * self._page, y)
        if self._notes_pitches[index] == 1:
            self._notes_pitches[index] = 0
            return
        if self._is_monophonic:  # one note per step
            for lane_row in range(LANES):
                self._notes_pitches[self._pitch_index(x + 8 * self._page, lane_row)] = 0
        self._notes_pitches[index] = 1

    def _edit_values(self, values, held, x, y, start, end):
        """Set one step's value; held: the left half sets every step of the loop, the right
        half steps them up (top rows) or down (bottom rows)."""
        if not held:
            values[x + 8 * self._page] = TOP_VALUE - y
        elif x < 4:
            for step in range(start, end):
                values[step] = TOP_VALUE - y
        else:
            for step in range(start, end):
                if y < 3 and values[step] < TOP_VALUE:
                    values[step] += 1
                if y > 3 and values[step] > 0:
                    values[step] -= 1

    def _randomise(self):
        start, end = self._edit_range()
        self._ensure_steps(end)

        for x in range(start, end):
            if self._mode == STEPSEQ_MODE_NOTES:
                val2 = randrange(0, 9)
                for y in range(7):
                    self._notes_pitches[x * 7 + 6 - y] = val2 == y
            elif self._mode == STEPSEQ_MODE_NOTES_OCTAVES:
                val = randrange(2, 6)
                self._notes_octaves[x] = val
            elif self._mode == STEPSEQ_MODE_NOTES_VELOCITIES:
                val = randrange(0, 7)
                self._notes_velocities[x] = val
            elif self._mode == STEPSEQ_MODE_NOTES_LENGTHS:
                val = randrange(0, 4)
                self._notes_lengths[x] = val

        self._update_clip_notes()

    # SIDE BUTTONS
    def _side_button(self, index, on_press, on_release, paint, refresh=None):
        press_button = PressButton(self._has_clip, on_press, on_release, paint, refresh)
        press_button.set_button(self._side_buttons[index])
        return press_button

    def _has_clip(self):
        return self.is_enabled() and self._clip != None

    def _side_press_buttons(self):
        return (
            self._octaves_button,
            self._lengths_button,
            self._velocities_button,
            self._pitches_button,
            self._random_button,
        )

    def _page_button(self, index, mode, skin, message, on_press=ignore, refresh=None):
        """A page button: lit on its page; a release shows the page."""

        def paint(button):
            if self.is_enabled():
                if self._clip != None:
                    button.set_on_off_values(skin + ".On", skin + ".Dim")
                    if self._mode == mode:
                        button.turn_on()
                    else:
                        button.turn_off()
                else:
                    button.set_light("DefaultButton.Disabled")

        def on_release(press_button, now):
            self._on_page_release(press_button, now, mode, message)

        return self._side_button(index, on_press, on_release, paint, refresh)

    def _on_page_release(self, press_button, now, mode, message):
        if mode == STEPSEQ_MODE_NOTES:
            self._is_mute_shifted = False
            self._is_velocity_shifted = False
            if press_button.since_release(now) < MONO_DOUBLE_TAP:
                self._is_monophonic = not self._is_monophonic
                self._update_clip_notes()
                self._step_sequencer._update_OSD()
                return
        elif mode == STEPSEQ_MODE_NOTES_VELOCITIES:
            self._is_mute_shifted = False
        self.set_mode(mode)
        self._control_surface.show_message(message)
        self.update()
        self._step_sequencer._update_OSD()

    def _on_pitches_press(self, press_button, now):
        self._is_mute_shifted = True
        self._is_velocity_shifted = True

    def _on_velocities_press(self, press_button, now):
        self._is_mute_shifted = True

    def _on_velocities_changed(self):
        self._step_sequencer._is_mute_shifted = self._is_mute_shifted

    # RANDOM
    def _paint_random_button(self, button):
        if self.is_enabled():
            if self._clip != None:
                button.set_on_off_values("StepSequencer2.Random.On", "StepSequencer2.Random.Off")
                button.turn_off()
            else:
                button.set_light("DefaultButton.Disabled")

    def _on_random_press(self, press_button, now):
        press_button.button.set_on_off_values("StepSequencer2.Random.On", "StepSequencer2.Random.Off")
        press_button.button.turn_on()

    def _on_random_release(self, press_button, now):
        press_button.button.set_on_off_values("StepSequencer2.Random.On", "StepSequencer2.Random.Off")
        press_button.button.turn_off()
        self._control_surface.show_message("randomise")
        self._randomise()
