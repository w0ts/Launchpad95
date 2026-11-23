import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

from .SongScaleListener import SongScaleListener

KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
CIRCLE_OF_FIFTHS = [7 * k % 12 for k in range(12)]
# KEY_CENTERS = CIRCLE_OF_FIFTHS[0:6] + CIRCLE_OF_FIFTHS[-1:5:-1]


MUSICAL_MODES = []
for name, notes in Live.Song.get_all_scales_ordered():
    MUSICAL_MODES.append(name)
    MUSICAL_MODES.append(list(notes))

TOP_OCTAVE = {"chromatic_gtr": 7, "diatonic_ns": 2, "diatonic_chords": 7, "diatonic": 6, "chromatic": 7}

# Scale editor row 0, pads 2-6: (layout mode, interval, horizontal, message)
LAYOUT_PADS = {
    2: ("chromatic_gtr", 3, True, "mode: chromatic gtr"),
    3: ("diatonic_ns", 3, True, "mode: diatonic not staggered"),
    4: ("diatonic_chords", 2, False, "mode: diatonic vertical (chords)"),
    5: ("diatonic", 3, True, "mode: diatonic"),
    6: ("chromatic", 3, True, "mode: chromatic"),
}
DRUMRACK_PAD = 7
BLACK_KEY_PADS = (0, 1, 3, 4, 5)  # row 1: the black key right of white key x
QUICK_SCALE_PAD = (7, 1)
FIRST_SCALE_ROW = 4


def _on_off(skin, on):
    return skin + (".On" if on else ".Off")


