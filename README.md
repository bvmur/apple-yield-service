# Урожайность сада яблонь — месяцы сезона

Лабораторная работа №2 по курсу «Разработка интернет-приложений» (МГТУ им. Н. Э. Баумана).
SSR-приложение на FastAPI + Jinja2, данные в PostgreSQL (SQLAlchemy 2, async), миграции — Alembic.

## Страницы

| Адрес | Что показывает |
|---|---|
| `/months` | плитка опубликованных месяцев с фильтром по температуре и числом лайков |
| `/months/feed`, `/months/feed/{id}` | лента: один месяц, переход к следующему по кругу |
| `/months/draft` | добавление месяца в два шага: «Далее» → «Опубликовать» |

## Запуск

```bash
# 1. PostgreSQL, Adminer и MinIO
docker compose up -d

# 2. Окружение Python
python -m venv my-webapp
source my-webapp/bin/activate
pip install -r requirements.txt

# 3. Переменные окружения
cp .env.example .env        # вписать пароль от БД из docker-compose.yml

# 4. Таблицы
alembic upgrade head

# 5. Сервер
python main.py              # http://127.0.0.1:8000
```

Adminer: http://localhost:8081 (сервер `postgres`, пользователь и пароль — из `docker-compose.yml`).

## Структура

```
api/handlers.py     обработчики (GET через ORM, «Далее» и «Опубликовать» через ORM, удаление — сырым SQL)
models/             модели SQLAlchemy: User, Month, MonthLike
db/                 Base и асинхронная сессия
core/config.py      настройки из .env (pydantic-settings)
alembic/            миграции
templates/, static/ шаблоны Jinja2, CSS, фото и видео по умолчанию
```
