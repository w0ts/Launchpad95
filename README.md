# Launchpad95

**An improved Novation Launchpad script for Ableton Live**

**Play, sequence and tweak from the grid.** Launchpad95 keeps everything Live's own Launchpad scripts do and adds an
instrument mode with scales, two step sequencers to edit MIDI clips, a device controller and a pro session mode.

**Nothing else to install.** It is a plain Live control surface script in Python: no Max for Live needed (an optional
Max for Live on-screen display is included for Suite users).

> ## [→ w0ts.github.io/Launchpad95](https://w0ts.github.io/Launchpad95/)
> **The manual, with every mode drawn button by button: on the site.**

---

## What it does

* **Instrument Controller** — the grid becomes a keyboard: a drum rack layout, or a melodic layout in any of Live's
  scales, in 4ths, 3rds, sequent, chromatic or chromatic guitar layout. Key and scale follow Live's clip scales.
* **Quick scales and note repeat** — change root, scale or mode from the top two rows while you play, and turn on
  note repeat with swing.
* **Drum step sequencer** — edit a MIDI clip on the grid, in a combined mode close to Push's or a multinote mode with
  one note per row, with velocity, mute, loop and clip duplication shortcuts.
* **Melodic step sequencer** — a hardware-style sequencer: pitch, velocity, length and octave pages, mono or poly,
  in the selected scale.
* **Device Controller** — eight parameters of any device at once, as sliders, lists or switches, with precision and
  stepless (velocity-sensitive) sliders and four device lock slots.
* **Pro Session** — shift, tempo, quantize, duplicate, delete and record modifiers on the scene buttons, from
  [Launchpad97](https://github.com/poltow/Launchpad97).
* **Session and mixer modes** as in Live's own scripts, with configurable volume levels.

Supported: Launchpad (MK1), Launchpad S, Launchpad Mini, Launchpad MK2, Launchpad Mini MK2, Launchpad Mini MK3 and
Launchpad X. The Launchpad Pro has its own script, [Launchpad Pro95](https://w0ts.github.io/Launchpad_Pro95/).

---

## Install

You need **Ableton Live 11 or later** (Mac or Windows). For Live 9 and 10, use the
[archived Live 9/10 release](https://github.com/w0ts/Launchpad95/releases/tag/legacy-live9-10).

1. Download [Launchpad95.zip](https://github.com/w0ts/Launchpad95/releases/latest/download/Launchpad95.zip) (the
   [latest release](https://github.com/w0ts/Launchpad95/releases/latest)) and unzip it.
2. Copy the `Launchpad95` folder into your Live User Library, in a folder named `Remote Scripts`
   (`User Library/Remote Scripts/Launchpad95/`).
3. Restart Live, open **Settings → Link, Tempo & MIDI**, choose **Launchpad95** as a Control Surface and your
   Launchpad as Input and Output. On a Launchpad X or Mini MK3 pick the **MIDI** port (`LPX MIDI`,
   `LPMiniMK3 MIDI`), not the DAW port.
4. Turn on **Track**, **Sync** and **Remote** for the Launchpad ports in the MIDI Ports list.

Step by step, with pictures and a F.A.Q.: [the manual](https://w0ts.github.io/Launchpad95/#install). Options (user
modes, stepless sliders, volume levels, …) are in `Settings.py`.

What changed in each version: [CHANGELOG.md](CHANGELOG.md).

---

## Development

The tests run the script outside Live, against a fake Live API and emulated Launchpads, with Python 3.11 (the Python of
Live 11+); CI runs them with ruff and black on every push. How to run them and where Ableton's `_Framework` comes
from: [tests/README.md](tests/README.md). The manual's source is `site/`, published by
`.github/workflows/pages.yml`.

Bug reports and suggestions: [GitHub issues](https://github.com/w0ts/Launchpad95/issues).

---

## Licence and attribution

GPL-3.0, see [LICENSE](LICENSE).

Launchpad95 is by w0ts. It started from Ableton's Launchpad control surface scripts, and grew with contributions from
Daniel Erceg, Pablo Torres ([Poltow](https://github.com/poltow), Pro Session and note repeat), Thomas Frössman,
MrMatch246 (stepless sliders, clip scales) and others: see the commit history.

## Not affiliated with Novation or Ableton

Launchpad95 is an independent project, not made or endorsed by Novation (Focusrite) or Ableton. Launchpad is a trademark
of Focusrite Audio Engineering; Ableton and Live are trademarks of Ableton AG.
