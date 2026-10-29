# Запуск в Docker

Нужны запущенный Docker Engine (например, Docker Desktop) и `make`.
Python и Poetry на хосте для этих команд не требуются.

```sh
make build   # Build the image
make test    # Run all tests
make lint    # Check isort, yapf and flake8
make format  # Apply isort and yapf to the host sources
```

Команды `test`, `lint` и `format` сначала собирают образ с использованием кеша Docker.
Зависимости устанавливаются Poetry из `poetry.lock`, включая группу `dev`.
При изменении только исходников слой установки зависимостей используется повторно.

Выбор тестов и параметров pytest:

```sh
make test PYTEST_ARGS="tests/delete_booking -q"
make test PYTEST_ARGS="--collect-only -q"
make test PYTEST_ARGS="-m positive -q"
```

Адрес сервиса, тайм-аут обычных API-запросов и имя образа можно переопределить:

```sh
make test BOOKER_BASE_URL="https://restful-booker.herokuapp.com" BOOKER_TIMEOUT=15
make build IMAGE="restful-booker-tests:dev"
```

Перед тестами действует общая проверка Ping с повторами. Для сборки нужен доступ
к реестру Docker и PyPI; для выполнения API-тестов — доступ к сервису.
Ненулевой код завершения pytest или линтера приводит к ошибке команды `make`.

Тесты и линтер используют исходники из образа. Для форматирования папка проекта
подключается к `/app`, поэтому изменения сохраняются на хосте. Контейнер форматирования
запускается с UID/GID текущего пользователя. Окружение контейнера находится
в `/opt/venv` и не зависит от локальной `.venv`.

Контейнеры автоматически удаляются после завершения. Можно запускать образ напрямую:

```sh
docker run --rm restful-booker-tests:local pytest tests/delete_booking -q
```

## Локальный запуск без Docker

Нужны Python 3.11, Poetry и виртуальное окружение `.venv` в корне проекта.
Первоначальная подготовка:

```sh
python3.11 -m venv .venv
VIRTUAL_ENV="$PWD/.venv" poetry install --with dev
```

Команды используют Poetry с явно выбранным окружением `.venv`:

```sh
make test-local
make test-local PYTEST_ARGS="tests/delete_booking -q"
make lint-local
make format-local
```

`PYTEST_ARGS`, `BOOKER_BASE_URL` и `BOOKER_TIMEOUT` работают так же, как для
контейнерного запуска. Активировать окружение вручную не требуется.
