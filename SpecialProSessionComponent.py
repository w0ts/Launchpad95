# imported from https://github.com/poltow/Launchpad97
"""Pro session: the session with the eight side buttons as modifiers.

Side buttons, top to bottom (tap / double tap / held + pad / held + shift + pad):
0 undo (tap undo, long press redo), 1 shift (select clip; double tap hides the detail
view), 2 click (copy/paste clip, launch scene; double tap metronome), 3 quantize (quantize
clip, create scene; double tap record quantization), 4 double (double the loop, capture
scene; double tap fixed length), 5 delete (delete clip, delete scene; double tap unmutes
all), 6 duplicate (duplicate clip, duplicate scene; double tap unsolos all), 7 record (tap
session record, held + pad arms and launches, shift + record toggles autorecord).
The bottom row while one is held: ProSessionBottomRow. The pads: SpecialClipSlotComponent.
"""

from types import SimpleNamespace

import Live
from _Framework import Task
from _Framework.SubjectSlot import subject_slot_group

from .PressButton import PressButton, ignore, lit_painter
from .ProSessionBottomRow import ProSessionBottomRow
from .ProSessionSettings import (
    LAUNCH_QNTZ_RATES,
    REC_QNTZ_RATES,
    launch_quantization_name,
    next_fixed_length,
    previous_fixed_length,
    record_quantization_name,
    step,
)
from .SpecialProSessionRecordingComponent import SpecialProSessionRecordingComponent
from .SpecialProSessionSceneComponent import SpecialSceneComponent
from .SpecialSessionComponent import SpecialSessionComponent
from .TargetTrackComponent import TargetTrackComponent

_Q = Live.Song.Quantization
Rec_Q = Live.Song.RecordingQuantization

MIN_TEMPO, MAX_TEMPO = 1, 999
TAP_TEMPO_UNDO_SECONDS = 1.5


