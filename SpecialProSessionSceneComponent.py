"""Pro session scene: the scene actions its pads trigger with shift and a side button held."""

import Live
from _Framework.SceneComponent import SceneComponent

from .SpecialProSessionClipSlotComponent import SpecialClipSlotComponent


class SpecialSceneComponent(SceneComponent):
    clip_slot_component_type = SpecialClipSlotComponent

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._session = None

    def _set_session(self, session, num_tracks):
        """Wire this scene and its pads to the pro session."""
        self._session = session
        for track_index in range(num_tracks):
            self.clip_slot(track_index)._set_parents(self, session)

    def _do_delete_scene(self, scene_for_overrides):
        try:
            if self._scene:
                song = self.song()
                song.delete_scene(list(song.scenes).index(self._scene))
                self._print("Scene deleted")
        except RuntimeError:
            pass  # Live keeps the last scene

    def _do_duplicate_scene(self):
        try:
            song = self.song()
            song.duplicate_scene(list(song.scenes).index(self._scene))
            self._print("Scene duplicated")
        except (Live.Base.LimitationError, RuntimeError, IndexError):
            pass  # no scene under the pad, or Live refused

    def _do_launch_scene(self, value):
        if value != 0:
            self._scene.fire()
            if self.song().select_on_launch:
                self.song().view.selected_scene = self._scene

    def _do_create_scene(self):
        try:
            song = self.song()
            song.view.selected_scene = song.create_scene(list(song.scenes).index(self._scene) + 1)
            self._print("Create scene " + song.view.selected_scene.name)
        except (Live.Base.LimitationError, RuntimeError, IndexError):
            pass  # no scene under the pad, or Live refused

    def _do_capture_and_insert_scene(self):
        try:
            song = self.song()
            song.view.selected_scene = self._scene
            song.capture_and_insert_scene(Live.Song.CaptureMode.all)
            self._print("Captured to scene " + song.view.selected_scene.name)
        except (Live.Base.LimitationError, RuntimeError, IndexError):
            pass  # no scene under the pad, or Live refused

    def _print(self, msg):
        self._session._print(str(msg))
