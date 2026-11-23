"""After disconnect() the script leaves no listener on Live's objects (they outlive it)."""
import pytest

from harness.rig import make_song

SESSION, USER1, USER2, MIXER = 4, 5, 6, 7


def live_objects(song):
	"""The song and the Live objects reachable from it that the script listens to."""
	import Live

	objects = [song, song.view, Live.Application.get_application(), Live.Application.get_application().view]
	for track in tuple(song.tracks) + tuple(song.return_tracks) + (song.master_track,):
		objects += [track, track.view, track.mixer_device] + list(track.mixer_device.sends)
		objects += [track.mixer_device.volume, track.mixer_device.panning]
		for device in track.devices:
			objects += [device] + list(device.parameters)
		for clip_slot in getattr(track, "clip_slots", ()):
			objects.append(clip_slot)
			if clip_slot.clip is not None:
				objects.append(clip_slot.clip)
	objects += list(song.scenes)
	return objects


def script_listeners(song):
	"""(object, event, listener) for every listener whose code is in the script package."""
	found = []
	for obj in live_objects(song):
		listener_set = obj.__dict__.get("_listener_set")
		if listener_set is None:
			continue
		for name, listeners in listener_set._by_name.items():
			for listener in listeners:
				owner = getattr(listener, "__self__", None)
				module = type(owner).__module__ if owner is not None else getattr(listener, "__module__", "")
				if module.startswith(("Launchpad95", "_Framework")):
					found.append((type(obj).__name__, name, getattr(listener, "__qualname__", repr(listener))))
	return found


@pytest.mark.parametrize("taps", [
	(), (SESSION,), (USER1,), (USER1, USER1), (USER2,), (USER2, USER2), (MIXER,),
], ids=["session", "pro session", "instrument", "device", "drum seq", "melodic seq", "mixer"])
def test_disconnect_removes_the_script_listeners(make_rig, model, taps):
	song = make_song(clips=[(0, 0)])
	rig = make_rig(model, song=song)
	for button in taps:
		rig.tap_top(button)
		rig.tick()
	rig.disconnect()
	leaks = script_listeners(song)
	assert leaks == [], "\n".join(map(str, leaks))
