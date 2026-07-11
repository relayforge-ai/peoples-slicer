# Contributing to The People's Slicer

Thanks for helping file the landmines down to nothing. This project runs everything *after* the
slice — discover printers, review finicky settings, send headless with zero parameter loss. The bar
is **bulletproof and legible**: a 74-year-old with a laptop and an agent should never hit a cryptic
failure.

## Dev setup

```bash
git clone https://github.com/relayforge-ai/peoples-slicer && cd peoples-slicer
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install pytest
pytest -q          # 98 tests should pass before you change anything
```

No printer required to develop — the test suite uses fixtures/mock adapters (`tests/`, `forge/fixtures.py`).

## The bar for a PR

- **Tests stay green.** New behavior ships with tests. Never weaken a test to make CI pass.
- **Small, focused PRs.** One change, described in plain terms: what, why, and how you verified it.
- **Errors must be legible.** Fail with a clear message that names the file/printer/field — never leak a
  bare stack trace at a boundary (config, discover, send). That legibility *is* the product.
- **No secrets, ever.** All credentials are read from the environment (`AD5X_*`, `BAMBU_*`,
  `MOONRAKER_URL`, or a `FORGE_CONFIG` you control). Nothing sensitive goes in the repo — CI will reject it.

## The highest-value contribution: a new printer adapter

Most printers are one adapter away. Subclass the base adapter (`forge/adapters/base.py`), implement
upload + start + status, and ship it with tests + a fixture (see `ad5x.py` / `bambu.py` / `klipper.py`
as references). Zero-parameter-loss is the whole point — prove your adapter drops nothing the machine
expects.

## ⚠️ `forge/guardian.py` is print-safety

The guardian is the layer that keeps an autonomous print from doing something dangerous. Changes there
get **extra scrutiny and a maintainer sign-off** — no logic, threshold, or timing change lands without
it. Clarity-only fixes (docstrings, names) are always welcome.

## Conduct

Be decent, be specific, assume good faith. We're building a tool people trust with real hardware.

By contributing, you agree your work is licensed under the project's **MIT License**.
