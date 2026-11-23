"""The instrument controller's pads: note pads, drum pads and the quick-scale and
note-repeat controls drawn over them, and what pressing those controls does.

Mixin for InstrumentControllerComponent (it reads ``_matrix``, ``_scales``,
``_note_repeat``, ``_quick_scale_root``, ``_quick_scales`` and ``_note_repeat_selector``).

Quick scale (top two rows, three pages cycled by pad (7, 0)): KEY_MODE picks the root
(white keys on row 1, black keys on row 0, circle of fifths, relative scale),
SCALE_TYPE_MODE picks one of the quick scales, the third page sets the note repeater.
On a drum rack, the scale button toggles the same note-repeat controls in the top right
4x4 block.
"""

from .ScaleComponent import CIRCLE_OF_FIFTHS, KEY_NAMES

KEY_MODE = 0
SCALE_TYPE_MODE = 1
WHITE_KEYS = (0, 2, 4, 5, 7, 9, 11, 12)
BLACK_KEY_PADS = (0, 1, 3, 4, 5)  # row 0: the black key right of white key x

SWING_PRESETS = (0.0, 0.25, 0.5, 0.75)
SWING_SKINS = (
    "QuickScale.Quant.Straight",
    "QuickScale.Quant.Swing",
    "QuickScale.Quant.Dotted",
    "QuickScale.Quant.Flam",
)
NO_SWING_LEFT = 0.98  # the swing-up pad goes dark from here


def _drum_repeater_cells():
    """The drum rack note-repeat block (x 4-7, y 0-3)."""
    cells = {(4, 0): ("swing_step", -1), (5, 0): ("swing_step", 1), (6, 0): ("empty",), (7, 0): ("repeat",)}
    for index, x in enumerate(range(4, 8)):
        cells[(x, 1)] = ("swing", index)
        for y in (2, 3):
            # the colour follows the column, as it always has, not the rate's triplet-ness
            cells[(x, y)] = ("rate", (x - 4) * 2 + y - 2, x % 2 == 1)
    return cells


def _quick_scale_repeater_cells():
    """The quick-scale repeater page (rows 0-1)."""
    cells = {(0, 0): ("swing_step", -1), (1, 0): ("swing_step", 1), (6, 0): ("repeat",), (7, 0): ("page",)}
    for index in range(4):
        cells[(index + 2, 0)] = ("swing", index)
    for x in range(8):
        cells[(x, 1)] = ("rate", x, x % 2 == 1)
    return cells


DRUM_REPEATER_CELLS = _drum_repeater_cells()
QUICK_SCALE_REPEATER_CELLS = _quick_scale_repeater_cells()


def _fifths_step(key, steps):
    return CIRCLE_OF_FIFTHS[(CIRCLE_OF_FIFTHS.index(key) + steps + 12) % 12]


