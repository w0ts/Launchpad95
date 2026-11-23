"""Follow the song's root note and scale (Live 11+) into a ScaleComponent.

Mixin for the components that show a scale: the class says which ScaleComponent follows
the song (``_followed_scale``) and turns the listeners on and off with its own enabled
state."""


class SongScaleListener:
    def _followed_scale(self):
        """The ScaleComponent that follows the song (the component itself by default)."""
        return self

    def _register_scale_listeners(self):
        song = self.song()
        if not song.root_note_has_listener(self.handle_root_note_changed):
            song.add_root_note_listener(self.handle_root_note_changed)
        if not song.scale_name_has_listener(self.handle_scale_name_changed):
            song.add_scale_name_listener(self.handle_scale_name_changed)

    def _remove_scale_listeners(self):
        song = self.song()
        if song.root_note_has_listener(self.handle_root_note_changed):
            song.remove_root_note_listener(self.handle_root_note_changed)
        if song.scale_name_has_listener(self.handle_scale_name_changed):
            song.remove_scale_name_listener(self.handle_scale_name_changed)

    def handle_root_note_changed(self):
        self._followed_scale().set_key(self.song().root_note, False, True)
        self.update()

    def handle_scale_name_changed(self):
        scale = self._followed_scale()
        scale.set_modus(scale._modus_names.index(self.song().scale_name), False, True)
        self.update()
