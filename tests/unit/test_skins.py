"""Every skin colour the script asks for exists in both skins (MK1 and RGB)."""

import ast
import glob
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIN_KEY_CALLS = (
    "set_light",
    "set_on_off_values",
    "send_value",
    "set_empty_value",
    "set_stopped_value",
    "set_started_value",
    "set_triggered_to_play_value",
    "set_triggered_to_record_value",
    "set_recording_value",
    "set_record_button_value",
    "set_stop_clip_value",
    "set_stop_clip_triggered_value",
    "set_selected_value",
    "set_playing_value",
    "set_triggered_value",
    "set_scene_value",
    "set_no_scene_value",
)
SKIN_FILES = ("SkinMK1.py", "SkinMK2.py", "ColorsMK1.py", "ColorsMK2.py")
# Constant tables of skin keys, read through an index (e.g. QUANTIZATION_COLOR_MAP[i]).
KEY_LISTS = ("QUANTIZATION_COLOR_MAP",)


def _string_args(node):
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            yield arg.value


def requested_keys():
    """(file:line, key, single_arg_on_off) for each literal skin key passed to a drawing call."""
    found = []
    for path in sorted(glob.glob(os.path.join(REPO, "*.py"))):
        if os.path.basename(path) in SKIN_FILES:
            continue
        tree = ast.parse(open(path).read())
        for node in ast.walk(tree):
            where = f"{os.path.basename(path)}:{getattr(node, 'lineno', 0)}"
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in SKIN_KEY_CALLS:
                args = list(_string_args(node))
                single = node.func.attr == "set_on_off_values" and len(node.args) == 1
                for key in args:
                    if "." in key:
                        found.append((where, key, single))
            elif isinstance(node, ast.Assign) and any(
                getattr(t, "attr", getattr(t, "id", None)) in KEY_LISTS for t in node.targets
            ):
                for element in getattr(node.value, "elts", ()):
                    found.append((where, element.value, False))
    return found


def dynamic_keys(package):
    """Keys the script builds at run time."""
    settings = package.Settings.Settings
    selector = package.MainSelectorComponent.MainSelectorComponent
    keys = []
    for mode in list(settings.USER_MODES_1) + list(settings.USER_MODES_2):
        name = selector.getSkinName(None, mode)
        keys += [f"Mode.{name}.On", f"Mode.{name}.Off"]
    # NoteEditorComponent: "StepSequencer.NoteEditor.Velocity" + index, 5 velocities.
    keys += [f"StepSequencer.NoteEditor.Velocity{index}" for index in range(5)]
    # TrackControllerComponent: set_on_off_values("Mode." + skin_name), default skin name "Session".
    keys += ["Mode.Session.On", "Mode.Session.Off"]
    # DeviceControllerStripServer custom colours and press-time steps.
    for column in range(8):
        keys += [f"Device.CustomSlider{column}.{part}" for part in ("On", "Off", "Third", "Half")]
    keys += [f"Device.ColorSteps.Step{step}" for step in range(10)]
    return keys


@pytest.fixture(scope="module", params=["SkinMK1", "SkinMK2"])
def skin(request, framework):
    module = sys.modules.get("Launchpad95." + request.param) or __import__(
        "Launchpad95." + request.param, fromlist=["x"]
    )
    return module.make_skin()


def has_key(skin, key):
    from _Framework.Skin import SkinColorMissingError

    try:
        skin[key]
        return True
    except SkinColorMissingError:
        return False


CUSTOM_SLIDER_KEYS = {f"Device.CustomSlider{column}.{part}" for column in range(8) for part in ("Third", "Half")}


def missing_literal_keys(skin):
    missing = set()
    for where, key, single in requested_keys():
        if single:
            ok = has_key(skin, key + ".On") and has_key(skin, key + ".Off")
        else:
            ok = has_key(skin, key)
        if not ok:
            missing.add(f"{where} {key}")
    return missing


def test_the_scan_finds_skin_keys():
    keys = requested_keys()
    assert len(keys) > 100
    assert any(key == "Session.ClipStopped" for _, key, _ in keys)


def test_literal_skin_keys_exist(skin):
    assert missing_literal_keys(skin) == set()


def test_built_skin_keys_exist(skin, framework):
    missing = {key for key in dynamic_keys(framework) if not has_key(skin, key)}
    assert missing == set()


def test_mk1_custom_slider_keys(framework):
    """Used when USE_CUSTOM_DEVICE_CONTROL_COLORS is on."""
    from Launchpad95.SkinMK1 import make_skin

    skin = make_skin()
    assert all(has_key(skin, key) for key in CUSTOM_SLIDER_KEYS)


def test_rgb_custom_slider_keys(framework):
    from Launchpad95.SkinMK2 import make_skin

    skin = make_skin()
    assert all(has_key(skin, key) for key in CUSTOM_SLIDER_KEYS)
