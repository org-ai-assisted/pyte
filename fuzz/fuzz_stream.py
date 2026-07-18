#!/usr/bin/python3 -Bsu

## Copyright (C) 2026 - 2026 ENCRYPTED SUPPORT LLC <adrelanos@whonix.org>
## See the file COPYING for copying conditions.

## AI-Assisted

"""
Atheris coverage-guided fuzz harness for pyte's Stream parser.

Feeds fuzzer-generated text through Stream.feed() and, when feed() succeeds,
asserts the Screen state invariants (display line count, cursor bounds). This
is the coverage-guided companion to the dist-ai in-process fuzzer
(pyte-tests-fuzz / fuzz_pyte.py).

The parser has known, already-reported crash classes on malformed input (see
the pyte-audit repository, bugs A-F: TypeError / UnboundLocalError /
AssertionError / ValueError escaping feed()). Those are tolerated here so the
coverage-guided engine explores PAST them and hunts for new failure modes
(other exception types, invariant violations, hangs). Once the parser-hardening
fixes land those exceptions no longer occur, and this harness keeps asserting
the same invariants.
"""

import sys

import atheris

with atheris.instrument_imports():
    import pyte

# Known, already-reported parser-crash exception classes (pyte-audit A-F).
_KNOWN = (TypeError, UnboundLocalError, AssertionError, ValueError)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(2 ** 16)

    screen = pyte.Screen(80, 24)
    stream = pyte.Stream(screen)
    try:
        stream.feed(text)
    except _KNOWN:
        return

    # feed() succeeded: the screen must remain in a consistent state.
    assert len(screen.display) == screen.lines
    assert 0 <= screen.cursor.x <= screen.columns
    assert 0 <= screen.cursor.y < screen.lines


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
