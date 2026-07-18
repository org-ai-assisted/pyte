"""Regression: VPA / DSR under DECOM with no scrolling margins must not crash.

When origin mode (DECOM) is enabled but no DECSTBM has set a scrolling region,
``self.margins`` is ``None``. ``cursor_to_line`` (VPA) and
``report_device_status`` (DSR, cursor-position report) used to dereference
``self.margins.top`` behind only an ``assert``, crashing with AssertionError
(or AttributeError under ``python -O``). ``cursor_position`` already handled
this; these two now do too.
"""
import pyte
from pyte import modes as mo


def test_vpa_under_decom_without_margins():
    pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[?6h\x1b[5d")


def test_dsr_under_decom_without_margins():
    pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[?6h\x1b[6n")


def test_cursor_to_line_decom_no_margins_direct():
    screen = pyte.Screen(10, 5)
    screen.set_mode(mo.DECOM)          # DECOM on, margins still None
    screen.cursor_to_line(3)
    assert 0 <= screen.cursor.y < screen.lines


def test_dsr_reports_cursor_under_decom_with_margins():
    # With a real scrolling region, DECOM still offsets the report correctly.
    seen = []
    screen = pyte.Screen(10, 24)
    screen.write_process_input = seen.append
    screen.set_margins(3, 20)
    screen.set_mode(mo.DECOM)
    screen.cursor_position(2, 4)
    screen.report_device_status(6)
    assert seen and seen[-1].endswith("R")
