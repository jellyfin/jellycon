# CRUSH.md - JellyCon Codebase Guidelines

## Build & Test Commands
- `python build.py --version py2` - Build Python 2 version
- `python build.py --version py3` - Build Python 3 version
- `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics` - Syntax errors
- `flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics` - Style check
- No unit tests available - manual testing required

## Python Code Style
**Imports:**
- `from __future__ import (division, absolute_import, print_function, unicode_literals)`
- Standard lib → Third-party → Local modules
- Use relative imports for local modules: `from .utils import get_device_id`

**Naming:**
- Classes: PascalCase (`LazyLogger`, `HomeWindow`)
- Functions/variables: snake_case (`get_jellyfin_url`)
- Constants: UPPER_CASE (`__LOGGER`)
- Module vars: double underscore prefix (`__addon__`)

**Formatting:**
- 4-space indentation
- Max line length: 127 chars
- Use docstrings with triple quotes
- Function type hints in docstrings

**Error Handling:**
- Extensive try/except with specific exceptions
- Use `LazyLogger` for logging
- Include context in error messages
- Use `traceback` for debugging

## Architecture Patterns
- Service-oriented modules
- Decorators for timing/logging (`@timer`)
- Property management via `HomeWindow`
- Event-driven with monitors/websockets
- Python 2/3 compatibility with kodi-six