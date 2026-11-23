"""Rig: a fake Live song, a FakeCInstance, an emulated Launchpad and the Launchpad95 script,
wired together the way Live wires them.

Lifecycle (as in Live): create_instance(c_instance) -> build_midi_map -> refresh_state ->
update_display ticks. The script asks for the device's identity a few ticks after
refresh_state; the emulated device answers on the next tick, and the script then builds
its components.

MIDI routing (as in Live): a message from the device is first translated (note/CC
translations set by the script during build_midi_map), then goes to the script if it is
forwarded in the current MIDI map, moves a parameter if it is mapped, and otherwise goes
to the tracks as instrument input (recorded in ``track_input``).
"""

import importlib

import Live
from Live.MidiMap import CC as MAP_CC
from Live.MidiMap import NOTE as MAP_NOTE
from Live.MidiMap import MidiMapHandle

from .c_instance import FakeCInstance
from .clock import TICK_SECONDS, FakeTime

PACKAGE_NAME = "Launchpad95"
BOOT_TICKS = 20
MAX_REBUILDS = 10


def make_song(clips=(), **k):
    """A Song; ``clips`` lists (track, scene) slots that get a 4-beat MIDI clip."""
    song = Live.Song.Song(**k)
    for track, scene in clips:
        song.tracks[track].clip_slots[scene].set_clip(Live.Clip.Clip(length=4.0))
    return song


class Rig:
    def __init__(self, device, song=None, clock=None):
        self.song = song if song is not None else make_song()
        Live.Application.set_document(self.song)
        self.application = Live.Application.get_application()
        self.device = device
        self.c_instance = FakeCInstance(self.song, on_midi=self.device.receive)
        self.midi_map = None
        self.track_input = []
        self.surface = None
        self.rebuilds = 0
        self.clock = clock if clock is not None else FakeTime()

    # -- lifecycle
    def create(self):
        package = importlib.import_module(PACKAGE_NAME)
        self.surface = package.create_instance(self.c_instance)
        self.rebuild_midi_map()
        self.surface.refresh_state()
        return self.surface

    def boot(self, ticks=BOOT_TICKS):
        self.create()
        self.tick(ticks)
        return self.surface

    def disconnect(self):
        if self.surface is not None:
            surface, self.surface = self.surface, None
            surface.disconnect()

    # -- time
    def tick(self, count=1):
        for _ in range(count):
            self.clock.advance(TICK_SECONDS)
            self._deliver_outbox()
            self.settle()
            self.surface.update_display()
            self.settle()

    def wait(self, seconds):
        """Let time pass, ticking like Live does (every 100 ms)."""
        self.tick(max(1, int(round(seconds / TICK_SECONDS))))

    def settle(self):
        """Rebuild the MIDI map while the script asks for it (Live does it after each call)."""
        for _ in range(MAX_REBUILDS):
            if not self.c_instance.rebuild_requested:
                return
            self.rebuild_midi_map()
        raise AssertionError("The script keeps requesting MIDI map rebuilds")

    def rebuild_midi_map(self):
        self.c_instance.rebuild_requested = False
        self.c_instance.clear_translations()
        self.midi_map = MidiMapHandle()
        self.surface.build_midi_map(self.midi_map)
        self.rebuilds += 1

    def _deliver_outbox(self):
        while self.device.outbox:
            self.surface.receive_midi(self.device.outbox.popleft())

    # -- input
    def send(self, midi_bytes):
        """A message from the device, routed as Live routes it."""
        midi_bytes = tuple(midi_bytes)
        if midi_bytes[0] == 0xF0:
            self.surface.receive_midi(midi_bytes)
            self.settle()
            return "script"
        status, channel = midi_bytes[0] & 0xF0, midi_bytes[0] & 0x0F
        kind = MAP_NOTE if status in (0x80, 0x90) else MAP_CC
        translations = self.c_instance.note_translations if kind == MAP_NOTE else self.c_instance.cc_translations
        identifier, channel = translations.get((midi_bytes[1], channel), (midi_bytes[1], channel))
        routed = (status | channel, identifier, midi_bytes[2])
        if self.midi_map.is_forwarded(kind, channel, identifier):
            self.surface.receive_midi(routed)
            self.settle()
            return "script"
        parameter = self.midi_map.mappings.get((kind, channel, identifier))
        if parameter is not None:
            span = parameter.max - parameter.min
            parameter.value = parameter.min + span * routed[2] / 127.0
            return "parameter"
        self.track_input.append(routed)
        return "track"

    def press(self, x, y, velocity=127):
        return self.send(self.device.grid_message(x, y, velocity))

    def release(self, x, y):
        return self.send(self.device.grid_message(x, y, 0))

    def tap(self, x, y, velocity=127):
        self.press(x, y, velocity)
        return self.release(x, y)

    def press_top(self, index):
        return self.send(self.device.top_message(index, 127))

    def release_top(self, index):
        return self.send(self.device.top_message(index, 0))

    def tap_top(self, index):
        self.press_top(index)
        return self.release_top(index)

    def press_side(self, index):
        return self.send(self.device.side_message(index, 127))

    def release_side(self, index):
        return self.send(self.device.side_message(index, 0))

    def tap_side(self, index):
        self.press_side(index)
        return self.release_side(index)

    # -- inspection
    @property
    def log(self):
        return self.c_instance.log

    @property
    def messages(self):
        return self.c_instance.messages

    @property
    def selector(self):
        return self.surface._selector
