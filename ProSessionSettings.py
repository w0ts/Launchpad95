"""Pro session settings tables: the launch and record quantization rates and the fixed
recording lengths, as the bottom row shows them (pad 0 on/off, 1 down, 2 up, 3-7 one value
each)."""

import Live

_Q = Live.Song.Quantization
Rec_Q = Live.Song.RecordingQuantization

REC_QNTZ_RATES = [
    Rec_Q.rec_q_quarter,
    Rec_Q.rec_q_eight,
    Rec_Q.rec_q_eight_triplet,
    Rec_Q.rec_q_eight_eight_triplet,
    Rec_Q.rec_q_sixtenth,
    Rec_Q.rec_q_sixtenth_triplet,
    Rec_Q.rec_q_sixtenth_sixtenth_triplet,
    Rec_Q.rec_q_thirtysecond,
]
# RecQuant pads 3-7: 1/4, 1/8, 1/8t, 1/16, 1/16t
REC_QNTZ_FIXED_RATES = [
    Rec_Q.rec_q_quarter,
    Rec_Q.rec_q_eight,
    Rec_Q.rec_q_eight_triplet,
    Rec_Q.rec_q_sixtenth,
    Rec_Q.rec_q_sixtenth_triplet,
]
REC_QNTZ_NAMES = ("1/4", "1/8", "1/8t", "1/8+t", "1/16", "1/16t", "1/16+t", "1/32")

LAUNCH_QNTZ_RATES = [
    _Q.q_8_bars,
    _Q.q_4_bars,
    _Q.q_2_bars,
    _Q.q_bar,
    _Q.q_half,
    _Q.q_half_triplet,
    _Q.q_quarter,
    _Q.q_quarter_triplet,
    _Q.q_eight,
    _Q.q_eight_triplet,
    _Q.q_sixtenth,
    _Q.q_sixtenth_triplet,
    _Q.q_thirtytwoth,
]
# LaunchQuant pads 3-7: 2 bars, 1 bar, 1/4, 1/8, 1/16
LAUNCH_QNTZ_FIXED_RATES = [_Q.q_2_bars, _Q.q_bar, _Q.q_quarter, _Q.q_eight, _Q.q_sixtenth]
LAUNCH_QNTZ_NAMES = (
    "8 Bars",
    "4 Bars",
    "2 Bars",
    "1 Bar",
    "1/2",
    "1/2t",
    "1/4",
    "1/4t",
    "1/8",
    "1/8t",
    "1/16",
    "1/16t",
    "1/32",
)

# Fixed recording length in bars (0.25 is one beat); FixedLength pads 3-7.
FIXED_LENGTH_VALUES = [0.25, 1, 2, 4, 8]
MIN_FIXED_LENGTH = 0.25
MAX_FIXED_LENGTH = 31


def step(rates, current, delta):
    """The rate ``delta`` places away from ``current`` in ``rates``, or None at either end."""
    index = rates.index(current) + delta
    return rates[index] if 0 <= index < len(rates) else None


def record_quantization_name(rate):
    return REC_QNTZ_NAMES[REC_QNTZ_RATES.index(rate)]


def launch_quantization_name(rate):
    return LAUNCH_QNTZ_NAMES[LAUNCH_QNTZ_RATES.index(rate)]


def next_fixed_length(length):
    """One bar longer (one beat, two beats, one bar, then whole bars), up to the maximum."""
    if length >= MAX_FIXED_LENGTH:
        return length
    return {0.25: 0.5, 0.5: 1}.get(length, length + 1)


def previous_fixed_length(length):
    if length <= MIN_FIXED_LENGTH:
        return length
    return {0.5: 0.25, 1: 0.5}.get(length, length - 1)
