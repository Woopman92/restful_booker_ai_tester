FROM python:3.11-slim-bookworm

ARG POETRY_VERSION=2.1.3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
    && python -m venv /opt/venv \
    && useradd --create-home --uid 1000 tester

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --with dev --no-root --no-ansi \
    && rm -rf /root/.cache/pypoetry \
    && chown tester:tester /app

COPY setup.cfg constants.py ./
COPY tests/ ./tests/
COPY checkers/ ./checkers/
COPY helpers/ ./helpers/

USER tester

CMD ["pytest"]
