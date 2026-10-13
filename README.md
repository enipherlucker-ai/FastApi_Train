# FastApi_Train

## Уроки

- [Создание своего docker и docker.yml для чайников](docs/docker-for-beginners.md) — Dockerfile и Docker Compose с объяснениями, практикой и самостоятельными заданиями на этом FastAPI-приложении.
- [Свой сервер PostgreSQL в Docker для чайников](docs/postgres-docker-for-beginners.md) — сервис базы в `compose.yaml`: данные в volume, пароль в `.env`, healthcheck, стартовые скрипты, подключение с компьютера и из соседних контейнеров (заготовка под `api`, `web`, `db`, `bot`).
- [ORM и SQLAlchemy в FastAPI для чайников](docs/orm-sqlalchemy-for-beginners.md) — Active Record и Data Mapper, модели, сессии и транзакции, репозитории для работы с базой, схемы Pydantic для API; по уроку эндпоинты пользователей переписываются на PostgreSQL.
- [OpenAI в FastAPI: модель раскладывает покупки по группам](docs/openai-categorizer-for-beginners.md) — structured outputs, ключ в настройках, проверка ответа модели, память из базы вместо повторных запросов; по уроку `POST /create_receipt` начинает сам определять группы позиций.
