# Repository Guidelines

## Project Structure & Module Organization

This is a small Flask API that generates PNG images with Pillow.

- `main.py` contains the Flask application, routes, request parsing, image creation, and local `app.run()` entry point.
- `src/pillow_web/__init__.py` currently contains the package stub.
- `README.md` documents the API behavior and example URLs.
- `pyproject.toml` defines package metadata, runtime dependencies, Python support, and the Hatchling build backend.
- `uv.lock`, `.python-version`, and `mise.toml` define the local toolchain. Use `uv` for dependency management.
- Put new tests under `tests/`, using names such as `tests/test_images.py`.

## Build, Test, and Development Commands

- `uv sync`: install locked dependencies into the project environment.
- `uv run main.py`: start the development server, usually at `http://127.0.0.1:5000`.
- `uv run python -m pytest`: run the test suite when tests are present.
- `uv build`: build source and wheel distributions through Hatchling.

When manually checking behavior, call endpoints such as:

```bash
curl -I "http://127.0.0.1:5000/Hello?width=300&height=120"
```

## Coding Style & Naming Conventions

Use standard Python style with 4-space indentation, clear function names, and small route handlers. Keep request parameter names stable because they are part of the public API, for example `width`, `height`, `font_size`, and `backgroundimage`.

Prefer explicit error handling around user input, network access, and Pillow image operations. Keep comments short and focused on non-obvious behavior. Ruff is configured in `pyproject.toml` for both formatting and linting; run `uv run ruff format` and `uv run ruff check` before committing.

## Testing Guidelines

Use `pytest` for new tests. Prefer Flask test-client tests for routes instead of starting a live server. Cover successful PNG generation, query parameter parsing, invalid numeric values, transparent backgrounds, and background image failure handling.

Name test files `test_*.py` and test functions `test_*`. Keep generated files and caches out of version control.

## Commit & Pull Request Guidelines

Recent history uses short, imperative commits, including Conventional Commit style such as `feat: Add GitHub Actions workflow for OpenHands resolver`. Prefer `type: summary` for feature and fix work, for example `fix: validate image dimensions`.

Pull requests should include a concise description, linked issue when applicable, test results, and screenshots or example URLs for visible API output changes.

## Security & Configuration Tips

The `backgroundimage` parameter fetches remote URLs. Validate or constrain this behavior before using the service in untrusted environments. Do not commit local virtual environments, caches, generated images, or secrets.
