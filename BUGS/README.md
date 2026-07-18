# pyte defect reports

Defects found while building the full unit + property + fuzz suite under
`tests/` (`test_full_*.py`, `fuzz_pyte.py`). Every finding was reproduced in a
clean sandbox against **both** upstream master `0.8.3.dev` (commit `0718fa8`)
**and** the Debian package `python3-pyte 0.8.0-3`.

All five defects reach `Screen` through `Stream.feed()` on plausibly-malformed
terminal output, so they are triggerable by any program whose output pyte
parses.

| ID | Severity | Trigger | Failure |
|----|----------|---------|---------|
| [BUG-A](BUG-AB-malformed-csi-crash.md) | crash | `ESC[1;2A` (surplus CSI params) | `TypeError` out of `feed()` |
| [BUG-B](BUG-AB-malformed-csi-crash.md) | crash | `ESC[?0A` (private marker on plain command) | `TypeError` out of `feed()` |
| [BUG-C](BUG-C-erase-unhandled-how-unboundlocal.md) | crash | `ESC[3K` / `ESC[4J` (unhandled erase mode) | `UnboundLocalError` |
| [BUG-D](BUG-D-decom-no-margins-assert.md) | crash | `ESC[?6h ESC[5d` / `ESC[?6h ESC[6n` (DECOM, no margins) | `AssertionError` / `AttributeError` |
| [BUG-E](BUG-E-resize-cursor-out-of-bounds.md) | data loss | `resize()` smaller than the cursor position | cursor left off-screen; later `draw()` lost |

BUG-C, BUG-D and BUG-E are unambiguous code defects (uninitialised local,
inconsistent `None` guard, missing re-clamp) with small, self-contained patches.
BUG-A/BUG-B are a malformed-input robustness class; the report discusses the
fix trade-off.

Each report contains: affected versions, a minimal `feed()` reproduction,
expected-vs-actual, root-cause, a proposed unified-diff patch, and the names of
the `xfail(strict=True)` regression tests that lock the fix.

## Differential: Debian 0.8.0-3 vs upstream master 0.8.3.dev

The suite was run against both builds in the sandbox.

* **Same crashes, same triggers.** All five defects are present in both
  versions. The 30k-iteration fuzz sweep produces the **identical five crash
  signatures** on each (`0 new` on both) -- the parser/handler code paths that
  fail have not changed between 0.8.0 and current master.
* **Only behavioural difference: BUG-D exception type.** Upstream master adds
  `assert self.margins is not None`, so BUG-D surfaces as `AssertionError`;
  Debian 0.8.0 has no assertion and reaches `None.top`, surfacing as
  `AttributeError`. Under `python -O` (assertions stripped) master degrades to
  the same `AttributeError`. The underlying defect is identical.
* **Version/API differences (not defects).** Debian 0.8.0 predates the modern
  rewrite: it still ships a `pyte.compat` shim and lacks `grapheme_clusters`
  (multi-codepoint emoji / combining-mark handling), so wide-/zero-width draw
  behaviour differs. These are expected version differences, not bugs, and are
  covered only in the upstream-targeted `test_full_api.py`.

## How these were found / how to reproduce

```console
$ cd tests
$ PYTHONPATH="$PWD/.." python3 -m pytest test_full_api.py test_full_regressions.py test_full_properties.py -q
$ PYTHONPATH="$PWD/.." python3 fuzz_pyte.py --iterations 30000 --report   # lists crash signatures
```

Every fuzz finding prints its `seed` and exact reproducing token sequence.
