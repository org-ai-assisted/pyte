# BUG-E: `resize()` to a smaller screen leaves the cursor out of bounds (silent data loss)

## Summary

`Screen.resize()` does not clamp the cursor to the new geometry. When the screen
is shrunk, the cursor can be left below the new bottom line or to the right of
the new last column. A subsequent `draw()` then writes to a buffer row/column
that is outside the visible area, so the text never appears in `display` -- it
is silently lost.

Unlike BUG-A..D this is not a crash; it is an observable wrong-state /
data-loss defect and a broken invariant (`0 <= cursor.y < lines`,
`0 <= cursor.x <= columns`).

## Affected versions

* upstream master `0.8.3.dev` (commit `0718fa8`) -- **confirmed**
* Debian `python3-pyte` `0.8.0-3` -- **confirmed** (identical)

## Minimal reproduction

```python
import pyte

screen = pyte.Screen(1, 10)     # 1 column, 10 lines
screen.cursor_position(9, 1)    # move to line 9 (y = 8)
screen.resize(lines=1, columns=1)

print(screen.cursor.y, screen.lines)      # -> 8 1   (cursor below the screen)
screen.draw("X")
print(screen.display)                     # -> [' ']  ('X' written off-screen)
print(8 in screen.buffer)                 # -> True  (leaked onto hidden row 8)
```

The column axis has the same defect:

```python
screen = pyte.Screen(10, 1)
screen.cursor_to_column(9)      # x = 8
screen.resize(lines=1, columns=2)
print(screen.cursor.x, screen.columns)    # -> 8 2   (cursor past the last column)
```

## Expected vs actual

* **Expected:** after a resize the cursor is clamped into the new bounds
  (`0 <= x <= columns`, `0 <= y < lines`); text drawn afterwards is visible.
* **Actual:** the cursor keeps its old coordinates; later output is written to
  an off-screen buffer cell and lost from `display`.

## Root cause

`pyte/screens.py`, `resize()`:

```python
if lines < self.lines:
    self.save_cursor()
    self.cursor_position(0, 0)
    self.delete_lines(self.lines - lines)
    self.restore_cursor()          # ensure_vbounds() here uses the OLD self.lines
...
self.lines, self.columns = lines, columns   # geometry updated only afterwards
self.set_margins()
```

`restore_cursor()` runs `ensure_vbounds()` / `ensure_hbounds()` while
`self.lines` and `self.columns` still hold the *old* values, so the cursor is
bounded to the pre-resize geometry. The column-shrink branch never re-clamps the
cursor at all.

## Proposed fix

Clamp the cursor to the new geometry after it has been applied:

```diff
--- a/pyte/screens.py
+++ b/pyte/screens.py
@@ def resize(self, lines=None, columns=None) -> None:
         self.lines, self.columns = lines, columns
+        self.ensure_hbounds()
+        self.ensure_vbounds()
         self.set_margins()
```

(`ensure_vbounds()` with no scrolling region bounds `y` to `[0, lines - 1]`;
`ensure_hbounds()` bounds `x` to `[0, columns - 1]`.)

## Regression test

`tests/test_full_regressions.py::test_resize_shrink_keeps_cursor_in_bounds`,
`::test_resize_column_shrink_keeps_cursor_x_in_bounds`,
`::test_draw_after_shrink_is_visible` (currently `xfail(strict=True)`).
