"""Read and write all notes of a MIDI clip, on any Live version.

Live 11+ has the extended note API (get_all_notes_extended / get_notes_extended,
remove_notes_extended, add_new_notes); the old calls (get_selected_notes,
replace_selected_notes) are deprecated there. Older Lives only have the old calls.

Both paths exchange notes as the old tuple format the step sequencers use:
(pitch, time, duration, velocity, mute).
"""

# Large enough to cover any clip; the extended API takes a time range.
_ALL_TIME_START = 0.0
_ALL_TIME_SPAN = 1.0e7
_ALL_PITCHES = (0, 128)

# Per-note attributes that the old tuple format cannot carry (Live 11+).
_EXTRA_ATTRIBUTES = ("probability", "velocity_deviation", "release_velocity")


def has_extended_api(clip):
	return hasattr(clip, "get_notes_extended") and hasattr(clip, "add_new_notes")


def _fetch_extended(clip):
	if hasattr(clip, "get_all_notes_extended"):
		return clip.get_all_notes_extended()
	return clip.get_notes_extended(_ALL_PITCHES[0], _ALL_PITCHES[1], _ALL_TIME_START, _ALL_TIME_SPAN)


def _note_key(pitch, time):
	return (int(pitch), round(float(time), 6))


def _extras_of(clip):
	"""Map (pitch, time) -> extra attributes of the notes currently in the clip."""
	extras = {}
	for note in _fetch_extended(clip):
		values = {}
		for name in _EXTRA_ATTRIBUTES:
			if hasattr(note, name):
				values[name] = getattr(note, name)
		extras[_note_key(note.pitch, note.start_time)] = values
	return extras


def read_all_notes(clip):
	"""Return every note of the clip as a tuple of (pitch, time, duration, velocity, mute)."""
	if has_extended_api(clip):
		return tuple(
			(note.pitch, note.start_time, note.duration, note.velocity, note.mute)
			for note in _fetch_extended(clip))
	clip.select_all_notes()
	notes = clip.get_selected_notes()
	clip.deselect_all_notes()
	return notes


def _default_spec_factory():
	import Live
	return Live.Clip.MidiNoteSpecification


def write_all_notes(clip, notes, spec_factory=None):
	"""Replace every note of the clip with notes, given as (pitch, time, duration, velocity, mute).

	On Live 11+, notes that already existed at the same pitch and time keep their
	probability, velocity deviation and release velocity.
	"""
	notes = tuple(tuple(note) for note in notes)
	if not has_extended_api(clip):
		clip.select_all_notes()
		clip.replace_selected_notes(notes)
		clip.deselect_all_notes()
		return
	if spec_factory is None:
		spec_factory = _default_spec_factory()
	extras = _extras_of(clip)
	specs = tuple(
		spec_factory(
			pitch=int(pitch), start_time=float(time), duration=float(duration),
			velocity=float(velocity), mute=bool(mute),
			**extras.get(_note_key(pitch, time), {}))
		for (pitch, time, duration, velocity, mute) in notes)
	clip.remove_notes_extended(_ALL_PITCHES[0], _ALL_PITCHES[1], _ALL_TIME_START, _ALL_TIME_SPAN)
	if specs:
		clip.add_new_notes(specs)
