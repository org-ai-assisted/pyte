# BUG-D: `cursor_to_line` (VPA) and `report_device_status` (DSR) crash under DECOM with no margins

## Summary

When origin mode (`DECOM`) is enabled but no scrolling region has been set with
`DECSTBM`, `self.margins` is `None`. `Screen.cursor_to_line()` and
`Screen.report_device_status(6)` both dereference `self.margins.top` guarded
only by `assert self.margins is not None`. With margins unset the assertion
fails (`AssertionError`), and with assertions disabled (`python -O`) it becomes
`AttributeError: 'NoneType' object has no attribute 'top'`. Either way the
exception escapes `Stream.feed()`.

`cursor_position()` already guards this exact situation correctly
(`if self.margins is not None and mo.DECOM in self.mode`); these two methods do
not.

## Affected versions

* upstream master `0.8.3.dev` (commit `0718fa8`) -- **confirmed** (`AssertionError`)
* Debian `python3-pyte` `0.8.0-3` -- **confirmed** (`AttributeError`, no asserts)

## Minimal reproduction

```python
import pyte

screen = pyte.Screen(10, 5)
pyte.Stream(screen).feed("\x1b[?6h\x1b[5d")   # set DECOM, then VPA (cursor_to_line)
```

```
AssertionError
```

Also `feed("\x1b[?6h\x1b[6n")` (DSR cursor-position report under DECOM), or the
direct call:

```python
screen = pyte.Screen(10, 5)
screen.set_mode(pyte.modes.DECOM)   # margins still None
screen.cursor_to_line(3)            # AssertionError
```

## Expected vs actual

* **Expected:** with no scrolling region, DECOM is relative to the full screen;
  the cursor move / status report should behave as if `margins.top == 0`. No
  crash. (This matches `cursor_position()`'s own handling.)
* **Actual:** `AssertionError` (or `AttributeError` under `-O`).

## Root cause

`pyte/screens.py`:

```python
def cursor_to_line(self, line=None):
    self.cursor.y = (line or 1) - 1
    if mo.DECOM in self.mode:
        assert self.margins is not None     # <-- fails when margins unset
        self.cursor.y += self.margins.top
    self.ensure_vbounds()

def report_device_status(self, mode):
    ...
    elif mode == 6:
        ...
        if mo.DECOM in self.mode:
            assert self.margins is not None  # <-- same
            y -= self.margins.top
        self.write_process_input(ctrl.CSI + f"{y};{x}R")
```

## Proposed fix

Guard on `self.margins`, mirroring `cursor_position()`:

```diff
--- a/pyte/screens.py
+++ b/pyte/screens.py
@@ def cursor_to_line(self, line: int | None = None) -> None:
-        if mo.DECOM in self.mode:
-            assert self.margins is not None
+        if mo.DECOM in self.mode and self.margins is not None:
             self.cursor.y += self.margins.top
@@ def report_device_status(self, mode: int) -> None:
-            if mo.DECOM in self.mode:
-                assert self.margins is not None
+            if mo.DECOM in self.mode and self.margins is not None:
                 y -= self.margins.top
```

## Regression test

`tests/test_full_regressions.py::test_vpa_under_decom_without_margins`,
`::test_dsr_under_decom_without_margins`,
`::test_cursor_to_line_decom_no_margins_direct` (currently `xfail(strict=True)`).
