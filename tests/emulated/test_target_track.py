"""TargetTrackComponent (pro session recording): the armed MIDI tracks, last armed first."""
from harness.devices import LaunchpadX
from harness.rig import make_song


def target(rig):
	return rig.selector._session._session_record._target_track_component


def test_tracks_armed_at_start_are_in_the_stack(make_rig):
	song = make_song()
	song.tracks[2].arm = True
	rig = make_rig(LaunchpadX, song=song)
	assert target(rig)._armed_track_stack == [song.tracks[2]]
	assert target(rig).target_track is song.tracks[2]


def test_arming_and_disarming_follows_the_last_armed_track(make_rig):
	rig = make_rig(LaunchpadX)
	tracks = rig.song.tracks
	tracks[1].arm = True
	tracks[3].arm = True
	assert target(rig).target_track is tracks[3]
	tracks[3].arm = False
	assert target(rig).target_track is tracks[1]


def test_each_instance_has_its_own_stack(make_rig):
	first = make_rig(LaunchpadX)
	first.song.tracks[1].arm = True
	second = make_rig(LaunchpadX)
	assert target(first)._armed_track_stack is not target(second)._armed_track_stack
	assert second.song.tracks[1] not in target(second)._armed_track_stack


def test_removed_tracks_leave_the_stack(make_rig):
	song = make_song()
	song.tracks[1].arm = True
	song.tracks[2].arm = True
	rig = make_rig(LaunchpadX, song=song)
	component = target(rig)
	component._refresh_armed_track_stack([])
	assert component._armed_track_stack == []
