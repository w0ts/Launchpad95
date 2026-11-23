"""Pro session bottom row (the stop-clip buttons): what it shows and does while a side
button is held.

- record: arm tracks (or fold group tracks); duplicate: solo; delete: mute
- shift: launch quantization; quantize: record quantization; double: fixed length.
  These three rows share one layout: pad 0 on/off, pad 1 down, pad 2 up, pads 3-7 one
  value each (a second press on the current value toggles the setting)
- click: pad 0 metronome, 1/2 nudge down/up, 3-6 tempo -5/-1/+1/+5, 7 tap tempo
- nothing held: stop clips, as in the plain session
"""

from _Framework.SessionComponent import SessionComponent
from _Framework.Util import in_range

from .ProSessionSettings import (
    FIXED_LENGTH_VALUES,
    LAUNCH_QNTZ_FIXED_RATES,
    LAUNCH_QNTZ_RATES,
    MAX_FIXED_LENGTH,
    MIN_FIXED_LENGTH,
    REC_QNTZ_FIXED_RATES,
    REC_QNTZ_RATES,
)

# Settings rows: pad 0 on/off, 1 down, 2 up, then the fixed values.
TOGGLE_PAD, DOWN_PAD, UP_PAD, FIRST_VALUE_PAD = 0, 1, 2, 3
# Tempo row (click held).
METRONOME_PAD, NUDGE_DOWN_PAD, NUDGE_UP_PAD, TAP_TEMPO_PAD = 0, 1, 2, 7
TEMPO_DELTAS = {3: -5, 4: -1, 5: 1, 6: 5}
TEMPO_SKINS = (
    None,  # metronome: on/off
    "Metronome.Nudge",
    "Metronome.Nudge",
    "Metronome.DeltaFive",
    "Metronome.DeltaOne",
    "Metronome.DeltaOne",
    "Metronome.DeltaFive",
    "Metronome.DeltaOne",
)


def _on_off(is_on):
    return ".On" if is_on else ".Off"


