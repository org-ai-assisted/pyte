# BUG-C: `erase_in_line` / `erase_in_display` raise `UnboundLocalError` on an unhandled `how`

## Summary

`Screen.erase_in_line(how)` and `Screen.erase_in_display(how)` build a local
`interval` only for the `how` values they recognise. Any other value leaves
`interval` unbound, so the next statement raises
`UnboundLocalError: cannot access local variable 'interval'`. The exception
propagates out of `Stream.feed()`, so a program that emits `ESC[3K` or `ESC[4J`
crashes the emulator.

## Affected versions

* upstream master `0.8.3.dev` (commit `0718fa8`) -- **confirmed**
* Debian `python3-pyte` `0.8.0-3` -- **confirmed** (identical)

## Minimal reproduction

```python
import pyte

screen = pyte.Screen(10, 5)
pyte.Stream(screen).feed("\x1b[3K")   # EL with parameter 3
```

```
UnboundLocalError: cannot access local variable 'interval' where it is not associated with a value
```

Equivalently `feed("\x1b[4J")` (ED with parameter 4), or the direct calls
`Screen(10, 5).erase_in_line(3)` / `.erase_in_display(4)`.

## Expected vs actual

* **Expected:** an unsupported erase mode is ignored (no-op), as with other
  unknown parameters. Most terminals ignore `CSI 3 K` and `CSI 4 J`.
* **Actual:** `UnboundLocalError` escapes `feed()`.

## Root cause

`pyte/screens.py`, `erase_in_line` (and the same shape in `erase_in_display`):

```python
self.dirty.add(self.cursor.y)
if how == 0:
    interval = range(self.cursor.x, self.columns)
elif how == 1:
    interval = range(self.cursor.x + 1)
elif how == 2:
    interval = range(self.columns)

line = self.buffer[self.cursor.y]
for x in interval:          # <-- interval never bound when how not in {0,1,2}
    ...
```

## Proposed fix

Treat an unrecognised `how` as a no-op.

```diff
--- a/pyte/screens.py
+++ b/pyte/screens.py
@@ def erase_in_line(self, how: int = 0, private: bool = False) -> None:
         self.dirty.add(self.cursor.y)
         if how == 0:
             interval = range(self.cursor.x, self.columns)
         elif how == 1:
             interval = range(self.cursor.x + 1)
         elif how == 2:
             interval = range(self.columns)
+        else:
+            return

         line = self.buffer[self.cursor.y]
         for x in interval:
             line[x] = self.cursor.attrs
@@ def erase_in_display(self, how: int = 0, *args: Any, **kwargs: Any) -> None:
         if how == 0:
             interval = range(self.cursor.y + 1, self.lines)
         elif how == 1:
             interval = range(self.cursor.y)
         elif how == 2 or how == 3:
             interval = range(self.lines)
+        else:
+            return

         self.dirty.update(interval)
```

## Regression test

`tests/test_full_regressions.py::test_erase_in_line_unknown_how_is_noop` and
`::test_erase_in_display_unknown_how_is_noop` (currently `xfail(strict=True)`).
