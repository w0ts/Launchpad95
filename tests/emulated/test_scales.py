"""The instrument mode's ScaleComponent on a booted surface."""
import pytest


def test_scale_component_pattern_uses_the_octave(make_rig):
	from harness.devices import LaunchpadX

	rig = make_rig(LaunchpadX)
	scale_component = rig.selector._instrument_controller._scales
	scale_component.set_octave(2, message=False)
	assert scale_component.get_pattern().note(0, 0).index == 36
	scale_component.set_octave(3, message=False)
	assert scale_component.get_pattern().note(0, 0).index == 48


@pytest.mark.xfail(strict=True, reason="bug: ScaleComponent.py:49 and InstrumentControllerComponent.py:307 use scale index 14 as Melodic Minor, ScaleComponent.py:419 uses 17; in Live 12's scale order (fake list, from memory) 14 is Harmonic Major")
def test_minor_mode_indexes_name_minor_scales(make_rig):
	from harness.devices import LaunchpadX

	rig = make_rig(LaunchpadX)
	scale_component = rig.selector._instrument_controller._scales
	names = [scale_component._modus_names[i] for i in scale_component._minor_modes]
	assert names == ["Minor", "Harmonic Minor", "Melodic Minor"]
