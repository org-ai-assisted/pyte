"""Regression: HistoryScreen.after_event must not mutate a line while iterating.

after_event() trims cells whose column index exceeds the (possibly reduced)
screen width when paging. It used to do `for x in line: ... line.pop(x)`,
which raises `RuntimeError: dictionary changed size during iteration` as soon
as one cell needs trimming -- reachable when a wider line captured in history
is paged back in after the screen was resized to fewer columns.
"""
import pyte


def test_paging_after_shrink_does_not_crash():
    screen = pyte.HistoryScreen(10, 3, history=20)
    stream = pyte.Stream(screen)
    for _ in range(8):
        stream.feed("ABCDEFGHIJ\r\n")   # 10-wide lines scroll into history.top
    screen.resize(lines=3, columns=4)    # shrink; history lines stay 10-wide
    screen.prev_page()                   # pages a wide line back -> after_event trims
    # No crash, and no cell beyond the new width survives on screen.
    for line in screen.buffer.values():
        assert all(x <= screen.columns for x in line)


def test_after_event_trims_overflow_cells_directly():
    screen = pyte.HistoryScreen(4, 2, history=10)
    # Plant a cell past the current width, then trigger the paging trim.
    screen.buffer[0][9] = screen.default_char._replace(data="X")
    screen.after_event("prev_page")
    assert 9 not in screen.buffer[0]
