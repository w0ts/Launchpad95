"""Find the drum rack a track plays (its instrument, or the first one inside its rack chains)."""

import Live
from _Framework.Util import find_if


def find_drum_group_device(track_or_chain):
    """The drum rack of the first instrument in ``track_or_chain``, searched through rack
    chains, or None."""
    device = find_if(lambda d: d.type == Live.Device.DeviceType.instrument, track_or_chain.devices)
    if device:
        if device.can_have_drum_pads:
            return device
        if device.can_have_chains:
            return find_if(bool, map(find_drum_group_device, device.chains))
    return None


def drum_rack_of(track):
    """The track's drum rack if it has pads, else None (also for no track)."""
    if track == None or not track.devices:
        return None
    device = find_drum_group_device(track)
    if device != None and device.can_have_drum_pads and device.has_drum_pads:
        return device
    return None
