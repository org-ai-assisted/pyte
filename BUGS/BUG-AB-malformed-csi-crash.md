# BUG-A / BUG-B: `Stream.feed()` crashes on malformed CSI (surplus parameters, stray private marker)

## Summary

The CSI parser in `Stream._parser_fsm()` forwards *every* collected parameter to
the mapped `Screen` handler with `handler(*params)` (and `private=True` when a
`?` was seen). Handlers have fixed signatures, so:

* **BUG-A** -- a CSI carrying more numeric parameters than the handler accepts
  raises `TypeError: ... takes from 1 to N positional arguments but M were
  given`. Example: `ESC[1;2A` calls `cursor_up(1, 2)`.
* **BUG-B** -- a private (`?`) CSI whose final byte maps to a handler without a
  `private` keyword raises `TypeError: ... got an unexpected keyword argument
  'private'`. Example: `ESC[?0A` calls `cursor_up(0, private=True)`.

Both exceptions escape `Stream.feed()` (the parser resets its own state in
`_send_to_parser` but then re-raises), so malformed or corrupted terminal
output crashes the hosting application.

These are robustness/hardening issues rather than spec violations -- the offending
sequences are malformed -- but a terminal emulator is expected to ignore
surplus parameters and unknown private markers, not abort. They were the
dominant finding of the fuzz harness (`tests/fuzz_pyte.py`).

## Affected versions

* upstream master `0.8.3.dev` (commit `0718fa8`) -- **confirmed**
* Debian `python3-pyte` `0.8.0-3` -- **confirmed** (identical)

## Minimal reproduction

```python
import pyte

# BUG-A: extra parameters
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[1;2A")      # cursor_up(1, 2)
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[1;2;3H")    # cursor_position(1, 2, 3)
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[0;0@")      # insert_characters(0, 0)

# BUG-B: private marker on a non-private handler
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[?0A")       # cursor_up(0, private=True)
pyte.Stream(pyte.Screen(10, 5)).feed("\x1b[?0@")       # insert_characters(0, private=True)
```

Each raises `TypeError`. Affected finals include essentially every
single-argument CSI command (`@ A B C D G L M P X d e ...`).

## Expected vs actual

* **Expected:** surplus parameters are ignored (only the first N consumed) and a
  private marker on a command that has no private form is ignored; no exception
  reaches the caller.
* **Actual:** `TypeError` propagates out of `feed()`.

## Root cause

`pyte/streams.py`, `_parser_fsm()` CSI branch:

```python
params.append(min(int(current or 0), 9999))
if char == ";":
    current = ""
else:
    if private:
        csi_dispatch[char](*params, private=True)
    else:
        csi_dispatch[char](*params)
    break
```

`csi_dispatch` is a `defaultdict` whose default is `debug`, so unknown *finals*
are already handled gracefully; only the *argument shape* is unchecked.

## Proposed fix

Scope the tolerance to the CSI dispatch and fall back to the existing `debug`
sink -- the designated endpoint for unrecognised sequences -- when the arguments
do not fit the handler:

```diff
--- a/pyte/streams.py
+++ b/pyte/streams.py
@@
                     else:
-                        if private:
-                            csi_dispatch[char](*params, private=True)
-                        else:
-                            csi_dispatch[char](*params)
-                        break  # CSI is finished.
+                        handler = csi_dispatch[char]
+                        try:
+                            if private:
+                                handler(*params, private=True)
+                            else:
+                                handler(*params)
+                        except TypeError:
+                            # Malformed CSI: surplus parameters or a private
+                            # marker on a command with no private form. Route
+                            # to the catch-all instead of crashing feed().
+                            debug(*params, private=private)
+                        break  # CSI is finished.
```

Trade-off worth noting for maintainers: this also swallows a hypothetical
`TypeError` raised *inside* a handler. If that is a concern, the alternative is
to give the single-parameter CSI handlers uniform `*args`/`private: bool = False`
signatures so surplus arguments are ignored at the handler instead of the
parser. Either approach fixes the crash; the parser-level guard is the smaller
diff.

## Regression tests

`tests/test_full_regressions.py::test_extra_params_cursor_up`,
`::test_extra_params_cursor_position`, `::test_extra_params_insert_characters`,
`::test_private_flag_cursor_up`, `::test_private_flag_insert_characters`
(currently `xfail(strict=True)`). The fuzz harness `tests/fuzz_pyte.py` also
tracks these signatures in `tests/known_crashes.json`.
