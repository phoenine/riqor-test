# Contributing

`pyproject.toml` is the dependency contract and `uv.lock` is the reproducible
lock file. `requirements.txt` and `requirements-dev.txt` are compatibility
entry points for pip users; do not add a second set of version pins there.

## Local setup

Use Python 3.11 or later and [uv](https://docs.astral.sh/uv/):

```bash
uv sync --all-extras --locked
uv run pytest
uv build
```

The Web runtime uses Playwright. Install a browser before running a browser test:

```bash
uv run playwright install chromium
```

Generated API and Web consumer projects must be checked from an empty directory:

```bash
uv sync
uv run pytest
```

## Release checklist

1. Run the local setup verification commands above.
2. Confirm the GitHub Actions workflow is green.
3. Create an annotated immutable tag matching `pyproject.toml`, for example
   `v0.2.0`, on the release commit.
4. Push the commit and tag. Consumers must use the tag or a full commit SHA,
   never a moving branch.