class ProSessionBottomRow:
    """Mixin for SpecialProSessionComponent."""

    # -- LEDs
    def _update_stop_track_clip_buttons(self):
        self._tap_button = None
        if self.is_enabled():
            for index in range(self._num_tracks):
                self._update_stop_clips_led(index)
            for index in range(8):
                self._update_select_leds(index)

    def _update_stop_clips_led(self, index):
        if not self.is_pro_mode_on():
            # the framework's own stop LED (not SpecialSessionComponent's)
            SessionComponent._update_stop_clips_led(self, index)
        elif self._stop_track_clip_buttons != None and index < len(self._stop_track_clip_buttons):
            button = self._stop_track_clip_buttons[index]
            track = self._track_at(index)
            if track is None:
                button.send_value("DefaultButton.Disabled")
            else:
                self._send_track_led(button, track)

    def _send_track_led(self, button, track):
        m = self.modifiers
        if m.record.held:
            if track.can_be_armed:
                button.send_value("Recording" + _on_off(track.arm))
            elif track.is_foldable:
                folded = track.fold_state != 0
                button.send_value("ProSession.ClipFoldedTrack" if folded else "ProSession.ClipUnFoldedTrack")
        elif m.duplicate.held:
            button.send_value("Mixer.Solo" + _on_off(track.solo))
        elif m.delete.held:
            button.send_value("TrackController.Mute" + _on_off(not track.mute))
        elif not (m.quantize.held or m.click.held or m.double.held or m.shift.held):
            if track.fired_slot_index == -2:
                button.send_value(self._stop_clip_triggered_value)
            elif track.playing_slot_index >= 0:
                button.send_value(self._stop_clip_value)
            else:
                button.turn_off()

    def _update_select_leds(self, index):
        if (
            self.is_pro_mode_on()
            and self._stop_track_clip_buttons != None
            and index < len(self._stop_track_clip_buttons)
        ):
            m = self.modifiers
            if m.quantize.held:
                self._update_rec_qntz_leds(index)
            elif m.click.held:
                self._update_tempo_leds(index)
            elif m.double.held:
                self._update_fixed_length_leds(index)
            elif m.shift.held:
                self._update_clip_trigger_leds(index)

    def _update_clip_trigger_leds(self, index):
        on = self._launch_quantization_on
        current = self.song().clip_trigger_quantization
        self._send_settings_led(
            index,
            "LaunchQuant",
            on,
            can_go_down=on and current != LAUNCH_QNTZ_RATES[0],
            can_go_up=on and current != LAUNCH_QNTZ_RATES[-1],
            value=current if on else self._launch_quantization,
            values=LAUNCH_QNTZ_FIXED_RATES,
        )

    def _update_rec_qntz_leds(self, index):
        on = self._record_quantization_on
        current = self.song().midi_recording_quantization
        self._send_settings_led(
            index,
            "RecQuant",
            on,
            can_go_down=on and current != REC_QNTZ_RATES[0],
            can_go_up=on and current != REC_QNTZ_RATES[-1],
            value=current if on else self._record_quantization,
            values=REC_QNTZ_FIXED_RATES,
        )

    def _update_fixed_length_leds(self, index):
        on = self._fixed_length_on
        self._send_settings_led(
            index,
            "FixedLength",
            on,
            can_go_down=on and self._fixed_length > MIN_FIXED_LENGTH,
            can_go_up=on and self._fixed_length < MAX_FIXED_LENGTH,
            value=self._fixed_length,
            values=FIXED_LENGTH_VALUES,
        )

    def _send_settings_led(self, index, prefix, on, can_go_down, can_go_up, value, values):
        button = self._stop_track_clip_buttons[index]
        if index == TOGGLE_PAD:
            button.send_value(prefix + _on_off(on))
        elif index == DOWN_PAD:
            button.send_value(prefix + ".PlusMinus" + _on_off(can_go_down))
        elif index == UP_PAD:
            button.send_value(prefix + ".PlusMinus" + _on_off(can_go_up))
        elif value in values and index - FIRST_VALUE_PAD == values.index(value):
            button.send_value(prefix + (".Value.On" if on else ".Value.Idle"))
        else:
            button.send_value(prefix + ".Value.Off")

    def _update_tempo_leds(self, index):
        button = self._stop_track_clip_buttons[index]
        if index == METRONOME_PAD:
            button.send_value("Metronome" + _on_off(self.song().metronome))
            return
        if index == TAP_TEMPO_PAD:
            self._tap_button = button
        button.send_value(TEMPO_SKINS[index])

    # -- presses
    def _bottom_row_value(self, value, button):
        """A bottom-row press or release in pro session; False when no modifier is held."""
        m = self.modifiers
        index = list(self._stop_track_clip_buttons).index(button)
        pressed = value != 0 or not button.is_momentary()
        if m.quantize.held:
            if pressed:
                self._choose_setting(index, self._record_quantization_row())
        elif m.double.held:
            if pressed:
                self._choose_setting(index, self._fixed_length_row())
                self._display_fixed_length_info()
        elif m.click.held:
            self._tempo_pad(index, value, pressed)
        elif m.shift.held:
            if pressed:
                self._choose_setting(index, self._launch_quantization_row())
        elif m.record.held or m.duplicate.held or m.delete.held:
            track = self._track_at(index) if pressed else None
            if track is not None and track in self.song().tracks:
                self._track_pad(track)
        else:
            return False
        return True

    def _record_quantization_row(self):
        return (
            self._toggle_record_quantization,
            self._step_record_quantization,
            self._choose_record_quantization,
            REC_QNTZ_FIXED_RATES,
        )

    def _launch_quantization_row(self):
        return (
            self._toggle_launch_quantization,
            self._step_launch_quantization,
            self._choose_launch_quantization,
            LAUNCH_QNTZ_FIXED_RATES,
        )

    def _fixed_length_row(self):
        return (self._toggle_fixed_length, self._step_fixed_length, self._choose_fixed_length, FIXED_LENGTH_VALUES)

    @staticmethod
    def _choose_setting(index, row):
        """A press on a settings row: (toggle, step(delta), choose(value), values)."""
        toggle, step, choose, values = row
        if index == TOGGLE_PAD:
            toggle()
        elif index == DOWN_PAD:
            step(-1)
        elif index == UP_PAD:
            step(1)
        else:
            choose(values[index - FIRST_VALUE_PAD])

    def _tempo_pad(self, index, value, pressed):
        song = self.song()
        if index == NUDGE_DOWN_PAD:
            song.nudge_down = value > 0
        elif index == NUDGE_UP_PAD:
            song.nudge_up = value > 0
        elif not pressed:
            return
        elif index == METRONOME_PAD:
            song.metronome = not song.metronome
        elif index == TAP_TEMPO_PAD:
            self._tap_tempo()
        else:
            self._change_tempo(TEMPO_DELTAS[index])

    def _track_pad(self, track):
        m = self.modifiers
        if m.record.held:
            self._arm_or_fold(track)
        elif m.duplicate.held:
            track.solo = not track.solo
        else:
            track.mute = not track.mute

    def _arm_or_fold(self, track):
        self._is_arming = True
        song = self.song()
        if track.can_be_armed:
            if track.arm:
                track.arm = False
                return
            exclusive = song.exclusive_arm if not self._record_mode_on else self._armed_track_count == 0
            if exclusive:
                for other in song.tracks:
                    if other.can_be_armed and other.arm:
                        other.arm = False
            track.arm = True
            self._armed_track_count += 1
            if song.view.selected_track != track:
                song.view.selected_track = track
        elif track.is_foldable:
            track.fold_state = 1 if track.fold_state == 0 else 0

    def _track_at(self, index):
        """The track under a bottom-row pad, or None past the last one."""
        tracks = self.tracks_to_use()
        track_index = index + self.track_offset()
        return tracks[track_index] if in_range(track_index, 0, len(tracks)) else None
