# AGENTS.md

## Tests

The comprehensive regression and fuzz suites for this repository live in
[github.com/org-ai-assisted/dist-ai](https://github.com/org-ai-assisted/dist-ai),
not in this tree. They are too high-volume to review here and run against this
checkout in CI via `.github/workflows/consumer-dist-ai-tests.yml`.

`pyte-audit-fixes.txt` at the repo root declares which
[pyte-audit](https://github.com/org-ai-assisted/pyte-audit) findings this tree
fixes. The dist-ai suites read it to decide, per finding, whether the
regression test must pass or must still reproduce, so a fix and its declaration
belong in the same commit.
