# Remaining Code Review Items

Issues from the initial deep review that have not yet been addressed.

## Deferred / Acknowledged

**#2 — No authentication on admin endpoints** (`text_server.py`)
Routes like `/adminReply`, `/addName`, `/removeBlock`, etc. have no auth.
_Acknowledged: authentication is handled at the network/infrastructure layer._

## Still To Fix

**#12 — `NameValidator` uses `dict` as a set** (`name_validator.py`)
`self.names[name] = 1` should be `self.names = set()` with `self.names.add(name)`.
Semantically cleaner and signals intent clearly.

~~**#14 — Trailing semicolons** (`text_server.py`)~~
~~A few lines in `text_server.py` still have trailing semicolons (e.g. `validNames = findValidNames(textIn);`).~~
~~Not a bug, but not Pythonic.~~ ✅ Fixed

**#18 — Unpinned Python version in Dockerfile** (`Dockerfile`)
`FROM python:3` will silently advance to new minor versions over time.
Pin to a specific version (e.g. `python:3.12-slim`) for reproducibility and a smaller image.
