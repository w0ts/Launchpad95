# Changelog

All notable changes to Launchpad95, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/).
Releases before 2026 had no version numbers and are listed by date. The manual is on
[w0ts.github.io/Launchpad95](https://w0ts.github.io/Launchpad95/).

## [Unreleased]

The project moves to [w0ts](https://w0ts.github.io/): repository [w0ts/Launchpad95](https://github.com/w0ts/Launchpad95),
manual on [w0ts.github.io/Launchpad95](https://w0ts.github.io/Launchpad95/).

### Changed

- **Live 11 or later is required.** The step sequencers read and write clip notes with the note API Live 11
  introduced: notes they rewrite keep their probability, velocity deviation and release velocity, and newer Lives no
  longer log deprecation warnings for them. Live 9 and 10 users: the
  [archived Live 9/10 release](https://github.com/w0ts/Launchpad95/releases/tag/legacy-live9-10).
- **Python 3 only.** The Python 2 compatibility code is gone (Live 11 and later run Python 3).
- **The device controller runs on Live's main thread.** Its eight columns no longer run in background threads; the
  stepless slides advance with Live's display updates (steps of about 0.1 s instead of 5 ms, the same speed per
  second, and a short tap still changes the value at once).
- The manual moves to [w0ts.github.io/Launchpad95](https://w0ts.github.io/Launchpad95/), with the Launchpad pictures
  redrawn; this change log replaces its History section.

### Fixed

- Melodic step sequencer: it keeps the notes it cannot show (muted notes, notes off its scale lanes or 7 octaves,
  notes before the clip start, extra notes in mono mode) instead of dropping them; long clips work (an error past
  beat 32 at 1/16); a duplicated clip is read again; a song key or scale change no longer raises an error.
- Step sequencers: notes before time 0 were duplicated on every edit; velocity and mute edits in the drum step
  sequencer added a duplicate note; with 2 lines per note the second row played the next pitch.
- Loop selector: setting a loop kept the old end; extending the loop copied from the clip start instead of the loop
  start; in multinote mode with 2 lines per note, auto-scroll showed the wrong page.
- Instrument mode: at the lowest and highest octaves the bottom pads played wrapped-around notes (they are now
  unplayable); a negative origin played a note an octave too high; the note selector picked the wrong note below
  the key; the mode kept following the song scale after you left it.
- Scales: Major, Minor and the pentatonics are found by name in Live's scale list instead of by position; the quick
  scale relative-scale pad turned a pentatonic the wrong way round the circle of fifths.
- Device controller: a locked device controller jumped to the device Live appointed when you selected another
  track; a 9-value list parameter lit a 9th button; next/previous device failed on racks with an empty chain; a device
  change outside device mode switched Live's detail view.
- Pro session: clips in Gate or Legato launch mode now get the pad release; a pad past the last track no longer
  fails; coming back to Session quickly no longer toggles pro session by itself.
- Track controller: next/previous track failed with a return or master track selected; leaving it could clear the
  selected track's arm; the solo and undo buttons failed without a session record button.
- MIDI channels of the user modes follow the mode names, so reordering `USER_MODES_1/2` in `Settings.py` keeps them
  right; the fixed-length + LED and the mixer overview side buttons show the right state; armed tracks are tracked
  per Launchpad.
- The script removes its Live listeners when it is unloaded.

### Added

- An automated test suite (pytest) that runs the script against a fake Live API and emulated Launchpads, and CI on
  GitHub Actions: tests, ruff and black. See [tests/README.md](tests/README.md).

## 2023-11-26

- Stepless faders for device controller are now on by default. Support for live 12

## 2023-09-25

- Added Stepless faders for device controller. Scale and root note are now synced with clip scales in instrument mode and step sequencers. Thanks to MrMatch246

## 2022-10-20

- Added Session Pro mode from Pablo Torres [poltow/Launchpad97](https://github.com/poltow/Launchpad97)

## 2021-04-07

- fixes for backward compatiblity with Live9

## 2021-02-24

- fix for older launchpads + Live11

## 2020-12-16

- Support for Live 11. User mode 1 and 2 are now disabled by default. They can be enabled from Settings.py

## 2020-03-23

- enable RGB session mode on LPX and LPmini MK3

## 2020-01-12

- user customisable mixer volume slider values

## 2019-11-02

- support for Launchpad Mini MK3 and Launchpad X

## 2019-08-26

- documentation fixes. duplicate clip now does not fire it.

## 2017-04-01

- note repeater ! (sub mode of quick scale mode) contribution from Pablo Torres.

## 2016-04-09

- small fixes for mk2. skin improvements

## 2016-03-28

- Launchpad MK2 RGB autodetect. better skinning. merging device mode from launchpad pro95

## 2016-03-02

- Launchpad MK2 RGB support.

## 2015-12-31

- code cleanup, partial and untested support for MK2 RGB, skinning

## 2015-04-03

- save scale in clip in stepseq and instrument mode (off by default, check Settings.py)
- customisable user modes (in Settings.py)
- clean up TrackController

## 2015-02-24

- minor fix for live 9.2 beta 1

## 2015-02-13

- minor fixes

## 2015-01-20

- change: Option to add clip stop buttons moved to Settings.py

## 2015-01-14

- add: added option to add stop buttons at bottom of session (MainSelectorComponent.py:39)

## 2015-01-14

- fix: minor cleanup and bugfixes !

## 2014-12-06

- fix: minor cleanup and bugfixes !

## 2014-10-03

- change: revamped device controller !

## 2014-09-16

- change: minor fixes in melodic stepseq.

## 2014-07-14

- change: double pressing mute button in stepseq holds shift.

## 2014-06-11

- fix: compatibility fix for live 9.1.3b8. should be backward compatible with 9.1.2 fix : minor fixes

## 2014-04-30

- add: m4l OSD/helper. fix : minor fixes in step seq. fix : uniformise scale edition and quick scale

## 2014-03-28

- fix: bugs while in drumrack mode. fix session scene not working while exiting user mode 1. add: relative scale to quick scales, added circle of fifth navigation

## 2014-03-12

- fix: compatibility with max4live in user mode 2. fix midi channels for some modes.
- add: duplicate clip in step seq (hold lock button for 0.5sec).

## 2014-02-27

- major update !
- new melodic step seq !
- preview of notes in combined step seq (hold 7th scene button and play on the note selector in the lower left corner of the matrix)
- quick scale in instrument mode to quickly change scale while playing
- compatibility with live 9.1.1 and 9.1.2 or above.
- various bugs fixes and improvements.

## 2014-01-06

- add: diatonic 3rd and sequent and guitar chromatic modes. fix: implicit arm. change: updated documentation

## 2014-01-06

- fix: track locking in step seq

## 2013-12-16

- fix: led feedback in instrument mode !

## 2013-12-11

- add: improve integration with launchpad95Colour.

## 2013-12-07

- change: change scale colour. minor bugfix.

## 2013-11-18

- fix: improve stepseq lock to a track mode.

## 2013-11-18

- add: long press on the stepseq lock button to lock to a track.

## 2013-11-11

- add: combos to mute, delete and extend clip content in step sequencer

## 2013-10-28

- fix: small bug fixes

## 2013-10-23

- add: add option to compress channels used by launchpad95 to free up channels for other devices

## 2013-10-18

- fix: show device panel while activating device controller. fix led blinking when entering stepseq. properly turn off scene buttons in user modes. add: use clip color palette to blink white clips

## 2013-10-09

- fix: Fix Clip linking in StepSeq. small fixes.

## 2013-09-27

- fix: matrix not fully updated while entering multinote stepseq.

## 2013-09-22

- fix: compatibility with live 9.1 beta. Fix Clip linking in StepSeq.

## 2013-09-02

- fix: fix a few bugs in metronome and clip callback in stepseq

## 2013-08-13

- add: complete rework of the stepseq

## 2013-05-28

- fix note highlighting in StepSeq in hires. various minor fixes in stepseq. Fix UserMode2 (was sending midi notes)

## 2013-05-25

- fix paging StepSeq, add support for selected DrumPad at the highest resolution. fix note feedback when entering instrument mode. add: very long press Arm in instrument mode to toggle implicit track arm

## 2013-05-09

- fix for live 9.0.4: replace overdub by session_record in TrackController. overdub in Python API started to behave strange from 9.0.4.

## 2013-05-04

- add: long press on solo to mute/unmute track in instrument mode. fix: disable implicit arm while leaving instrument mode.

## 2013-04-13

- change : changed some buttons in instrument mode. support for implicit arm.

## 2013-04-13

- add : support for Instrument mode

## 2013-03-13

- fix : fix loop length dec button

## 2013-03-05

- add : Launchpad95 to support Live 9

## 2012-10-21

- change : while extending midi clip, clone existing notes in the newly created portion

## 2012-02-02

- change : fixed midi channels for step sequencer and device controller to avoid conflicts

## 2012-01-22

- add: up/down per octave paging in step sequencer (press and hold mute and press navigation keys) fix:scrolling boundaries

## 2012-01-21

- add: Scale mode. fix: better scrolling in fold and scale mode. change: merged mute shift and mute. changed: merge velocity and velocity shift.

## 2012-01-03

- add: easier to configure metronome and note markers in step sequencer. add: adapted LaunchpadColour (Launchpad85Colour) to this script, for color blind people

## 2012-01-02

- bug fix: improve button response time in step sequencer (was causing problem while pressing multiple buttons at once)

## 2011-12-31

- bug fix: loops longer than 8 blocks were not supported. add : scale marked in step sequencer marking C (3 amber blocks) and A (one amber block)

## 2011-12-29

- bug fix: some buttons not responding correctly in user mode 1

## 2011-12-26

- Improved live integration (shows Device chain/clip editor). fixed crash while loading Live Set

## 2011-12-23

- support for MaxForLive. addition of lock mode in step sequencer. bug fixes. renamed from Launchpad75 to Launchpad85.

## 2011-10-05

- addition mute lane in step sequencer

## 2011-10-01

- addition of device controller

## 2011-08-20

- bug fixes

## 2011-07-22

- first public version

## 2011-05

- working on an initial version
