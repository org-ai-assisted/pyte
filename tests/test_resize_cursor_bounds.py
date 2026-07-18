"""Regression: resize() must keep the cursor within the new bounds.

Shrinking the screen used to leave the cursor below the new bottom line (or
right of the new last column), because restore_cursor()'s ensure_?bounds() ran
against the OLD geometry and the column-shrink path never re-clamped. A draw()
afterwards then landed on an off-screen buffer cell and was lost from display().
"""
import pyte


def test_resize_shrink_keeps_cursor_y_in_bounds():
    screen = pyte.Screen(1, 10)
    screen.cursor_position(9, 1)       # y = 8
    screen.resize(lines=1, columns=1)
    assert 0 <= screen.cursor.y < screen.lines


def test_resize_shrink_keeps_cursor_x_in_bounds():
    screen = pyte.Screen(10, 1)
    screen.cursor_to_column(9)         # x = 8
    screen.resize(lines=1, columns=2)
    assert 0 <= screen.cursor.x <= screen.columns


def test_draw_after_shrink_is_visible():
    screen = pyte.Screen(1, 10)
    screen.cursor_position(9, 1)
    screen.resize(lines=1, columns=1)
    screen.draw("X")
    assert "X" in "".join(screen.display)


def test_resize_grow_leaves_cursor_untouched():
    # Growing the screen must not move a cursor that is already in bounds.
    screen = pyte.Screen(5, 5)
    screen.cursor_position(3, 4)
    screen.resize(lines=10, columns=10)
    assert (screen.cursor.x, screen.cursor.y) == (3, 2)
