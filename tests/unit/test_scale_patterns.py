"""ScaleComponent's pure parts: Modus (scales from the song's scale list) and MelodicPattern
(which note each pad of the instrument grid plays)."""

import pytest

MAJOR = [0, 2, 4, 5, 7, 9, 11]


@pytest.fixture(scope="module")
def scales(framework):
    from Launchpad95 import ScaleComponent

    return ScaleComponent


def test_modes_come_from_lives_scale_list(scales):
    import Live

    names = scales.MUSICAL_MODES[0::2]
    assert names == [name for name, _ in Live.Song.get_all_scales_ordered()]
    assert scales.MUSICAL_MODES[1] == MAJOR


def test_modus_transposes_to_a_key(scales):
    major = scales.Modus("Major", MAJOR)
    d_major = major.scale(2)
    assert d_major.name == "D"
    assert d_major.notes == [2, 4, 6, 7, 9, 11, 13]
    assert [s.name for s in major.scales([0, 7])] == ["C", "G"]


def pattern(scales, **k):
    k.setdefault("scale", MAJOR)
    k.setdefault("base_note", 48)
    return scales.MelodicPattern(**k)


def test_diatonic_rows_step_by_the_interval(scales):
    p = pattern(scales, steps=[1, 3], origin=[0, 0])
    assert p.note(0, 0).index == 48 and p.note(0, 0).root
    assert p.note(1, 0).index == 50  # next scale degree to the right
    assert p.note(0, 1).index == 53  # three degrees up per row (a fourth)
    assert p.note(7, 0).index == 60 and p.note(7, 0).root  # octave after 7 degrees
    assert p.note(2, 0).highlight  # the third


def test_diatonic_ns_rows_are_octaves(scales):
    p = pattern(scales, steps=[1, 3], origin=[0, 0], diatonic_ns_mode=True)
    assert p.note(0, 1).index == 60


def test_chromatic_rows_are_fourths(scales):
    p = pattern(scales, steps=[1, 3], origin=[0, 0], chromatic_mode=True)
    assert p.note(1, 0).index == 49
    assert not p.note(1, 0).in_scale
    assert p.note(0, 1).index == 53


def test_guitar_layout_has_the_b_string_shift(scales):
    p = pattern(scales, steps=[1, 3], origin=[0, 0], chromatic_mode=True, chromatic_gtr_mode=True)
    assert p.note(0, 4).index - p.note(0, 3).index == 4  # major third between G and B strings
    assert p.note(0, 3).index - p.note(0, 2).index == 5


def test_notes_stay_in_midi_range(scales):
    p = pattern(scales, steps=[1, 3], origin=[0, 0], base_note=96)
    indexes = [p.note(x, y).index for x in range(8) for y in range(8)]
    assert all(index is None or 0 <= index < 128 for index in indexes)


def test_negative_origin_goes_down_an_octave(scales):
    p = pattern(scales, steps=[1, 3], origin=[-1, 0])
    assert p.note(0, 0).index == 47  # one degree below C3: B2


def test_notes_outside_midi_range_are_no_note(scales):
    low = pattern(scales, steps=[1, 3], origin=[0, 0], base_note=-24)
    assert low.note(0, 0).index is None
    assert not low.note(0, 0).valid
    high = pattern(scales, steps=[1, 3], origin=[0, 0], base_note=120)
    assert high.note(7, 0).index is None
