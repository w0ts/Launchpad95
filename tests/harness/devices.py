"""Emulated Launchpads: they answer the script's handshake, turn button presses into the
MIDI the hardware sends, and decode the LED state from the MIDI the script sends.

Coordinates: grid ``(x, y)`` with x = column 0..7 left to right, y = row 0..7 top to
bottom. ``top(i)`` is the i-th round button above the grid (up, down, left, right,
session, user1, user2, mixer), ``side(i)`` the i-th button right of the grid, top first.
"""
from collections import deque

import Live

NOTE_ON = 0x90
CC = 0xB0
SYSEX_START = 0xF0
SYSEX_END = 0xF7

IDENTITY_REQUEST = (240, 126, 127, 6, 1, 247)
MK2_CHALLENGE_HEADER = (240, 0, 32, 41, 2, 24, 64)

# LED channels of the RGB models: 0 = static colour, 1 = flashing, 2 = pulsing.
STATIC, FLASH, PULSE = 0, 1, 2


class Led:
	"""The state of one LED: the static value, and the flash/pulse value if any."""

	def __init__(self):
		self.static = None
		self.flash = None
		self.pulse = None
		self.channel = None

	def apply(self, channel, value):
		self.channel = channel
		if channel == FLASH:
			self.flash = value
		elif channel == PULSE:
			self.pulse = value
		else:
			self.static = value
			self.flash = None
			self.pulse = None

	@property
	def value(self):
		for value in (self.pulse, self.flash, self.static):
			if value is not None:
				return value
		return None

	def __repr__(self):
		return f"Led(static={self.static!r}, flash={self.flash!r}, pulse={self.pulse!r})"


class EmulatedLaunchpad:
	"""Common behaviour; subclasses give the MIDI layout and the handshake."""

	name = "Launchpad"
	loaded_log = None
	top_status = CC
	side_status = NOTE_ON

	def __init__(self):
		self.outbox = deque()
		self.leds = {}
		self.received = []
		self.answered_handshake = False

	# -- layout
	def grid_identifier(self, x, y):
		raise NotImplementedError

	def top_identifier(self, index):
		raise NotImplementedError

	def side_identifier(self, index):
		raise NotImplementedError

	def _message(self, status, identifier, value, channel=0):
		return (status | channel, identifier, value)

	# -- input (what the user does)
	def grid_message(self, x, y, velocity=127):
		return self._message(NOTE_ON, self.grid_identifier(x, y), velocity)

	def top_message(self, index, value=127):
		return self._message(self.top_status, self.top_identifier(index), value)

	def side_message(self, index, value=127):
		return self._message(self.side_status, self.side_identifier(index), value)

	# -- output (what the script sends us)
	def receive(self, midi_bytes):
		self.received.append(midi_bytes)
		if midi_bytes[0] == SYSEX_START:
			self.receive_sysex(midi_bytes)
			return
		status = midi_bytes[0] & 0xF0
		channel = midi_bytes[0] & 0x0F
		if status in (NOTE_ON, CC) and len(midi_bytes) == 3:
			self.receive_short(status, channel, midi_bytes[1], midi_bytes[2])

	def receive_short(self, status, channel, identifier, value):
		self.leds.setdefault((status, identifier), Led()).apply(channel, value)

	def receive_sysex(self, midi_bytes):
		pass

	def answer(self, midi_bytes):
		self.answered_handshake = True
		self.outbox.append(tuple(midi_bytes))

	# -- LED access
	def _led(self, status, identifier):
		return self.leds.get((status, identifier), Led())

	def grid_led(self, x, y):
		return self._led(NOTE_ON, self.grid_identifier(x, y))

	def top_led(self, index):
		return self._led(self.top_status, self.top_identifier(index))

	def side_led(self, index):
		return self._led(self.side_status, self.side_identifier(index))

	def led(self, x, y):
		"""Colour value of grid button (x, y) (flash/pulse value wins over static)."""
		return self.grid_led(x, y).value

	def grid_values(self):
		return [[self.led(x, y) for x in range(8)] for y in range(8)]