class ScaleComponent(SongScaleListener, ControlSurfaceComponent):

    # matrix = control_matrix(PlayableControl)

    def __init__(self, control_surface=None, enabled=False, mode="diatonic", *a, **k):
        self._layout_set = False
        self._modus_list = [Modus(MUSICAL_MODES[v], MUSICAL_MODES[v + 1]) for v in range(0, len(MUSICAL_MODES), 2)]
        self._modus_names = [MUSICAL_MODES[v] for v in range(0, len(MUSICAL_MODES), 2)]
        self._control_surface = control_surface
        self._osd = None
        self._modus = 0
        self._key = 0
        self._octave = 3
        self._mode = mode  # diatonic
        self._is_drumrack = False
        self._quick_scale = False
        self._is_horizontal = True
        self._is_absolute = False
        self._interval = 3
        self._matrix = None
        self._top_octave = 6

        # C  D  E  F  G  A  B
        self._white_notes_index = [0, 2, 4, 5, 7, 9, 11]

        # Scales are found by name: their order comes from Live (Live.Song.get_all_scales_ordered)
        self._major_modus = self._modus_index("Major")
        self._natural_minor_modus = self._modus_index("Minor")
        self._minor_pentatonic_modus = self._modus_index("Minor Pentatonic")
        self._major_pentatonic_modus = self._modus_index("Major Pentatonic")
        self._minor_modes = [
            i
            for i in (
                self._natural_minor_modus,
                self._modus_index("Harmonic Minor"),
                self._modus_index("Melodic Minor"),
            )
            if i != -1
        ]  # Natural, Harmonic, Melodic
        self._current_minor_mode = self._natural_minor_modus

        super().__init__(*a, **k)
        self.set_enabled(enabled)

    def _modus_index(self, name):
        """Index of the scale called name in Live's list, or -1."""
        try:
            return self._modus_names.index(name)
        except ValueError:
            return -1

    def set_enabled(self, enabled):
        ControlSurfaceComponent.set_enabled(self, enabled)
        if not enabled:
            self._remove_scale_listeners()
        else:
            self._register_scale_listeners()

    @property
    def notes(self):
        return self.modus.scale(self._key).notes

    @property
    def modus(self):
        return self._modus_list[self._modus]

    def set_key(self, key, message=True, listener_called=False):
        if key >= 0 and key <= 11:
            self._key = key % 12
            if not listener_called:
                self.song().root_note = self._key
            if message:
                self._control_surface.show_message(
                    str("Selected Scale: " + KEY_NAMES[self._key]) + " " + str(self._modus_names[self._modus])
                )

    def set_octave(self, octave, message=True):
        if octave >= 0 and octave < self._top_octave:
            self._octave = octave
            if message:
                self._control_surface.show_message("Selected octave: " + str(octave))

    def _set_top_octave(self, message=True):
        if self.is_drumrack:
            self._top_octave = 8
        else:
            self._top_octave = TOP_OCTAVE[self._mode]

        if self._octave >= self._top_octave:
            self._octave = self._top_octave - 1
            if message:
                self._control_surface.show_message("Selected octave: " + str(self._octave))

    def octave_up(self, message=True):
        self.set_octave(self._octave + 1, message)

    def octave_down(self, message=True):
        self.set_octave(self._octave - 1, message)

    def set_modus(self, index, message=True, listener_called=False):
        if index > -1 and index < len(self._modus_list):
            self._modus = index
            if not listener_called:
                self.song().scale_name = self._modus_names[self._modus]
            if message:
                self._control_surface.show_message(
                    str("selected scale: " + KEY_NAMES[self._key]) + " " + str(self._modus_names[self._modus])
                )

    def set_drumrack(self, drumrack):
        self._is_drumrack = drumrack
        self._set_top_octave(True)

    # def set_matrix(self, matrix):
    # 	if not matrix or not self._layout_set:
    # 		self._matrix = matrix
    # 		#self._matrix.set_control_element(matrix)
    # 		for index, button in enumerate(self._matrix):
    # 			#button.set_playable(False)
    # 			self._layout_set = bool(matrix)
    # 		self.update()
    def set_matrix(self, matrix):
        self._matrix = matrix
        if matrix:
            matrix.reset()
        if matrix != self._matrix:
            if self._matrix != None:
                self._matrix.remove_value_listener(self._matrix_pressed)
        self._matrix = matrix
        if self._matrix != None:
            self._matrix.add_value_listener(self._matrix_pressed)
        self.update()

    def set_osd(self, osd):
        self._osd = osd

    def _update_OSD(self):
        if self._osd != None:
            self._osd.attributes[0] = ""
            self._osd.attribute_names[0] = ""
            self._osd.attributes[1] = MUSICAL_MODES[self._modus * 2]
            self._osd.attribute_names[1] = "Scale"
            self._osd.attributes[2] = KEY_NAMES[self._key % 12]
            self._osd.attribute_names[2] = "Root Note"
            self._osd.attributes[3] = self._octave
            self._osd.attribute_names[3] = "Octave"
            self._osd.attributes[4] = " "
            self._osd.attribute_names[4] = " "
            self._osd.attributes[5] = " "
            self._osd.attribute_names[5] = " "
            self._osd.attributes[6] = " "
            self._osd.attribute_names[6] = " "
            self._osd.attributes[7] = " "
            self._osd.attribute_names[7] = " "
            self._osd.update()

    def update(self):
        if not self.is_enabled() or self._matrix == None:
            return
        super().update()
        self._update_OSD()
        for button, (col, row) in self._matrix.iterbuttons():
            button.set_enabled(True)
            button.set_light(self._pad_skin(col, row))

    def _pad_skin(self, col, row):
        """The scale editor pad colours: row 0 layouts, rows 1-2 keys, row 3 octaves, rows 4-7
        scales (a drum rack has only the drum rack, quick scale and octave pads)."""
        if row == 0:
            return self._layout_pad_skin(col)
        if row == 1:
            return self._black_key_row_skin(col)
        if row == 2:
            if self.is_drumrack:
                return "DefaultButton.Disabled"
            if col < 7:
                return _on_off("Scale.Key", self._key == self._white_notes_index[col])
            return "Scale.CircleOfFifths"
        if row == 3:
            if self._octave == col:
                return "Scale.Octave.On"
            return "Scale.Octave.Off" if col < self._top_octave else "DefaultButton.Disabled"
        index = (row - FIRST_SCALE_ROW) * 8 + col
        if self.is_drumrack or (row == 7 and index > len(self._modus_list)):
            return "DefaultButton.Disabled"
        return _on_off("Scale.Modus", self._modus == index)

    def _layout_pad_skin(self, col):
        if col == 0:
            return _on_off("Scale.AbsoluteRoot", self._is_absolute)
        if col == 1:
            return _on_off("Scale.Horizontal", self._is_horizontal)
        if col == DRUMRACK_PAD:
            return _on_off("Scale.Mode", self.is_drumrack)
        return _on_off("Scale.Mode", not self.is_drumrack and self._mode == LAYOUT_PADS[col][0])

    def _black_key_row_skin(self, col):
        if col == 7:
            return _on_off("Scale.QuickScale", self._quick_scale)
        if self.is_drumrack:
            return "DefaultButton.Disabled"
        if col in BLACK_KEY_PADS:
            return _on_off("Scale.Key", self._key == self._white_notes_index[col] + 1)
        return "Scale.RelativeScale" if col == 2 else "Scale.CircleOfFifths"

    def _matrix_pressed(self, value, x, y, is_momentary):
        if not self.is_enabled() or value <= 0:
            return
        if y == 0:
            self._layout_pad(x)
        if not self.is_drumrack:
            self._root_pad(x, y)
        if (x, y) == QUICK_SCALE_PAD:
            self._quick_scale = not self._quick_scale
            self._control_surface.show_message("Quick scale ON" if self._quick_scale else "Quick scale OFF")
        if y == 3:
            self.set_octave(x)
            self._control_surface.show_message("octave : " + str(self._octave))
        if y >= FIRST_SCALE_ROW and not self.is_drumrack:
            self.set_modus((y - FIRST_SCALE_ROW) * 8 + x, True)
            self._control_surface.show_message(
                "Selected Scale: " + KEY_NAMES[self._key] + " " + str(self._modus_names[self._modus])
            )
        self.update()

    def _layout_pad(self, x):
        """Row 0: absolute root, horizontal (diatonic), the layouts and the drum rack."""
        if x == 0 and not self.is_drumrack:
            self._is_absolute = not self._is_absolute
            self._control_surface.show_message("absolute root" if self._is_absolute else "relative root")
        elif x == 1 and not self.is_drumrack and self.is_diatonic:
            self._is_horizontal = not self._is_horizontal
            self._control_surface.show_message("Is Horizontal" if self._is_horizontal else "Is Vertical")
        elif x in LAYOUT_PADS:
            self._mode, self._interval, self._is_horizontal, message = LAYOUT_PADS[x]
            self._is_drumrack = False
            self._control_surface.show_message(message)
        elif x == DRUMRACK_PAD:
            self.set_drumrack(True)
            self._control_surface.show_message("mode: drumrack")
        self._set_top_octave(True)

    def _root_pad(self, x, y):
        """Rows 1-2: a root key, the circle of fifths (pads (6, 1) and (7, 2)) or the
        relative scale (pad (2, 1))."""
        key, modus = self._key, self._modus
        root = -1
        message = True
        if y == 1 and x in BLACK_KEY_PADS or y == 2 and x < 7:
            root = [0, 2, 4, 5, 7, 9, 11, 12][x] + (1 if y == 1 else 0)
        if (x, y) in ((7, 2), (6, 1)):
            arrow, steps = ("->", 1) if y == 2 else ("<-", -1)
            root = CIRCLE_OF_FIFTHS[(CIRCLE_OF_FIFTHS.index(key) + steps + 12) % 12]
            name = " " + str(self._modus_names[modus])
            self._control_surface.show_message(
                "circle of 5ths " + arrow + " " + KEY_NAMES[key] + name + " => " + KEY_NAMES[root] + name
            )
            message = False
        if (x, y) == (2, 1):
            modus, root = self._relative_scale(key, modus, root)
            self._control_surface.show_message(
                "Relative scale : " + KEY_NAMES[root] + " " + str(self._modus_names[modus])
            )
            message = False
        if root != -1:
            self.set_modus(modus, message)
            self.set_key(root, message)

    def _relative_scale(self, key, modus, root):
        """(modus, root) of the relative major/minor scale; ``root`` unchanged when the scale
        has none."""
        fifths = CIRCLE_OF_FIFTHS.index(key)
        if modus == self._major_modus:  # a minor third down
            return self._current_minor_mode, CIRCLE_OF_FIFTHS[(fifths + 3) % 12]
        if modus in self._minor_modes:  # Natural (Aeolian), Harmonic, Melodic Minor: a minor third up
            self._current_minor_mode = modus
            return 0, CIRCLE_OF_FIFTHS[(fifths - 3 + 12) % 12]
        if modus == self._minor_pentatonic_modus:
            return self._major_pentatonic_modus, CIRCLE_OF_FIFTHS[(fifths - 3) % 12]
        if modus == self._major_pentatonic_modus:
            return self._minor_pentatonic_modus, CIRCLE_OF_FIFTHS[(fifths + 3 + 12) % 12]
        return modus, root

    # @matrix.released
    def matrix_release(self, pad):
        pass
        # selected_drum_pad = self._coordinate_to_pad_map[pad.coordinate]
        # if selected_drum_pad in self._selected_pads:
        # 	self._selected_pads.remove(selected_drum_pad)
        # 	if not self._selected_pads:
        # 		self._update_control_from_script()
        # 	self.notify_pressed_pads()
        # self._update_led_feedback()

    @property
    def is_drumrack(self):
        return self._is_drumrack

    @property
    def is_diatonic(self):
        return not self.is_drumrack and (
            self._mode == "diatonic" or self._mode == "diatonic_ns" or self._mode == "diatonic_chords"
        )

    @property
    def is_chromatic(self):
        return not self.is_drumrack and (self._mode == "chromatic" or self._mode == "chromatic_gtr")

    @property
    def is_diatonic_ns(self):
        return self._mode == "diatonic_ns"

    @property
    def is_chromatic_gtr(self):
        return self._mode == "chromatic_gtr"

    @property
    def is_quick_scale(self):
        return self._quick_scale

    def get_pattern(self):
        notes = self.notes
        # origin
        if not self._is_absolute:
            origin = 0
        elif self.is_diatonic:
            origin = 0
            for k in range(len(notes)):
                if notes[k] >= 12:
                    origin = k - len(notes)
                    break
        else:
            origin = -notes[0]

        # interval
        if self._interval == None:
            interval = 8
        elif self.is_chromatic:
            interval = [0, 2, 4, 5, 7, 9, 10, 11][self._interval]
        else:
            interval = self._interval

        # layout
        if self._is_horizontal:
            steps = [1, interval]
            origin = [origin, 0]
        else:
            steps = [interval, 1]
            origin = [0, origin]

        return MelodicPattern(
            steps=steps,
            scale=notes,
            origin=origin,
            base_note=(self._octave + 1) * 12,
            chromatic_mode=self.is_chromatic,
            chromatic_gtr_mode=self.is_chromatic_gtr,
            diatonic_ns_mode=self.is_diatonic_ns,
        )


