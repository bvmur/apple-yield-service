# Урожайность сада яблонь — веб-сервис (ЛР3)

Бэкенд на **FastAPI** для расчёта урожайности сада яблонь. Услуги — **месяцы** сезона
с климатическими нормами (температура, осадки). Данные — в **PostgreSQL** (SQLAlchemy + Alembic),
фото и видео месяцев — в **MinIO**. API отдаёт JSON и проверяется в Postman/Insomnia.

## Запуск

```bash
docker compose up -d              # postgres (5432), adminer (8081), minio (9000 / консоль 9001)
pip install -r requirements.txt
alembic upgrade head              # создать / обновить таблицы
python main.py                    # http://127.0.0.1:8000, документация API — /docs
```

Настройки подключения — в `.env` (образец — `.env.example`).

## Структура

| Папка / файл | Назначение |
|---|---|
| `api/months_api.py`, `api/users_api.py` | обработчики REST API (домены «месяцы» и «пользователь») |
| `api/handlers.py` | SSR-страницы из ЛР2 (HTML) |
| `schemas/` | сериализаторы Pydantic: что уходит в JSON и что можно прислать |
| `repositories/` | запросы к БД через ORM |
| `storage/minio_storage.py` | проверка и загрузка файлов в MinIO |
| `models/` | ORM-модели таблиц |
| `core/current_user.py` | функция-singleton текущего пользователя |
| `core/errors.py` | единый формат ошибок |
| `docs/postman_collection.json` | коллекция запросов Postman |

## Общие правила API

- Все адреса начинаются с `/api`. Формат данных — JSON (кроме создания месяца: `multipart/form-data`).
- Успех: `{"status": "success", "data": ..., "message": ...}`.
- Ошибка: `{"status": "fail", "message": "..."}` с кодом **400** (неверный запрос), **403** (чужая запись),
  **404** (не найдено), **409** (конфликт состояния).
- **Текущий пользователь** зафиксирован (авторизация — в ЛР4): `ivan_sadovod`, id = 1.
  Его возвращает функция-singleton `get_current_user()`, все методы получают его через `Depends`.
- **Системные поля** (`id`, `status`, `creator_id`, `created_at`, `formed_at`) клиент передавать не может —
  их нет во входных схемах, лишние поля отклоняются с кодом 400.
- Месяцы в статусе `deleted` клиенту не отдаются ни одним методом.
- Переходы статусов: `draft → published` (PUT публикации) и `draft/published → deleted` (DELETE).
  Вернуть в черновик нельзя.

## HTTP-методы

### Домен «месяцы» — `/api/months`

| # | Метод и URL | Тело запроса | Ответ | Коды |
|---|---|---|---|---|
| 1 | `GET /api/months?temp_from=&title=` | — | список опубликованных месяцев: `id, title, phase, norm_temp, norm_precip, impact, image_url, likes_count, is_mine` | 200, 400 |
| 2 | `GET /api/months/feed` <br> `GET /api/months/feed/{id}?next=true` | — | одна опубликованная запись ленты: поля месяца + `description, video_url, likes_count, is_liked`. Без id — первый месяц, с id — этот месяц, с `next=true` — следующий (по кругу). БД возвращает ровно одну строку | 200, 400, 404 |
| 3 | `GET /api/months/draft` | — | черновик текущего пользователя (не более одного), id не указывается | 200, 404 |
| 4 | `POST /api/months` | `multipart/form-data`: `title` (текст), `image` (файл JPG/PNG/WEBP до 5 МБ), `video` (файл MP4/MOV/WEBM до 30 МБ) | созданный черновик. Файлы сохраняются в MinIO (бакет `media`) под сгенерированными латинскими именами (`months/images/<uuid>.jpg`), ссылки — в `image_url`, `video_url` | 201, 400, 409 |
| 5 | `PUT /api/months/{id}/publish` | JSON: `description` (1–500 симв.), `norm_temp` (−50…50), `norm_precip` (0…1000), необязательно `phase`, `impact` (1–3) | опубликованный месяц: `status = published`, `formed_at` = время публикации. Только свой и только черновик | 200, 400, 403, 404, 409 |
| 6 | `DELETE /api/months/{id}` | — | логическое удаление: `status = deleted`. Только свои месяцы | 200, 403, 404 |
| 7 | `POST /api/months/{id}/like` | JSON: `{"value": 1}` — поставить, `{"value": 0}` — снять | `month_id, is_liked, likes_count`. Лайк от текущего пользователя, только опубликованным | 200, 400, 404 |

Признаки: `is_mine` = 1, если создатель месяца — текущий пользователь; `is_liked` = 1, если текущий пользователь лайкнул месяц.

### Домен «пользователь» — `/api/users`

| # | Метод и URL | Тело запроса | Ответ | Коды |
|---|---|---|---|---|
| 8 | `POST /api/users/register` | JSON: `username` (3–50, латиница/цифры/_), `password` (6–128) | `id, username, is_moderator`. Пароль хранится хэшем (PBKDF2-SHA256) и не возвращается | 201, 400, 409 |
| 9 | `POST /api/users/login` | JSON: `username`, `password` | заглушка (реализация — ЛР4) | 200 |
| 10 | `POST /api/users/logout` | — | заглушка (реализация — ЛР4) | 200 |

## Таблицы БД

### `users` — пользователи
| Поле | Тип | Ограничения |
|---|---|---|
| `id` | INTEGER | PK |
| `username` | VARCHAR(50) | NOT NULL, UNIQUE |
| `password_hash` | VARCHAR(255) | NOT NULL, по умолчанию `''` |
| `is_moderator` | BOOLEAN | NOT NULL, по умолчанию `false` |

### `months` — месяцы (услуги)
| Поле | Тип | Ограничения / смысл |
|---|---|---|
| `id` | INTEGER | PK |
| `title` | VARCHAR(30) | NOT NULL — наименование |
| `phase` | VARCHAR(50) | фаза развития дерева |
| `description` | VARCHAR(500) | краткое описание |
| `norm_temp` | SMALLINT | поле по теме: норма температуры, °C |
| `norm_precip` | SMALLINT | поле по теме: норма осадков, мм |
| `impact` | SMALLINT | значимость для урожая (1–3) |
| `image_url` | VARCHAR(255) | ссылка на фото в MinIO |
| `video_url` | VARCHAR(255) | ссылка на видео в MinIO |
| `status` | VARCHAR(20) | NOT NULL, по умолчанию `draft`; CHECK: `draft`, `published`, `deleted` |
| `created_at` | TIMESTAMP | NOT NULL, по умолчанию `now()` — дата создания |
| `formed_at` | TIMESTAMP | дата формирования (публикации) |
| `creator_id` | INTEGER | NOT NULL, FK → `users.id` — создатель |

Частичный уникальный индекс `uq_months_one_draft_per_creator (creator_id) WHERE status = 'draft'` —
у пользователя не более одного черновика.

### `month_likes` — лайки (связь М-М пользователь ↔ месяц)
| Поле | Тип | Ограничения |
|---|---|---|
| `id` | INTEGER | PK |
| `user_id` | INTEGER | NOT NULL, FK → `users.id` |
| `month_id` | INTEGER | NOT NULL, FK → `months.id` |

UNIQUE (`user_id`, `month_id`) — один лайк от пользователя на месяц. Каскадное удаление не используется.
