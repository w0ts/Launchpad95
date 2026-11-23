"""Walk a track's devices in the order Live shows them, into and out of rack chains: the
device controller's previous/next device buttons."""

import Live


def next_device(device, track):
    """The device after ``device`` (the first device of ``track`` when there is none)."""
    if device is None:
        return track.devices[0] if len(track.devices) > 0 else None
    if not isinstance(device, Live.Device.Device):
        return None
    if device.can_have_chains and len(device.chains) > 0 and len(device.chains[0].devices) > 0:
        return device.chains[0].devices[0]
    return _next_sibling(device) or _next_from_parent(device)


def previous_device(device, track):
    """The device before ``device`` (the last device of ``track`` when there is none)."""
    if device is None:
        return track.devices[-1] if len(track.devices) > 0 else None
    if not isinstance(device, Live.Device.Device):
        return None
    previous_sibling = _previous_sibling(device)
    if previous_sibling:
        return _last_in_chain(previous_sibling)
    if device.canonical_parent and isinstance(device.canonical_parent, Live.Chain.Chain):
        return device.canonical_parent.canonical_parent
    return _previous_from_parent(device)


def _next_sibling(device):
    parent = device.canonical_parent
    if isinstance(parent, Live.Chain.Chain):
        devices = parent.devices
        index = list(devices).index(device)
        if index + 1 < len(devices):
            return devices[index + 1]
        if isinstance(parent.canonical_parent, Live.Device.Device):
            return _next_sibling(parent.canonical_parent)
    return None


def _previous_sibling(device):
    parent = device.canonical_parent
    if isinstance(parent, Live.Chain.Chain):
        devices = parent.devices
        index = list(devices).index(device)
        if index > 0:
            return devices[index - 1]
    return None


def _last_in_chain(device):
    if not isinstance(device, Live.Device.Device):
        return None
    if device.can_have_chains and len(device.chains) > 0 and len(device.chains[-1].devices) > 0:
        return _last_in_chain(device.chains[-1].devices[-1])
    return device


def _next_from_parent(device):
    parent = device.canonical_parent
    if isinstance(parent, Live.Chain.Chain):
        parent_device = parent.canonical_parent
        if isinstance(parent_device, Live.Device.Device):
            return _next_sibling(parent_device) or _next_from_parent(parent_device)
    elif isinstance(parent, Live.Track.Track):
        devices = list(parent.devices)
        if device in devices and devices.index(device) < len(devices) - 1:
            return devices[devices.index(device) + 1]
    return None


def _previous_from_parent(device):
    parent = device.canonical_parent
    if isinstance(parent, Live.Chain.Chain):
        return parent.canonical_parent
    if isinstance(parent, Live.Track.Track):
        devices = list(parent.devices)
        if device in devices and devices.index(device) > 0:
            return _last_in_chain(devices[devices.index(device) - 1])
    return None
