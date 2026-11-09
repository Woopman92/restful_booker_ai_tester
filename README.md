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
├── .github/workflows/
│   ├── auto-pr.yml            # Open a PR on the first push of a new branch
│   ├── main-tests.yml         # Test main and propose a revert PR on failure
│   └── tests.yml              # Build the Docker image and run all API tests
├── .github/scripts/           # Automation for proposing revert pull requests
├── tests/
│   ├── client.py              # Endpoint-specific ApiClient methods
│   ├── conftest.py            # Shared fixtures, session health check and cleanup
│   └── <endpoint>/            # Endpoint-specific positive and negative test modules
├── checkers/                  # Reusable response and persisted-state checks
│   ├── common.py              # Checks shared across endpoint test groups
│   ├── get_bookings.py        # GetBookings-specific checks
│   └── create_token.py        # CreateToken-specific checks
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

## 7. Automatic PRs

The `.github/workflows/auto-pr.yml` workflow opens a pull request into `main` on
the first push of a new branch to this repository. It skips `main`, branch
deletions, and subsequent pushes, and checks for an existing open PR before
creating one. Later commits pushed to the branch appear in the same PR.

Enable **Settings → Actions → General → Workflow permissions → Allow GitHub
Actions to create and approve pull requests**. The workflow uses GitHub's
provided token; no personal token, local GitHub CLI installation, or SSH key
is needed on the runner. It does not approve or merge PRs.

First publish the workflow to `main`. Then create a branch containing changes
relative to `main` before its first push:

```sh
git switch main
git pull --ff-only
git switch -c feature/example
# Make changes and commit them before pushing
git push -u origin feature/example
```

Check the workflow result on GitHub's **Actions** tab and the new PR on the
**Pull requests** tab. A branch identical to `main` cannot produce a PR. If the
first run fails, fix the cause and rerun the failed job from **Actions**.

## 8. CI Tests

The `.github/workflows/tests.yml` workflow runs on every branch push except
`main`, including the first push and subsequent updates. Its `API tests` job
checks out the pushed commit on an Ubuntu runner and executes `make test`, which
builds the Docker image and runs the complete pytest suite. The job has read-only
repository permissions and a 30-minute timeout.

Tests run independently of automatic PR creation. Using `push` avoids depending
on approval of workflows triggered by PRs created with `GITHUB_TOKEN`.
The runner needs network access to the Docker registry, PyPI, and Restful Booker.
Test failures, setup or cleanup errors, and an unsuccessful session Ping check
fail the job; documented expected failures (`xfail`) remain allowed.

View results and pytest output on the **Actions** tab or in the PR checks.
The workflow alone does not block merging: after publishing it and running it
once, make `API tests` a required status check in the ruleset for `main`.

The workflow also supports **Actions → API tests → Run workflow** for diagnostic
runs. Select the branch to test. GitHub does not count checks from
`workflow_dispatch` runs toward required PR status checks, even if the run
succeeds for the PR's latest commit.

## 9. Revert Proposals

The `Main API tests` workflow runs `make test` after every push to `main`.
On failure, including a build or service availability failure, a separate job
creates a branch named `revert/failed-main-<commit SHA>` and opens a PR into
`main`. Review the failed run before deciding whether to apply the revert.
The workflow never approves or merges PRs, and does not bypass branch rules.
The proposal runs only when GitHub reports the test job as failed; canceled and
skipped jobs do not create a revert proposal.

The proposal reverts the original push's first-parent commit range, supporting
merge commits, squash merges, and rebase merges. It starts from the latest
`main`, preserving later changes when the revert applies without conflicts.
Conflicts fail the proposal job and require manual resolution; inspect its logs.
Only updates associated with a merged PR are eligible. Direct pushes are tested
but do not generate a revert PR. A merged automatic revert never generates
another automatic revert, preventing a rollback loop.

The deterministic branch name prevents duplicate PRs on reruns, including when
the previous PR was closed. If branch publication succeeded but PR creation
failed, a rerun reuses the published branch. Later changes to `main` may require
updating that PR before it can be merged.

The proposal job uses `GITHUB_TOKEN` with `contents: write` and
`pull-requests: write`; the test job has read-only repository access. Keep
**Allow GitHub Actions to create and approve pull requests** enabled.
No additional secrets or ruleset bypass permissions are needed.

Pushes made with `GITHUB_TOKEN` do not start push-triggered CI. For a revert PR,
publish a reviewed commit to its branch using your own GitHub credentials.
If no code changes are needed, an empty commit triggers the normal `push`
workflow without altering the files:

```sh
git fetch origin
git switch --track origin/revert/failed-main-<commit-SHA>
git commit --allow-empty -m "ci: trigger required tests for revert"
git push
```

If the branch already exists locally, switch to it and update it with
`git pull --ff-only` instead of creating it again. Replace `<commit-SHA>` with
the failed commit's SHA from the revert PR. Wait for the push-triggered
`API tests` check before merging manually. A successful manual
`workflow_dispatch` run cannot replace this check. These limitations are
documented in [GitHub's required checks troubleshooting guide](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks#checks-from-some-workflow-jobs-are-not-evaluated).
