"""Pro session pad: launches its clip, or with a side button held acts on the clip (or,
with shift too, on its scene)."""

import Live
from _Framework.ClipSlotComponent import ClipSlotComponent
from _Framework.SubjectSlot import subject_slot

from .ColorsMK2 import Blink, Pulse
from .ProSessionSettings import record_quantization_name
from .Settings import Settings

_Q = Live.Song.Quantization


class SpecialClipSlotComponent(ClipSlotComponent):
    quantization_component = None
    device = True

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._scene = None
        self._session = None
        self._launched_by_press = False  # the last press launched: forward its release

    def _set_parents(self, scene, session):
        self._scene = scene
        self._session = session

    @property
    def _modifiers(self):
        return self._session.modifiers

    def _is_selecting(self):
        """Shift alone: a pad selects its clip and shows it."""
        m = self._modifiers
        others = (m.click, m.quantize, m.double, m.delete, m.duplicate)
        return m.shift.held and not any(modifier.held for modifier in others)

    # -- pad
    @subject_slot("value")
    def _launch_button_value(self, value):
        if not self._session.is_pro_mode_on():
            super()._launch_button_value(value)
            return
        if not self.is_enabled():
            return
        if self._clip_slot is None and not self._modifiers.shift.held:
            return  # no track or scene under this pad; shift actions work on scenes
        if value:
            action = self._held_modifier_action(value)
            if action is not None:
                action()
                return
        if self._clip_slot is not None and (value or self._launched_by_press):
            # the release of a launching press goes on too: gate and legato launch modes need it
            self._launched_by_press = bool(value)
            if value and self._session.should_arm():
                self._do_track_arm()
            self._do_launch_clip(value)

    def _held_modifier_action(self, value):
        """What a press does with side buttons held (first match), or None to launch."""
        m = self._modifiers
        scene = self._scene
        shifted = m.shift.held
        actions = (
            (m.delete, lambda: scene._do_delete_scene(scene), self._do_delete_clip),
            (m.duplicate, scene._do_duplicate_scene, self._do_duplicate_clip),
            (m.click, lambda: scene._do_launch_scene(value), self._do_copypaste_clip),
            (m.double, scene._do_capture_and_insert_scene, self._do_double_loop),
            (m.quantize, scene._do_create_scene, self._do_quantize_clip),
        )
        for modifier, scene_action, clip_action in actions:
            if modifier.held:
                return scene_action if shifted else clip_action
        if shifted:
            return self._do_select_clip_slot
        return None

    # -- actions
    def _do_select_clip_slot(self):
        self._do_select_clip(self._clip_slot)

    def _do_select_clip(self, clip_slot):
        super()._do_select_clip(clip_slot)
        if self._clip_slot is None:
            return
        view = self.application().view
        if not view.is_view_visible("Detail"):
            view.show_view("Detail")
            self.device = True
        if clip_slot.clip:
            if not view.is_view_visible("Detail/Clip") and self.device and self._is_selecting():
                view.show_view("Detail/Clip")
        else:
            self.device = False
        if not view.is_view_visible("Detail/DeviceChain") and not self.device and self._is_selecting():
            view.show_view("Detail/DeviceChain")
        self.device = not self.device

    def _do_duplicate_clip(self):
        slot = self._clip_slot
        clip = slot.clip if slot else None
        if clip is None:
            return
        track = slot.canonical_parent
        view = self.song().view
        try:
            start_duplicate = clip.is_playing
            destination_index = track.duplicate_clip_slot(list(track.clip_slots).index(slot))
            view.highlighted_clip_slot = track.clip_slots[destination_index]
            view.detail_clip = view.highlighted_clip_slot.clip
            if start_duplicate:
                view.highlighted_clip_slot.fire(force_legato=True, launch_quantization=_Q.q_no_q)
            self._print("Clip duplicated")
        except (Live.Base.LimitationError, RuntimeError):
            pass  # no room (or Live refused): nothing to duplicate into

    def _do_copypaste_clip(self):
        clip_slot = self._clip_slot
        session = self._session
        if session.copy_buffer is None:
            if clip_slot.has_clip:
                session.copy_buffer = clip_slot
            return
        try:
            session.copy_buffer.duplicate_clip_to(clip_slot)
        except RuntimeError:
            pass  # Live refuses some targets (e.g. audio clip to a MIDI track)

    def _do_double_loop(self):
        self._do_select_clip(self._clip_slot)
        clip = self.song().view.detail_clip
        if clip and clip.is_midi_clip:
            try:
                clip.duplicate_loop()
                self._print("Clip length doubled to " + str(clip.length))
            except RuntimeError:
                pass  # Live refused (clip too long)

    def _do_quantize_clip(self):
        if self._clip_slot and self._clip_slot.has_clip:
            clip = self._clip_slot.clip
            assert isinstance(clip, Live.Clip.Clip)
            rate = self._session.record_quantization
            clip.quantize(rate, 1.0)
            self._print("Clip quantized to " + record_quantization_name(rate))

    def _do_delete_clip(self):
        if self._clip_slot and self._clip_slot.has_clip:
            self._clip_slot.delete_clip()
            self._print("Clip deleted")

    def _do_track_arm(self):
        song = self.song()
        track = self._clip_slot.canonical_parent
        if track.can_be_armed and not track.arm:
            if song.exclusive_arm:
                for other in song.tracks:
                    if other.can_be_armed and other.arm:
                        other.arm = False
            track.arm = True
            if song.view.selected_track != track:
                song.view.selected_track = track
        if self._clip_slot.has_clip:
            song.session_record = not song.session_record

    def _do_launch_clip(self, value):
        if not self._session.is_fixed_length_on():
            super()._do_launch_clip(value)
            return
        button = self._launch_button_value.subject  # MATRIX BUTTON
        launch_pressed = value or not button.is_momentary()
        if not self.has_clip():
            self._has_fired_slot = True
        if button.is_momentary():
            if self.has_clip():
                self._clip_slot.clip.set_fire_button_state(value != 0)
            elif value:
                self._fire_with_fixed_length()
        elif launch_pressed:
            if self.has_clip():
                self._clip_slot.fire()
            else:
                self._fire_with_fixed_length()
        if launch_pressed and self.song().select_on_launch:
            self.song().view.highlighted_clip_slot = self._clip_slot
            self.application().view.show_view("Detail/Clip")

    def _fire_with_fixed_length(self):
        session = self._session
        self._clip_slot.fire(record_length=session.get_fixed_length(), launch_quantization=session.get_launch_quant())

    def _feedback_value(self):
        value = super()._feedback_value()
        if self._clip_slot and value == "ProSession.ClipStopped":
            track = self._clip_slot.canonical_parent
            if track.is_foldable:
                return "ProSession.ClipUnFoldedTrack" if track.fold_state == 0 else "ProSession.ClipFoldedTrack"
        return self._in_clip_colour(value)

    def _in_clip_colour(self, value):
        """With Settings.SESSION__CLIP_COLOR_WHEN_PLAYING on an RGB Launchpad (the session set a clip
        colour table), a triggered clip blinks and a playing one pulses in its own colour."""
        if not Settings.SESSION__CLIP_COLOR_WHEN_PLAYING or self._clip_rgb_table is None:
            return value
        if self._clip_slot is None or not self.has_clip():
            return value
        if value == self._started_value:
            return Pulse(self._color_value(self._clip_slot.clip.color))
        if value == self._triggered_to_play_value:
            return Blink(self._color_value(self._clip_slot.clip.color))
        return value

    def _print(self, msg):
        self._session._print(str(msg))
