"""Regression tests: the parser must not crash on malformed CSI input.

These cover the crashes reported in issue #209 ("Various parser crashes on
random input") and related reports: surplus CSI parameters, a private marker on
a command with no private form, an unsupported erase mode, and a non-ASCII
"digit" in a parameter. Feeding any of these must not raise out of ``feed()``.
"""
import pyte


def feed(data):
    screen = pyte.Screen(10, 5)
    pyte.Stream(screen).feed(data)
    return screen


def test_surplus_csi_parameters_do_not_crash():
    # More parameters than the handler accepts (#209): cursor_up(1, 2) etc.
    feed("\x1b[1;2A")
    feed("\x1b[1;2;3H")
    feed("\x1b[0;0@")


def test_private_marker_on_plain_command_does_not_crash():
    # "?" private marker on a command with no private form (#209, #126, #67).
    feed("\x1b[?0A")
    feed("\x1b[?0@")
    feed("\x1b[?0r")


def test_unsupported_erase_mode_is_noop():
    # erase_in_line / erase_in_display with an out-of-range ``how``.
    screen = pyte.Screen(5, 1)
    screen.draw("abcde")
    screen.erase_in_line(3)
    assert "".join(screen.buffer[0][x].data for x in range(5)) == "abcde"
    feed("\x1b[3K")
    feed("\x1b[4J")


def test_non_ascii_digit_parameter_does_not_crash():
    # str.isdigit() accepts superscripts that int() rejects (#209).
    feed("\x1b[\u00b3A")   # superscript three
    feed("\x1b[1\u00b2B")  # superscript two after an ASCII digit


def test_valid_sequences_still_work():
    # The hardening must not change behaviour for well-formed input.
    screen = feed("\x1b[3B\x1b[2C")
    assert (screen.cursor.x, screen.cursor.y) == (2, 3)
    screen = feed("\x1b[?25l")           # hide cursor (valid private mode)
    assert screen.cursor.hidden is True