class Scale:

    # Input vars: scale name, array of scale steps -> (ScaleName, ScaleSteps)
    def __init__(self, name, notes, *a, **k):
        super().__init__(*a, **k)
        self.name = name
        self.notes = notes


class Modus(Scale):

    def __init__(self, *a, **k):
        super().__init__(*a, **k)

    def scale(self, base_note):
        return Scale(KEY_NAMES[base_note], [base_note + x for x in self.notes])

    def scales(self, base_notes):
        return [self.scale(b) for b in base_notes]


class MelodicPattern:

    def __init__(
        self,
        steps=None,
        scale=range(12),
        base_note=0,
        origin=None,
        valid_notes=range(128),
        chromatic_mode=False,
        chromatic_gtr_mode=False,
        diatonic_ns_mode=False,
        *a,
        **k,
    ):
        super().__init__(*a, **k)
        self.steps = steps if steps is not None else [0, 0]
        self.scale = scale
        self.base_note = base_note
        self.origin = origin if origin is not None else [0, 0]
        self.valid_notes = valid_notes
        self.chromatic_mode = chromatic_mode
        self.chromatic_gtr_mode = chromatic_gtr_mode
        self.diatonic_ns_mode = diatonic_ns_mode

    class NoteInfo:

        def __init__(self, index, channel, root=False, highlight=False, in_scale=False, valid=False):
            self.index = index
            self.channel = channel
            self.root = root
            self.highlight = highlight
            self.in_scale = in_scale
            self.valid = valid

    @property
    def _extended_scale(self):
        if self.chromatic_mode:
            first_note = self.scale[0]
            return range(first_note, first_note + 12)
        else:
            return self.scale

    def _octave_and_note(self, x, y):
        scale = self._extended_scale
        scale_size = len(scale)
        if self.chromatic_mode:
            self.steps[1] = 5
        else:
            if self.diatonic_ns_mode:
                self.steps[1] = scale_size
        index = self.steps[0] * (self.origin[0] + x) + self.steps[1] * (self.origin[1] + y)
        if self.chromatic_gtr_mode and y > 3:
            index = index - 1
        octave = index // scale_size
        note = scale[index % scale_size]
        return (octave, note)

    def note(self, x, y):
        octave, note = self._octave_and_note(x, y)
        index = self.base_note + 12 * octave + note
        if not 0 <= index < 128:
            index = None  # outside the MIDI range: the pad plays nothing
        root = note == self.scale[0]
        highlight = note == self.scale[2] or note == self.scale[4]
        in_scale = note in self.scale
        valid = index is not None and index in self.valid_notes
        return self.NoteInfo(index, x, root=root, highlight=highlight, in_scale=in_scale, valid=valid)