class InstrumentPads:
    # -- presses
    def _matrix_value_quickscale(self, value, x, y, is_momentary):  # matrix listener for the script's pads
        if not self.is_enabled() or (value == 0 and is_momentary):
            return
        scales = self._scales
        if scales.is_drumrack:
            self._repeater_pad(DRUM_REPEATER_CELLS.get((x, y)))
            self.update()
        elif not scales.is_enabled() and scales.is_quick_scale:
            if self._quick_scale_root == KEY_MODE:
                self._quick_scale_key_pad(x, y)
            elif self._quick_scale_root == SCALE_TYPE_MODE:
                self._quick_scale_type_pad(x, y)
            else:
                self._repeater_pad(QUICK_SCALE_REPEATER_CELLS.get((x, y)))
                self.update()

    def _repeater_pad(self, cell):
        if cell is None:
            return
        kind = cell[0]
        if kind == "swing_step":
            self._change_swing_amount_value(cell[1])
        elif kind == "swing":
            self._set_swing_amount_value(SWING_PRESETS[cell[1]])
        elif kind == "repeat":
            self._toggle_note_repeater()
            self._control_surface.show_message("REPEATER is: " + ("ON" if self._note_repeat.is_enabled() else "OFF"))
        elif kind == "rate":
            self._note_repeat.set_freq_index(cell[1])
            self._control_surface.show_message("REPEATER Step: " + str(self._note_repeat.freq_name()))
        elif kind == "page":
            self.setup_quick_scale_mode()

    def _quick_scale_key_pad(self, x, y):
        scales = self._scales
        key, modus = scales._key, scales._modus
        root = -1
        if y == 1 and x < 7 or y == 0 and x in BLACK_KEY_PADS:
            root = WHITE_KEYS[x] + (1 if y == 0 else 0)
            self._show_scale(root, modus)
            if root == key:  # the current root again: major <-> minor
                modus = self._alternate_modus(modus)
                self._show_scale(root, modus)
        elif y == 0 and x == 7:
            self.setup_quick_scale_mode()
            self.update()
        elif y == 1 and x == 7:
            root = _fifths_step(key, 1)
            self._show_fifths("->", key, root, modus)
        elif y == 0 and x == 6:
            root = _fifths_step(key, -1)
            self._show_fifths("<-", key, root, modus)
        elif y == 0 and x == 2:
            modus, root = scales._relative_scale(key, modus, -1)
            name = KEY_NAMES[root]  # root -1 (no relative scale): shows "B", as before
            self._control_surface.show_message("Relative scale : " + name + " " + str(scales._modus_names[modus]))
        if root != -1:
            scales.set_modus(modus, False)
            scales.set_key(root, False)
            self.update()

    def _show_scale(self, root, modus):
        self._control_surface.show_message(KEY_NAMES[root] + " " + str(self._scales._modus_names[modus]))

    def _show_fifths(self, arrow, key, root, modus):
        name = " " + str(self._scales._modus_names[modus])
        message = "circle of 5ths " + arrow + " " + KEY_NAMES[key] + name + " => " + KEY_NAMES[root] + name
        self._control_surface.show_message(message)

    def _alternate_modus(self, modus):
        scales = self._scales
        if modus == scales._major_modus:
            return scales._current_minor_mode
        if modus in scales._minor_modes:
            scales._current_minor_mode = modus
            return 0
        if modus == scales._minor_pentatonic_modus:
            return scales._major_pentatonic_modus
        if modus == scales._major_pentatonic_modus:
            return scales._minor_pentatonic_modus
        return modus

    def _quick_scale_type_pad(self, x, y):
        if y == 0 and x == 7:
            self.setup_quick_scale_mode()
            self.update()
            return
        index = x if y == 0 else x + 7
        if y in (0, 1) and index < len(self._quick_scales) and self._quick_scales[index] != -1:
            self._scales.set_modus(self._quick_scales[index])
            self._control_surface.show_message("mode : " + str(self._scales._modus_names[self._scales._modus]))
            self.update()

    # -- LEDs
    def _paint_repeater_cell(self, button, cell):
        kind = cell[0]
        if kind == "swing_step":
            button.set_on_off_values("QuickScale.Quant.On", "QuickScale.Quant.Off")
            swing = self._swing_amount()
            lit = swing != 0.0 if cell[1] < 0 else swing < NO_SWING_LEFT
            self._light(button, lit)
        elif kind == "swing":
            button.set_on_off_values(SWING_SKINS[cell[1]], "DefaultButton.Disabled")
            button.turn_on()
        elif kind == "repeat":
            button.set_on_off_values("QuickScale.NoteRepeater.On", "QuickScale.NoteRepeater.Off")
            self._light(button, self._note_repeat.is_enabled())
        elif kind == "rate":
            off_skin = "QuickScale.Quant.Tripplet" if cell[2] else "QuickScale.Quant.Note"
            button.set_on_off_values("QuickScale.Quant.Selected", off_skin)
            self._light(button, cell[1] == self._note_repeat.freq_index())
        elif kind == "page":
            button.set_light("QuickScale.Quant.Mode")
        else:
            button.set_light("DrumGroup.PadEmpty")

    @staticmethod
    def _light(button, lit):
        if lit:
            button.turn_on()
        else:
            button.turn_off()

    def _drum_note(self, x, y):
        """The drum note under a pad: two 4x4 blocks, 16 notes apart per octave."""
        if self._note_repeat_selector and x >= 4 and y < 4:
            return None  # a note-repeat control
        base = 16 * (self._scales._octave - 1)
        return base + x + 4 * (8 - y) if x < 4 else base + 32 + x + 4 * (7 - y)

    def _paint_drum_pads(self, non_feedback_channel):
        drums = self._drum_group_device
        for button, (x, y) in self._matrix.iterbuttons():
            if not button:
                continue
            note = self._drum_note(x, y)
            if note is None:
                button.set_enabled(True)
                button.set_channel(non_feedback_channel)
                self._paint_repeater_cell(button, DRUM_REPEATER_CELLS[(x, y)])
            elif 0 <= note < 128:
                filled = drums == None or (
                    drums.can_have_drum_pads and drums.has_drum_pads and drums.drum_pads[note].chains
                )
                button.set_light("DrumGroup.PadFilled" if filled else "DrumGroup.PadEmpty")
                button.set_enabled(False)
                button.set_channel(self.base_channel)
                button.set_identifier(note)
            else:
                button.set_light("DrumGroup.PadEmpty")
                button.set_enabled(True)
                button.set_channel(non_feedback_channel)

    def _paint_quick_scale_page(self):
        if self._quick_scale_root == KEY_MODE:
            self._paint_quick_scale_keys()
        elif self._quick_scale_root == SCALE_TYPE_MODE:
            self._paint_quick_scale_types()
        else:
            self._paint_quick_scale_repeater()

    def _quick_scale_colours(self):
        scales = self._scales
        if scales._modus in (scales._major_modus, scales._major_pentatonic_modus):
            return "QuickScale.Major"
        if scales._modus in (scales._natural_minor_modus, scales._minor_pentatonic_modus):
            return "QuickScale.Minor"
        return "QuickScale.Other"

    def _paint_quick_scale_keys(self):
        colours = self._quick_scale_colours()
        matrix = self._matrix
        matrix.get_button(7, 1).set_light(colours + ".CircleOfFifths")  # right
        matrix.get_button(6, 0).set_light(colours + ".CircleOfFifths")  # left
        matrix.get_button(7, 0).set_light(colours + ".Mode")
        matrix.get_button(2, 0).set_light(colours + ".RelativeScale")
        key = self._scales._key
        for row, pads, offset in ((0, BLACK_KEY_PADS, 1), (1, range(7), 0)):
            for x in pads:
                button = matrix.get_button(x, row)
                button.set_enabled(True)
                button.set_on_off_values(colours + ".Key")
                self._light(button, WHITE_KEYS[x] + offset == key)

    def _paint_quick_scale_types(self):
        matrix = self._matrix
        modus = self._scales._modus
        matrix.get_button(7, 0).set_light("QuickScale.Major.Mode")
        for x in range(7):
            button = matrix.get_button(x, 0)
            button.set_enabled(True)
            if self._quick_scales[x] != -1:
                button.set_on_off_values("QuickScale.Modus")
                self._light(button, self._quick_scales[x] == modus)
            else:
                button.set_light("DefaultButton.Disabled")
        for x in range(8):
            button = matrix.get_button(x, 1)
            button.set_enabled(True)
            if self._quick_scales[x + 7] != -1:
                button.set_on_off_values("QuickScale.Modus")
            else:
                button.set_on_off_values("DefaultButton.Disabled", "DefaultButton.Disabled")
            self._light(button, self._quick_scales[x + 7] == modus)

    def _paint_quick_scale_repeater(self):
        matrix = self._matrix
        self._paint_repeater_cell(matrix.get_button(7, 0), QUICK_SCALE_REPEATER_CELLS[(7, 0)])
        for row, width in ((0, 7), (1, 8)):
            for x in range(width):
                button = matrix.get_button(x, row)
                button.set_enabled(True)
                self._paint_repeater_cell(button, QUICK_SCALE_REPEATER_CELLS[(x, row)])

    def _paint_note_pads(self, non_feedback_channel):
        """The scale's notes; a note on several pads goes out on the next channel each time
        (up to 15), so Live can tell the pads apart."""
        note_channel = [self.base_channel] * 128
        pattern = self._scales.get_pattern()
        max_j = self._matrix.width() - 1
        a = 63 if self._scales.is_chromatic else 0
        for button, (i, j) in self._matrix.iterbuttons():
            if not button or (self._scales.is_quick_scale and j <= 1):
                continue
            a += 1
            note_info = pattern.note(i, max_j - j)
            if note_info.index != None:
                button.set_light(self._note_pad_skin(note_info))
                button.set_enabled(False)
                button.set_channel(note_channel[note_info.index])
                button.set_identifier(note_info.index)
                if note_channel[note_info.index] < 15:
                    note_channel[note_info.index] += 1
            else:
                button.set_channel(non_feedback_channel)
                button.set_identifier(a)
                button.set_light("Note.Pads.Invalid")
                button.set_enabled(True)
            button.force_next_send()

    @staticmethod
    def _note_pad_skin(note_info):
        if note_info.root:
            return "Note.Pads.Root"
        if note_info.highlight:
            return "Note.Pads.Highlight"
        if note_info.in_scale:
            return "Note.Pads.InScale"
        if note_info.valid:
            return "Note.Pads.OutOfScale"
        return "Note.Pads.Invalid"