class LaunchpadMK1(EmulatedLaunchpad):
	"""Launchpad, Launchpad S and Launchpad Mini (MK1/MK2 Mini): notes row * 16 + column."""

	name = "Launchpad MK1"
	loaded_log = "LaunchPad95 (classic) Loaded !"
	flags = dict(_mk2_rgb=False, _mk3_rgb=False, _lpx=False)

	def __init__(self):
		super().__init__()
		self._challenge_bytes = {}
		self.config_values = []

	def grid_identifier(self, x, y):
		return y * 16 + x

	def top_identifier(self, index):
		return 104 + index

	def side_identifier(self, index):
		return index * 16 + 8

	def receive_short(self, status, channel, identifier, value):
		if status == CC and 17 <= identifier <= 20:
			self._challenge_bytes[identifier - 17] = value
			if len(self._challenge_bytes) == 4:
				challenge = sum(self._challenge_bytes[i] << (8 * i) for i in range(4))
				self._challenge_bytes = {}
				response = Live.Application.encrypt_challenge2(challenge)
				self.answer((240, 0, 32, 41, 6, response & 0x7F, (response >> 8) & 0x7F, 247))
			return
		if status == CC and identifier == 0:
			self.config_values.append(value)
			return
		super().receive_short(status, channel, identifier, value)


class _RGBLaunchpad(EmulatedLaunchpad):
	def grid_identifier(self, x, y):
		return 81 - 10 * y + x


class LaunchpadMK2(_RGBLaunchpad):
	name = "Launchpad MK2"
	loaded_log = "LaunchPad95 (mk2) Loaded !"
	flags = dict(_mk2_rgb=True, _mk3_rgb=False, _lpx=False)
	# Identity reply of a Launchpad MK2 (family code 0x69); not used by the script.
	identity_reply = (240, 126, 0, 6, 2, 0, 32, 41, 105, 0, 0, 0, 0, 1, 7, 9, 247)

	def top_identifier(self, index):
		return 104 + index

	def side_identifier(self, index):
		return 89 - 10 * index

	def receive_sysex(self, midi_bytes):
		if midi_bytes == IDENTITY_REQUEST:
			self.answer(self.identity_reply)
		elif midi_bytes[:7] == MK2_CHALLENGE_HEADER and len(midi_bytes) == 12:
			challenge = sum(midi_bytes[7 + i] << (8 * i) for i in range(4))
			response = Live.Application.encrypt_challenge2(challenge)
			self.answer(MK2_CHALLENGE_HEADER + (response & 0x7F, (response >> 8) & 0x7F, 247))


class _ProgrammerModeLaunchpad(_RGBLaunchpad):
	"""Launchpad X and Mini MK3: identity reply, then programmer mode via sysex."""

	top_status = CC
	side_status = CC
	device_id = None
	family = None

	def __init__(self):
		super().__init__()
		self.sysex_commands = []

	@property
	def identity_reply(self):
		# Firmware bytes after the family/model codes are plausible values, not captured ones.
		return (240, 126, 0, 6, 2, 0, 32, 41) + self.family + (0, 0, 0, 4, 2, 0, 247)

	def top_identifier(self, index):
		return 91 + index

	def side_identifier(self, index):
		return 89 - 10 * index

	def receive_sysex(self, midi_bytes):
		if midi_bytes == IDENTITY_REQUEST:
			self.answer(self.identity_reply)
		elif midi_bytes[:6] == (240, 0, 32, 41, 2, self.device_id):
			self.sysex_commands.append(midi_bytes[6:-1])

	@property
	def in_programmer_mode(self):
		modes = [cmd[1] for cmd in self.sysex_commands if cmd[0] == 14]
		return bool(modes) and modes[-1] == 1


class LaunchpadX(_ProgrammerModeLaunchpad):
	name = "Launchpad X"
	loaded_log = "LaunchPad95 (LPX) Loaded !"
	flags = dict(_mk2_rgb=False, _mk3_rgb=False, _lpx=True)
	device_id = 12
	family = (3, 1)


class LaunchpadMiniMK3(_ProgrammerModeLaunchpad):
	name = "Launchpad Mini MK3"
	loaded_log = "LaunchPad95 (mk3) Loaded !"
	flags = dict(_mk2_rgb=False, _mk3_rgb=True, _lpx=False)
	device_id = 13
	family = (19, 1)


ALL_MODELS = (LaunchpadMK1, LaunchpadMK2, LaunchpadMiniMK3, LaunchpadX)
