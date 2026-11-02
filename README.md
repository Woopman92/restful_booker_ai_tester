# Restful Booker Tests

## 1. Overview

A Python API test suite for [Restful Booker](https://restful-booker.herokuapp.com/),
an API playground for practicing API testing by creating and managing hotel bookings.
Tests use pytest and requests
to validate authentication and booking operations against the
[API documentation](https://restful-booker.herokuapp.com/apidoc/).

The suite checks response statuses, media types, schemas, field values, boundaries,
and persistence after write operations. Positive and negative scenarios are separated.
Each scenario uses its own booking data where needed and cleans it up afterward.
A session-level Ping check with retries runs before the tests. Confirmed deviations
from the documented contract use strict `xfail` markers; unspecified behavior is
recorded separately without `xfail` and marked `current_behavior`. Load testing is outside the project scope.

## 2. Structure

```text
.
├── tests/
│   ├── client.py              # Endpoint-specific ApiClient methods
│   ├── conftest.py            # Shared fixtures, session health check and cleanup
│   └── <endpoint>/            # Endpoint-specific positive and negative test modules
├── checkers/                  # Reusable response and persisted-state checks
│   ├── common.py              # General response checks
│   └── bookings.py            # Shared booking checks
├── helpers/
│   ├── models.py              # Shared dataclasses
│   └── payloads.py            # Payload transformations and serialization
├── constants.py               # Host, endpoint paths, credentials and Ping settings
├── pyproject.toml             # Poetry dependencies and pytest configuration
├── poetry.lock               # Locked dependency versions
├── setup.cfg                 # isort, yapf and flake8 configuration
├── Dockerfile                # Container environment and default test command
├── .dockerignore             # Build context exclusions
├── .gitignore                # Git exclusions for local environments, caches and IDE files
├── Makefile                  # Docker and local development commands
└── AGENTS.md                 # Project development instructions
```

Endpoint directories may also contain fixtures and support code specific to their
lifecycle. Shared implementations are reused across endpoint groups.

## 3. Requirements

| Run mode | Required tools |
| --- | --- |
| Docker | Docker Engine with a running daemon, or Docker Desktop, and GNU Make |
| Local | Python 3.11, Poetry (2.1.3 is used in the image), GNU Make, and a project `.venv` |

Git is needed to clone the repository and manage changes. The Makefile commands
assume a POSIX shell, such as on Linux, macOS, or within WSL on Windows.

Image builds require access to the Docker registry and PyPI. Local dependency
installation requires access to PyPI. API test execution requires network access
to the configured Restful Booker service. No local application server or database
is required when using the default public service. Docker commands do not require
Python or Poetry to be installed on the host.

## 4. Code Style

- Follow the configuration in `setup.cfg`: isort for imports, yapf for formatting,
  and flake8 for linting, with a maximum line length of 120 characters.
- Add type annotations and clear docstrings to functions. Use Google-style
  docstrings for helpers, fixtures and methods, including applicable `Args`,
  `Returns` or `Yields`, and `Raises` sections. Test docstrings briefly describe
  the behavior being checked. Write docstrings and code comments in English.
- Use snake_case endpoint directory names derived from documentation anchors.
  Name test files `test_<endpoint>_positive.py` or `test_<endpoint>_negative.py`.
- Group related tests into classes and apply the `positive` or `negative` marker.
  Keep parameter values consistent and put case descriptions in the shared `ids`
  argument of `pytest.mark.parametrize()`.
- Arrange test bodies as preparation, request, and verification. Execute each
  request on its own line and store its result in `response`. Use separate tests
  when parameter cases require different expectations instead of adding `if`
  branches to the test body.
- Reuse existing functions before introducing new ones. Place reusable checks in
  `checkers`, data transformations in `helpers`, and shared dataclasses in
  `helpers/models.py`. Keep API client methods in `tests/client.py`.
- Use plain `assert` statements and register assertion rewriting before importing
  checker modules. Keep response parsing inside checkers.
- Mark confirmed documentation mismatches with a descriptive `xfail`. For
  unspecified behavior, use a separate current-behavior test with an explanatory
  English comment and no `xfail`.
- Remove unused helpers, fixtures and imports when deleting tests. Run formatting
  and lint checks before committing; use Conventional Commits messages.

## 5. Docker Run

Start Docker Engine or Docker Desktop, then run:

```sh
make build   # Build the image
make test    # Run all tests
make lint    # Check isort, yapf and flake8
make format  # Apply isort and yapf to the host sources
```

The `test`, `lint`, and `format` targets first build the image using Docker's build
cache. Poetry installs dependencies from `poetry.lock`, including the `dev` group.
Changes to source files alone reuse the dependency installation layer.

Select tests and pass pytest options with `PYTEST_ARGS`:

```sh
make test PYTEST_ARGS="tests/delete_booking -q"
make test PYTEST_ARGS="--collect-only -q"
make test PYTEST_ARGS="-m positive -q"
make test PYTEST_ARGS="-m current_behavior -q"
make test PYTEST_ARGS="-m 'not current_behavior' -q"
```

`current_behavior` supplements `positive` or `negative` and identifies expectations
based on observed, undocumented behavior. It does not make failures expected.
Known deviations from documented behavior continue to use `xfail`.
The same marker expressions work with `make test-local`.

Override the service URL, regular API request timeout in seconds, or image name:

```sh
make test BOOKER_BASE_URL="https://restful-booker.herokuapp.com" BOOKER_TIMEOUT=15
make build IMAGE="restful-booker-tests:dev"
```

The session-level Ping check retries failed requests before allowing tests to run.
Its timeout and retry settings are defined separately in `constants.py`.
A nonzero exit code from pytest or a code quality tool causes `make` to fail.

Tests and lint checks use source files copied into the image. Formatting mounts
the project directory at `/app`, so changes are saved to the host. The formatting
container runs with the host user's UID/GID. The container's virtual environment
is located at `/opt/venv` and does not depend on the host's `.venv`.

Containers are automatically removed after completion. You can also run the image
directly:

```sh
docker run --rm restful-booker-tests:local pytest tests/delete_booking -q
```

## 6. Local Run

Create the project's `.venv` and install dependencies:

```sh
python3.11 -m venv .venv
VIRTUAL_ENV="$PWD/.venv" poetry install --with dev
```

The local commands use Poetry with the project's `.venv` selected explicitly:

```sh
make test-local
make test-local PYTEST_ARGS="tests/delete_booking -q"
make lint-local
make format-local
```

`PYTEST_ARGS`, `BOOKER_BASE_URL`, and `BOOKER_TIMEOUT` work the same way as for
container runs. You do not need to activate the virtual environment manually.
Use `make help` to list all available targets.