class SpecialProSessionComponent(ProSessionBottomRow, SpecialSessionComponent):
    """Special session subclass that handles ConfigurableButtons"""

    scene_component_type = SpecialSceneComponent

    def __init__(
        self, num_tracks, num_scenes, stop_clip_buttons, side_buttons, control_surface, main_selector, livesong=None
    ):
        self._pro_mode_on = False
        SpecialSessionComponent.__init__(
            self,
            num_tracks=num_tracks,
            num_scenes=num_scenes,
            stop_clip_buttons=stop_clip_buttons,
            control_surface=control_surface,
            main_selector=main_selector,
        )
        self._side_buttons = side_buttons
        self._osd = None
        self._song = livesong
        self.copy_buffer = None  # the clip slot click + pad copied
        self._record_mode_on = False  # autorecord
        self._is_arming = False
        self._armed_track_count = 0
        self._tap_button = None

        self._end_undo_step_task = self._tasks.add(
            Task.sequence(Task.wait(TAP_TEMPO_UNDO_SECONDS), Task.run(self.song().end_undo_step))
        )
        self._end_undo_step_task.kill()

        self._launch_quantization = self._song.clip_trigger_quantization
        self._launch_quantization_on = self._launch_quantization != _Q.q_no_q
        record_quantization = self._song.midi_recording_quantization
        self._record_quantization_on = record_quantization != Rec_Q.rec_q_no_q
        self._record_quantization = record_quantization if self._record_quantization_on else Rec_Q.rec_q_sixtenth
        self._fixed_length = 1
        self._fixed_length_on = False

        self._song.add_clip_trigger_quantization_listener(self._on_clip_trigger_quantization_changed_in_live)
        self._song.add_midi_recording_quantization_listener(self._on_record_quantization_changed_in_live)
        self.song().add_session_record_listener(self._on_session_record_changed_in_live)
        self._song.add_metronome_listener(self._on_metronome_status_changed)

        self._session_record = SpecialProSessionRecordingComponent(
            target_track_component=TargetTrackComponent(), control_surface=self._control_surface
        )
        self._session_record._set_parent(self)

        if self._control_surface._mk2_rgb:
            from .ColorsMK2 import CLIP_COLOR_TABLE, RGB_COLOR_TABLE

            self.set_rgb_mode(CLIP_COLOR_TABLE, RGB_COLOR_TABLE)

        for scene_index in range(self._num_scenes):
            self.scene(scene_index)._set_session(self, self._num_tracks)
        self.modifiers = self._make_modifiers()
        for modifier, button in zip(self.modifiers.all, self._side_buttons, strict=True):
            modifier.set_button(button)
            button.turn_off()
        self.update()

    def _make_modifiers(self):
        """The eight side buttons, top to bottom: (skin, lit, press, release[, refresh, held])."""
        song = self.song

        def modifier(skin, is_lit, on_press, on_release, refresh=self.update, tracks_held=True):
            skin_name = skin if callable(skin) else (lambda: skin)
            paint = lit_painter(self._is_pro_active, skin_name, is_lit)
            return PressButton(self._is_pro_active, on_press, on_release, paint, refresh, tracks_held=tracks_held)

        undo = modifier(
            "ProSession.Undo", lambda: song().can_undo, ignore, self._on_undo_release, refresh=lambda: undo.update()
        )
        held_modifiers = (
            ("shift", "ProSession.Shift", self._is_shift_lit, self._on_shift_press, self._on_shift_release),
            ("click", "ProSession.Click", lambda: song().metronome, self._on_click_press, self._on_click_release),
            (
                "quantize",
                "ProSession.Quantize",
                self._is_quantize_lit,
                self._on_quantize_press,
                self._on_quantize_release,
            ),
            ("double", "ProSession.Double", self._is_fixed_length_lit, self._on_double_press, self._on_double_release),
            ("delete", "ProSession.Delete", self._is_delete_lit, self._on_delete_press, self._on_delete_release),
            (
                "duplicate",
                "ProSession.Duplicate",
                self._is_duplicate_lit,
                self._on_duplicate_press,
                self._on_duplicate_release,
            ),
        )
        record = modifier(
            self._record_skin, self._is_recording, self._on_record_press, self._on_record_release, tracks_held=False
        )
        table = (("undo", undo), *((name, modifier(*row)) for name, *row in held_modifiers), ("record", record))
        modifiers = SimpleNamespace(**dict(table))
        modifiers.all = tuple(press_button for _, press_button in table)
        return modifiers

    def disconnect(self):
        self._song.remove_clip_trigger_quantization_listener(self._on_clip_trigger_quantization_changed_in_live)
        self._song.remove_midi_recording_quantization_listener(self._on_record_quantization_changed_in_live)
        self.song().remove_session_record_listener(self._on_session_record_changed_in_live)
        self._song.remove_metronome_listener(self._on_metronome_status_changed)
        for modifier in self.modifiers.all:
            modifier.set_button(None)
            modifier.held = False
        self._end_undo_step_task.kill()
        self._end_undo_step_task = None
        self._record_quantization_on = False
        self.copy_buffer = None
        self._tap_button = None
        super().disconnect()

    # -- state the pads and the session recording read
    def is_pro_mode_on(self):
        return self._pro_mode_on

    def set_pro_mode_on(self, pro_mode_on):
        self._pro_mode_on = pro_mode_on

    def _is_pro_active(self):
        return self.is_enabled() and self._pro_mode_on

    def should_arm(self):
        return self.modifiers.record.held or self._record_mode_on

    def is_fixed_length_on(self):
        return self._fixed_length_on

    def get_fixed_length(self):
        """The fixed length to record or create clips with, in beats."""
        if self._fixed_length == 0.25:
            return 1.0
        return 4.0 / self.song().signature_denominator * self.song().signature_numerator * self._fixed_length

    def get_launch_quant(self):
        return self.song().clip_trigger_quantization

    @property
    def record_quantization(self):
        return self._record_quantization

    # -- side buttons
    def _on_undo_release(self, modifier, now):
        song = self.song()
        if not modifier.is_long_press(now):
            if song.can_undo:
                song.undo()
                self._print("Undo")
            else:
                self._print("Can't Undo!")
        elif song.can_redo:
            song.redo()
            self._print("Redo")
        else:
            self._print("Can`t Redo!")

    def _is_quantize_lit(self):
        return self._record_quantization_on

    def _is_fixed_length_lit(self):
        return self._fixed_length_on

    def _is_delete_lit(self):
        return self.modifiers.delete.held

    def _is_duplicate_lit(self):
        return self.modifiers.duplicate.held

    def _is_shift_lit(self):
        return self.modifiers.shift.held or self._launch_quantization_on

    def _on_shift_press(self, modifier, now):
        self._print("Select clip - [ Set launch quantization -> now: " + self._get_launch_quant_msg() + " ]")

    def _on_shift_release(self, modifier, now):
        if modifier.is_double_tap(now):
            self.application().view.hide_view("Detail")

    def _shift_held(self):
        return self.modifiers.shift.held

    def _on_click_press(self, modifier, now):
        self._print(("Launch scene" if self._shift_held() else "Copy/paste clip") + " - [ Tempo ]")

    def _on_click_release(self, modifier, now):
        self._tap_button = None
        self.copy_buffer = None
        if modifier.is_double_tap(now):
            song = self.song()
            song.metronome = not song.metronome
            self._print("Metronome On" if song.metronome else "Metronome Off")

    def _on_quantize_press(self, modifier, now):
        action = "Create Scene" if self._shift_held() else "Quantize clip"
        self._print(action + " - [ Record quantization -> now: " + self._get_record_quant_msg() + " ]")

    def _on_quantize_release(self, modifier, now):
        if modifier.is_double_tap(now):
            self._toggle_record_quantization()

    def _on_double_press(self, modifier, now):
        action = "Capture scene" if self._shift_held() else "Double midi clip"
        self._print(action + " - [ Clip fixed length recording -> now: " + self._get_fixed_length_msg() + " ]")

    def _on_double_release(self, modifier, now):
        if modifier.is_double_tap(now):
            self._toggle_fixed_length()
            self._display_fixed_length_info()

    def _all_tracks(self):
        return tuple(self.song().tracks) + tuple(self.song().return_tracks)

    def _on_delete_press(self, modifier, now):
        self._print("Delete scene" if self._shift_held() else "Delete clip  - [ Mute Tracks ]")

    def _on_delete_release(self, modifier, now):
        if modifier.is_double_tap(now):
            for track in self._all_tracks():
                if track.mute:
                    track.mute = False

    def _on_duplicate_press(self, modifier, now):
        self._print("Duplicate scene" if self._shift_held() else "Duplicate clip - [ Solo track ]")

    def _on_duplicate_release(self, modifier, now):
        if modifier.is_double_tap(now):
            for track in self._all_tracks():
                if track.solo:
                    track.solo = False

    def _record_skin(self):
        return "ProSession.SessionRecMode" if self._record_mode_on else "ProSession.SessionRec"

    def _is_recording(self):
        song = self.song()
        return song.session_record_status == Live.Song.SessionRecordStatus.on or song.session_record

    def _on_record_press(self, modifier, now):
        if self._shift_held():
            self._record_mode_on = not self._record_mode_on
            self._session_record.set_record_mode(self._record_mode_on)
            self._print("Autorecord: On" if self._record_mode_on else "Autorecord: Off")
        else:
            modifier.held = True
            modifier.pressed_at = now
            self._print("Record clip -  [ Arm track ]")

    def _on_record_release(self, modifier, now):
        if self._shift_held():
            return
        modifier.held = False
        if not modifier.is_long_press(now) and not self._is_arming:
            self._session_record._on_record_button_value()
        self._armed_track_count = 0
        self._is_arming = False

    # -- settings (side-button double taps and the bottom row)
    def _toggle_record_quantization(self):
        self._record_quantization_on = not self._record_quantization_on
        rate = self._record_quantization if self._record_quantization_on else Rec_Q.rec_q_no_q
        self.song().midi_recording_quantization = rate

    def _step_record_quantization(self, delta):
        current = self.song().midi_recording_quantization
        if current != Rec_Q.rec_q_no_q:
            rate = step(REC_QNTZ_RATES, current, delta)
            if rate is not None:
                self.song().midi_recording_quantization = rate

    def _choose_record_quantization(self, rate):
        if self.song().midi_recording_quantization != rate:
            self.song().midi_recording_quantization = rate
        else:
            self._toggle_record_quantization()

    def _toggle_launch_quantization(self):
        self._launch_quantization_on = not self._launch_quantization_on
        rate = self._launch_quantization if self._launch_quantization_on else _Q.q_no_q
        self.song().clip_trigger_quantization = rate

    def _step_launch_quantization(self, delta):
        if self._launch_quantization_on:
            rate = step(LAUNCH_QNTZ_RATES, self._launch_quantization, delta)
            if rate is not None:
                self.song().clip_trigger_quantization = rate

    def _choose_launch_quantization(self, rate):
        if self.song().clip_trigger_quantization != rate:
            self.song().clip_trigger_quantization = rate
        else:
            self._toggle_launch_quantization()

    def _toggle_fixed_length(self):
        self._fixed_length_on = not self._fixed_length_on

    def _step_fixed_length(self, delta):
        if self._fixed_length_on:
            change = next_fixed_length if delta > 0 else previous_fixed_length
            self._fixed_length = change(self._fixed_length)

    def _choose_fixed_length(self, length):
        if self._fixed_length != length:
            self._fixed_length = length
            self._fixed_length_on = True
        else:
            self._toggle_fixed_length()

    def _tap_tempo(self):
        if not self._end_undo_step_task.is_running:
            self.song().begin_undo_step()
        self._end_undo_step_task.restart()
        self.song().tap_tempo()

    def _change_tempo(self, tempo_delta):
        new_tempo = int(self.song().tempo + tempo_delta)
        if MIN_TEMPO <= new_tempo < MAX_TEMPO:
            self.song().tempo = new_tempo

    # -- Live listeners
    def _on_metronome_status_changed(self):
        self.modifiers.click.update()

    def _on_record_quantization_changed_in_live(self):
        rate = self._song.midi_recording_quantization
        self._record_quantization_on = rate != Rec_Q.rec_q_no_q
        if self._record_quantization_on:
            self._record_quantization = rate
        self._print("Record quantization: " + self._get_record_quant_msg())
        self.update()

    def _on_clip_trigger_quantization_changed_in_live(self):
        rate = self._song.clip_trigger_quantization
        self._launch_quantization_on = rate != _Q.q_no_q
        if self._launch_quantization_on:
            self._launch_quantization = rate
        self._print("Launch quantization: " + self._get_launch_quant_msg())
        self.update()

    def _on_session_record_changed_in_live(self):
        self.update()

    # -- messages
    def _get_record_quant_msg(self):
        if self._record_quantization_on:
            return "ON: " + record_quantization_name(self._record_quantization)
        return "OFF"

    def _get_launch_quant_msg(self):
        if self._launch_quantization_on:
            return "ON: " + launch_quantization_name(self._launch_quantization)
        return "OFF"

    def _display_fixed_length_info(self):
        """Displays the current fixed recording length/state in the status bar."""
        if self._is_pro_active():
            self._print("Fixed length: " + self._get_fixed_length_msg())

    def _get_fixed_length_msg(self):
        if not self._fixed_length_on:
            return "OFF"
        named = {0.25: "1 Beat", 0.5: "2 Beats", 1: "1 Bar"}
        if self._fixed_length in named:
            return "ON: " + named[self._fixed_length]
        song = self.song()
        bars = int((self.get_fixed_length() * (song.signature_denominator / 4.0)) / song.signature_numerator)
        return "ON: " + str(bars) + " Bars"

    def _print(self, msg):
        if self._control_surface != None:
            self._control_surface.show_message(str(msg))

    # -- framework hooks
    @subject_slot_group("value")
    def _on_stop_track_value(self, value, button):
        if not self._pro_mode_on:
            super()._on_stop_track_value(value, button)
        elif self.is_enabled():
            if not self._bottom_row_value(value, button):
                super()._on_stop_track_value(value, button)
            self.update()

    def update(self):
        SpecialSessionComponent.update(self)
        if self._pro_mode_on:
            m = self.modifiers
            for modifier in (m.shift, m.undo, m.click, m.delete, m.quantize, m.duplicate, m.double, m.record):
                modifier.update()
            self._update_stop_track_clip_buttons()
        if self._main_selector._main_mode_index == 0:
            self._update_OSD()

    def set_enabled(self, enabled):
        SpecialSessionComponent.set_enabled(self, enabled)
        self._session_record.set_enabled(enabled and self._pro_mode_on)
        if self._main_selector._main_mode_index == 0:
            self._update_OSD()

    def set_stop_track_clip_buttons(self, buttons):
        if (not self._pro_mode_on) or buttons != None:
            super(SpecialSessionComponent, self).set_stop_track_clip_buttons(buttons)
