# ORM и SQLAlchemy в FastAPI для чайников 😄

**Цель урока:** после него ты сам, с пустых файлов, подключаешь FastAPI к PostgreSQL через ORM: описываешь таблицу классом, открываешь сессии, пишешь репозиторий для работы с базой и схемы, которые принимает и отдаёт API. И можешь объяснить, что происходит на каждом шаге запроса — от HTTP до SQL и обратно.

Урок построен на этом репозитории. В начале урока API хранит пользователей в списке `fake_user_database`, и после перезапуска всё пропадает. В конце те же пять эндпоинтов работают с таблицей `payment_statistic.users` в PostgreSQL из [урока по Postgres](postgres-docker-for-beginners.md). Адреса и параметры эндпоинтов не меняются, поэтому фронтенд из урока по Nuxt продолжит работать.

Команды выполняются **из корня репозитория** (там, где лежит `compose.yaml`) и одинаково работают в PowerShell и в Linux shell. Всё проверено на Python 3.12, SQLAlchemy 2.1.4, asyncpg 0.32, FastAPI 0.141, Pydantic 2.13 и PostgreSQL 18 (образ `postgres:18`).

## 0. Как проходить урок

Правила те же, что в [уроке по Docker](docker-for-beginners.md) и [уроке по Postgres](postgres-docker-for-beginners.md):

1. **Печатай руками.** Не копируй блоки кода из урока в файлы. Опечатки и ошибки — часть обучения.
2. **Одна настройка — одна проверка.** Проект собирается по одному файлу; после каждого шага ты запускаешь код и проверяешь, что изменилось именно то, что ожидал.
3. **Сначала предскажи — потом запусти.** Перед каждой командой скажи себе, что должно произойти. Расхождение с реальностью — самое ценное место урока.
4. **Ответы — в свёрнутых блоках.** Открывай их только после своей попытки.

И одно новое правило:

5. **Смотри на SQL.** ORM пишет SQL за тебя, и главный способ понять ORM — видеть, какой SQL он отправил. Во всех примерах урока включён режим `echo`: каждый запрос к базе печатается в терминал. Когда проект запущен в Docker, держи открытым терминал с `docker compose logs -f api`.

План: понять, что такое ORM и зачем он нужен (раздел 1) → два способа устроить ORM, Active Record и Data Mapper (2) → семь вопросов, из которых собирается подключение к базе (3) → инструменты (4) → ORM руками в одном файле, без FastAPI (5) → сессии подробно (6) → собрать проект по одному файлу (7) → проследить один запрос целиком (8) → правила, на которых ошибаются (9) → диагностика (10) → тренировка (11) → повторение по памяти (12).

---

## 1. Что такое ORM и какую проблему он решает

В [уроке по Postgres](postgres-docker-for-beginners.md) ты читал базу через `psycopg`: писал SQL строкой и получал кортежи `(1, 'Anna', 30)`. Для одного скрипта это нормально. Для приложения быстро становится больно:

- SQL-строки разбросаны по коду, опечатку в имени колонки видно только при запуске.
- Кортеж `(1, 'Anna', 30)` надо руками превращать в объект и обратно.
- Чтобы обновить пользователя, ты сам решаешь, какие колонки поменялись, и сам собираешь `UPDATE`.
- Чтобы два изменения прошли «оба или ни одного», ты сам управляешь транзакцией.

**ORM** (Object-Relational Mapping, «отображение объектов на таблицы») делает это за тебя: класс соответствует таблице, объект — строке, атрибут — колонке. Ты работаешь с объектами Python, а ORM переводит это в SQL.

| Объект | Что это | Аналогия |
|---|---|---|
| SQLAlchemy | Библиотека ORM для Python. Самая распространённая, её используют с FastAPI | Переводчик между Python и SQL |
| Драйвер (`asyncpg`) | Библиотека, которая по сети говорит с PostgreSQL. SQLAlchemy сам в сеть не ходит, он вызывает драйвер | Телефонная линия до базы |
| Engine | Объект, который знает адрес базы и держит **пул подключений**. Один на всё приложение | Телефонная станция с несколькими линиями |
| Пул подключений | Несколько уже открытых подключений к базе. Подключение берут из пула и возвращают, а не открывают каждый раз заново | Линии, которые не кладут трубку |
| Модель | Класс Python, описывающий таблицу: `class User` ↔ `payment_statistic.users` | Карта: где в таблице что лежит |
| Сессия (`AsyncSession`) | Рабочее место для одной порции работы: загружает объекты, следит за их изменениями, отправляет SQL, управляет транзакцией | Корзина в магазине |
| Транзакция | Группа изменений, которая применяется целиком или не применяется вовсе: `BEGIN ... COMMIT` или `ROLLBACK` | Оплата на кассе: либо вся корзина, либо ничего |
| Репозиторий | Твой класс, в котором собраны все запросы к одной таблице: `get`, `list`, `create`, `find_by_name` | Продавец, который знает, где что лежит на складе |
| Схема (Pydantic) | Описание того, что API **принимает и отдаёт**: какие поля, какие типы, какие ограничения | Бланк заявления с правилами заполнения |

**Модель отвечает на вопрос «как выглядит строка таблицы в Python?». Сессия отвечает на вопрос «что я изменил и когда отправить это в базу?». Репозиторий отвечает на вопрос «какие запросы к этой таблице умеет делать приложение?». Схема отвечает на вопрос «что API принимает и отдаёт?».**

Ещё три факта, которые понадобятся дальше:

- **Модель не создаёт таблицу.** Таблица `payment_statistic.users` уже создана скриптом `database/init/02_table_users.sql`. Модель — это только описание, «карта» существующей таблицы. Если карта не совпадает с местностью, ошибка будет при первом запросе (раздел 9).
- **Ничего не сохраняется, пока нет `commit`.** Сессия копит изменения и отправляет их в базу внутри транзакции. Без `commit` транзакция откатывается, и все изменения пропадают.
- **У нас асинхронный стек.** FastAPI асинхронный, поэтому берём асинхронный драйвер `asyncpg` и асинхронную сессию `AsyncSession`. Всё, что идёт в базу, вызывается с `await`.

### Как это выглядит в реальной работе

Один запрос `PUT /users/update/1?name=Anna&age=31` проходит такой путь:

```text
HTTP-запрос: PUT /users/update/1?name=Anna&age=31
   │
   ▼
FastAPI: проверяет параметры по схеме UserUpdate (Pydantic) ──── ошибка → ответ 422
   │
   ▼
Depends: get_session()         → новая AsyncSession
         get_user_repository() → UserRepository(session)
         get_user_or_404()     → объект User из базы ─────────── нет такого → ответ 404
   │
   ▼
Обработчик update_user():  users.update(user, ...)  →  session.commit()
   │                               │
   │                               ▼
   │                Engine → пул подключений → asyncpg → PostgreSQL (pg_database:5432)
   ▼
response_model=UserRead: ORM-объект User → JSON → ответ 200
```

К концу урока ты сможешь пройти по этой схеме пальцем и сказать, какая строка кода отвечает за каждую стрелку.

---

## 2. Active Record и Data Mapper

ORM бывают устроены двумя способами. Это главный выбор архитектуры, поэтому разберём его до кода.

### Active Record: объект сам ходит в базу

Объект знает про базу и **сам себя сохраняет**. Так устроены Django ORM, Ruby on Rails, Laravel Eloquent, Peewee. Пример в стиле Django (только для сравнения, не запускай):

```python
user = User(name="Anna", age=30)
user.save()                     # объект сам делает INSERT

user.age = 31
user.save()                     # объект сам делает UPDATE

anna = User.objects.get(id=1)   # класс сам делает SELECT
anna.delete()                   # объект сам делает DELETE
```

Удобно: мало кода, всё в одном месте. Но у модели две работы сразу — хранить данные **и** уметь работать с базой. Код, которому нужен пользователь, автоматически получает доступ к базе. Каждый `save()` — отдельный поход в базу, и где кончается транзакция, видно плохо.

### Data Mapper: объект — просто данные, в базу ходит отдельный «картограф»

Объект **ничего не знает** о базе. Переносом данных между объектами и таблицей занимается отдельный механизм — mapper. В SQLAlchemy с ним работают через **сессию**:

```python
user = User(name="Anna", age=30)   # просто объект в памяти, о базе не знает
session.add(user)                   # сессия взяла объект под наблюдение
user.age = 31                       # сессия заметит изменение сама
await session.commit()              # сессия решает, какой SQL отправить, и фиксирует транзакцию
```

У `user` нет методов `save()` или `delete()`. Все операции с базой идут **через сессию**, а у нас — ещё и через **репозиторий**, который прячет сессию за понятными методами.

### Сравнение

| | Active Record | Data Mapper |
|---|---|---|
| Кто ходит в базу | Сам объект: `user.save()` | Сессия или репозиторий: `session.add(user)` |
| Где лежат запросы | В модели: `User.objects.filter(...)` | В репозитории: `users.find_by_name(...)` |
| Транзакция | Часто — каждый `save()` отдельно | Одна на порцию работы, `commit` в одном месте |
| Несколько изменений «всё или ничего» | Нужно не забыть обернуть в транзакцию | Так по умолчанию: всё, что в сессии, уходит одним `commit` |
| Тесты | Модель трудно отделить от базы | Репозиторий легко подменить фальшивым |
| Порог входа | Ниже | Выше: нужно понять сессию |
| Хорош для | Простых CRUD-приложений, админок | Приложений, которые растут: API, боты, сервисы |

### Почему у нас Data Mapper

1. **Модель — только данные.** `User` описывает колонки и не умеет ходить в базу. Его можно передать куда угодно, не боясь, что кто-то случайно что-то сохранит.
2. **Все запросы к таблице — в одном классе.** Нужно понять, как приложение работает с пользователями, — открываешь `UserRepository`, а не ищешь `.filter(...)` по всему проекту.
3. **Транзакция в одном месте.** Один HTTP-запрос — одна сессия — один `commit`. Если в запросе два изменения (удалить пользователя и записать это в лог), они применятся вместе или не применятся вовсе (уровень 5 тренировки).
4. **SQLAlchemy — Data Mapper по устройству**, а это главный ORM для FastAPI.

> **Но ведь в SQLAlchemy модель наследуется от `Base` — разве это не Active Record?**
>
> Нет. Наследование от `Base` (декларативный стиль) — только удобный способ **описать соответствие** класса и таблицы в одном месте. Методов `save()`, `delete()` или `User.objects` у модели нет; всё, что идёт в базу, проходит через сессию.
>
> Чтобы увидеть Data Mapper в чистом виде, вот та же модель в **императивном** стиле: обычный dataclass, отдельно описание таблицы, и отдельная строка, которая их связывает. Класс `User` здесь вообще не импортирует SQLAlchemy.
>
> ```python
> from dataclasses import dataclass
>
> from sqlalchemy import Column, Integer, MetaData, Table, Text
> from sqlalchemy.orm import registry
>
>
> @dataclass
> class User:                       # просто данные
>     name: str
>     age: int
>     description: str | None = None
>     id: int | None = None
>
>
> metadata = MetaData()
> users_table = Table(              # просто описание таблицы
>     "users", metadata,
>     Column("id", Integer, primary_key=True),
>     Column("name", Text, nullable=False),
>     Column("age", Integer, nullable=False),
>     Column("description", Text),
>     schema="payment_statistic",
> )
>
> registry(metadata=metadata).map_imperatively(User, users_table)   # mapper: связать
> ```
>
> Работает этот вариант точно так же (проверишь в уровне 7 тренировки). В проекте мы пишем декларативно: короче, и типы колонок видны прямо в классе. Принцип при этом тот же.

**Правило проекта:** в модели — только колонки и, при необходимости, простая логика над своими полями. Ни одного `session` внутри модели. Все запросы к базе — в репозиториях. `commit` — там, где начинается и заканчивается порция работы (у нас — в обработчике запроса).

> **Проверь себя.** Какие из строк ниже нарушают правило проекта и почему?
>
> 1. `await user.save()`
> 2. `await users.create(name="Anna", age=30)`
> 3. `User.query.filter_by(name="Anna")`
> 4. `user.age += 1`
> 5. `await session.commit()` внутри метода `UserRepository.create`
>
> <details><summary>Ответ</summary>
>
> 1 и 3 — Active Record: объект или класс сам ходит в базу. 2 — так и надо: запрос спрятан в репозитории. 4 — нормально: это просто изменение объекта, в базу оно уйдёт при `commit`, который сделает кто-то другой. 5 — нарушение: репозиторий не должен решать, когда закончилась порция работы. Если обработчику нужно создать пользователя и записать событие в лог, `commit` внутри `create` зафиксирует первое до того, как случится второе. Подробно — в шаге 6 раздела 7.
>
> </details>

---

## 3. Алгоритм: семь вопросов перед подключением ORM

Подключение к базе не пишут «сверху вниз по памяти». Его пишут, **ответив на вопросы**. Запомни их — это и есть навык:

1. Какой драйвер и какой адрес базы? → `DATABASE_URL` в `config.py`
2. Как приложение подключается к базе? → `engine` в `database.py`, один на всё приложение
3. Откуда берётся сессия и сколько она живёт? → `session_factory` и `get_session` в `database.py`: одна сессия на один HTTP-запрос
4. Как таблица выглядит в Python? → модель в `models/`
5. Что API принимает и отдаёт? → схемы Pydantic в `schemas/`
6. Какие запросы к таблице нужны приложению? → репозиторий в `repositories/`
7. Где транзакция начинается и где фиксируется? → зависимости в `api/dependencies.py` выдают сессию и репозиторий; `commit` — в обработчике в `api/users.py`

Ответы для нашего проекта:

| Вопрос | Ответ |
|---|---|
| Драйвер и адрес | `asyncpg`; `postgresql+asyncpg://user:secret@127.0.0.1:5432/pg_test_db` с компьютера, `...@pg_database:5432/...` из контейнера `api` |
| Подключение | `create_async_engine(DATABASE_URL)` |
| Сессия | `async_sessionmaker(engine, expire_on_commit=False)`; `get_session` выдаёт новую сессию на каждый запрос и закрывает после ответа |
| Таблица | `payment_statistic.users`: `id`, `name`, `age`, `description` → класс `User` |
| Что API принимает и отдаёт | `UserCreate`, `UserUpdate` — на вход; `UserRead` — на выход |
| Запросы | `BaseRepository` (get, list, create, update, delete) + `UserRepository` (find_by_name) |
| Транзакция | Начинается сама при первом запросе в сессии; `await session.commit()` в обработчиках, которые что-то меняют |

Итоговая структура папки `app/`:

```text
app/
├── __init__.py
├── main.py              ← создаёт FastAPI и подключает роутер
├── config.py            ← вопрос 1: адрес базы
├── database.py          ← вопросы 2–3: engine, фабрика сессий, get_session
├── models/              ← вопрос 4: как таблицы выглядят в Python
│   ├── __init__.py
│   ├── base.py
│   └── user.py
├── schemas/             ← вопрос 5: что API принимает и отдаёт
│   ├── __init__.py
│   └── user.py
├── repositories/        ← вопрос 6: запросы к таблицам
│   ├── __init__.py
│   ├── base.py
│   └── user.py
└── api/                 ← вопрос 7: зависимости и эндпоинты
    ├── __init__.py
    ├── dependencies.py
    └── users.py
```

> **Проверь себя.** Почему `models/` и `schemas/` — разные папки? Ведь и там, и там описан «пользователь с именем и возрастом».
>
> <details><summary>Ответ</summary>
>
> Это разные вещи с разными задачами. Модель описывает **таблицу**: какие колонки есть в базе. Схема описывает **договор с клиентом API**: что можно прислать и что вернётся. Они совпадают только сейчас, пока проект маленький. Когда появится колонка `password_hash`, она будет в модели, но её **не должно** быть ни в одной схеме: иначе API отдаст хеш пароля наружу. А `UserCreate` не содержит `id`, хотя в таблице он есть: id назначает база, а не клиент.
>
> </details>

---

## 4. Подготовь инструменты

**База из прошлого урока должна работать.** Запусти её и проверь таблицу. Имя пользователя и базы возьми из своего `.env` (в `.env.example` это `user` и `pg_test_db`):

```sh
docker compose up -d --wait pg_database
docker compose exec pg_database psql -U user -d pg_test_db -c "\d payment_statistic.users"
```

**Ожидаемо:** описание таблицы с колонками `id`, `name`, `age`, `description` и ограничением `users_age_check`. Если видишь `Did not find any relation named "payment_statistic.users"`, значит volume создан раньше, чем появился `02_table_users.sql`: стартовые скрипты выполняются только на пустой базе. Вернись в раздел 7 урока по Postgres.

**Поставь библиотеки** в `.venv` проекта (активируй его, как в прошлых уроках):

```sh
python -m pip install "sqlalchemy[asyncio]~=2.1.4" "asyncpg~=0.32.0"
python -c "import sqlalchemy, asyncpg; print(sqlalchemy.__version__, asyncpg.__version__)"
```

**Ожидаемо:** `2.1.4 0.32.0`.

- `sqlalchemy[asyncio]` — SQLAlchemy вместе с `greenlet`, без которого асинхронная часть не работает. Без `[asyncio]` асинхронный код упадёт на первом запросе.
- `asyncpg` — асинхронный драйвер PostgreSQL. `psycopg` из прошлого урока тоже умеет асинхронно, но `asyncpg` — самый частый выбор с FastAPI.

**Песочница.** Опыты разделов 5–6 пиши в папке `sandbox/` в корне. Она уже есть в `.gitignore`, в git не попадёт.

---

## 5. Шаг ноль: ORM руками в одном файле

Главный приём, как и в прошлых уроках: **сначала делаешь руками, потом раскладываешь по файлам.** Здесь нет FastAPI, нет репозиториев — только SQLAlchemy и база. Так ты увидишь, что делает каждая строка.

### 5.1. Engine и первое подключение

Создай **`sandbox/step0.py`**:

```python
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "postgresql+asyncpg://user:secret@127.0.0.1:5432/pg_test_db",
    echo=True,
)


async def main():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, name, age FROM payment_statistic.users"))
        for row in result:
            print(row)
    await engine.dispose()


asyncio.run(main())
```

- **Адрес** состоит из тех же пяти частей, что в прошлом уроке, плюс **диалект и драйвер** в начале:

  ```text
  postgresql+asyncpg://user:secret@127.0.0.1:5432/pg_test_db
  └──┬─────┘ └──┬──┘   └┬─┘ └─┬──┘ └───┬───┘ └┬─┘ └───┬────┘
   диалект   драйвер  польз. пароль    хост   порт   база
  ```

  Диалект говорит SQLAlchemy, на каком «наречии» SQL писать запросы. Драйвер — какой библиотекой отправлять их по сети.
- `create_async_engine(...)` — создать engine. **Подключения при этом ещё нет**: engine подключается при первом запросе.
- `echo=True` — печатать каждый SQL-запрос.
- `async def main()` и `asyncio.run(main())` — асинхронный код живёт внутри `async def`, а `asyncio.run` его запускает. В FastAPI это делает сам Uvicorn.
- `async with engine.connect() as conn` — взять подключение из пула и вернуть его в конце блока.
- `text("...")` — «это готовый SQL, отправь как есть». Без ORM: сырой SQL, как в `psycopg`.
- `await engine.dispose()` — закрыть все подключения пула перед выходом.

```sh
python sandbox/step0.py
```

**Ожидаемо:** несколько служебных запросов (`select pg_catalog.version()`, `select current_schema()`, `show standard_conforming_strings` — так SQLAlchemy знакомится с сервером при первом подключении), затем `BEGIN (implicit)`, твой `SELECT`, строки таблицы (если таблица пустая — строк не будет) и `ROLLBACK`.

> **Почему в конце `ROLLBACK`, если мы ничего не меняли?**
>
> <details><summary>Ответ</summary>
>
> SQLAlchemy **всегда** работает внутри транзакции: она начинается сама перед первым запросом (`BEGIN (implicit)`). Мы её не зафиксировали (`commit`), поэтому при возврате подключения в пул SQLAlchemy её откатывает. Для чтения это ничего не меняет, а для записи — это то место, где теряются данные, если забыть `commit`.
>
> </details>

> **Предскажи:** замени в адресе `postgresql+asyncpg://` на `postgresql://` и запусти. Что будет?
>
> <details><summary>Ответ</summary>
>
> ```text
> ModuleNotFoundError: No module named 'psycopg'
> ```
>
> Без `+asyncpg` SQLAlchemy берёт драйвер PostgreSQL по умолчанию — `psycopg`, который мы не ставили. А если `psycopg` у тебя остался после прошлого урока, ошибки не будет вовсе: SQLAlchemy молча подключится через него, а не через `asyncpg`, который ты выбрал. Вывод: **драйвер всегда пиши в адресе явно**.
>
> </details>

### 5.2. Модель: описываем таблицу классом

Теперь то же самое через ORM. Создай **`sandbox/orm_playground.py`** — верхняя часть будет общей для всех опытов этого раздела:

```python
import asyncio

from sqlalchemy import Text, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

URL = "postgresql+asyncpg://user:secret@127.0.0.1:5432/pg_test_db"
engine = create_async_engine(URL, echo=True)
Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "payment_statistic"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    age: Mapped[int]
    description: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name!r}, age={self.age})"
```

Разберём по строкам:

- `class Base(DeclarativeBase)` — общий предок всех моделей. Через него SQLAlchemy собирает список всех таблиц проекта (`Base.metadata`). Пустой класс — это нормально.
- `__tablename__ = "users"` — имя таблицы. **Обязательно.**
- `__table_args__ = {"schema": "payment_statistic"}` — схема PostgreSQL, в которой лежит таблица. Без этой строки SQLAlchemy будет искать `public.users`.
- `Mapped[int]` — **аннотация типа**: какой тип у атрибута в Python. По ней SQLAlchemy понимает и тип колонки, и можно ли в ней `NULL`.
- `mapped_column(...)` — дополнительные настройки колонки: первичный ключ, точный тип SQL, значение по умолчанию. Если настроек нет, `mapped_column` можно не писать (как у `age`).
- `__repr__` — как объект печатается в `print`. Для ORM не нужен, нужен тебе — видеть, что происходит.

Как аннотация превращается в колонку:

| Аннотация | Колонка | Почему |
|---|---|---|
| `id: Mapped[int] = mapped_column(primary_key=True)` | `INTEGER PRIMARY KEY` | Первичный ключ; значение назначает база (`SERIAL`) |
| `name: Mapped[str] = mapped_column(Text)` | `TEXT NOT NULL` | `str` без `None` — значит, `NULL` нельзя |
| `age: Mapped[int]` | `INTEGER NOT NULL` | Тип выведен из аннотации |
| `description: Mapped[str \| None] = mapped_column(Text)` | `TEXT` (можно `NULL`) | `\| None` — значит, `NULL` можно |

`Text` указан явно, потому что для `str` SQLAlchemy по умолчанию берёт `VARCHAR`. Для чтения существующей таблицы разница не важна, но модель должна честно описывать таблицу.

> **Важно:** этот код **не создаёт** таблицу и не проверяет, что она такая. Он только говорит SQLAlchemy: «вот так выглядит таблица, которая уже есть». Если ошибиться в имени колонки, ошибку покажет первый же запрос.

### 5.3. Сессия: создаём строку

Допиши в `orm_playground.py` функцию и запуск:

```python
async def main():
    async with Session() as session:
        anna = User(name="Anna", age=30)
        print(">>> 1. создан объект:", anna)
        session.add(anna)
        print(">>> 2. после add:", anna)
        await session.flush()
        print(">>> 3. после flush:", anna)
        await session.commit()
        print(">>> 4. после commit:", anna)
    await engine.dispose()


asyncio.run(main())
```

- `async_sessionmaker(engine, ...)` (наверху файла) — **фабрика сессий**: настраивается один раз, а `Session()` каждый раз выдаёт новую сессию.
- `async with Session() as session` — открыть сессию и **закрыть** её в конце блока. При закрытии всё незафиксированное откатывается.
- `session.add(anna)` — отдать объект сессии под наблюдение. **Без `await`**: в базу ничего не идёт.
- `await session.flush()` — отправить накопленные изменения в базу **внутри текущей транзакции**, но не фиксировать её.
- `await session.commit()` — сначала `flush`, потом `COMMIT`: изменения зафиксированы, их видят все.

> **Предскажи до запуска:** между какими строками `>>>` появится `INSERT`? Когда у `anna` появится `id`?
>
> <details><summary>Ответ</summary>
>
> ```text
> >>> 1. создан объект: User(id=None, name='Anna', age=30)
> >>> 2. после add: User(id=None, name='Anna', age=30)
> ... BEGIN (implicit)
> ... INSERT INTO payment_statistic.users (name, age, description) VALUES ($1::VARCHAR, $2::INTEGER, $3::VARCHAR) RETURNING payment_statistic.users.id
> ... [generated in 0.00029s] ('Anna', 30, None)
> >>> 3. после flush: User(id=3, name='Anna', age=30)
> ... COMMIT
> >>> 4. после commit: User(id=3, name='Anna', age=30)
> ```
>
> `add` ничего не отправляет. `INSERT` уходит только на `flush`, и в этот момент база назначает `id` и возвращает его (`RETURNING ... id`). SQLAlchemy сам записывает его в `anna.id`. Число у тебя будет своё. `COMMIT` — только на `commit`.
>
> `$1`, `$2`, `$3` — это **параметры**: значения передаются отдельно от текста запроса (`('Anna', 30, None)`). Поэтому SQL-инъекция через `name` невозможна.
>
> </details>

Объект за это время прошёл три состояния:

| Состояние | Когда | `id` | В базе |
|---|---|---|---|
| transient (новый) | Создан `User(...)`, сессия о нём не знает | `None` | Нет |
| pending (ожидает) | После `session.add` | `None` | Нет |
| persistent (сохранён) | После `flush`: строка есть в транзакции | Есть | Да, в текущей транзакции; после `commit` — для всех |

### 5.4. Читаем: `get`, `select` и карта объектов

Замени тело `main()` (верхнюю часть файла не трогай):

```python
async def main():
    async with Session() as session:
        a = await session.get(User, 1)
        print(">>> a:", a)
        b = await session.get(User, 1)
        print(">>> b:", b, "| a is b:", a is b)
        c = (await session.scalars(select(User).where(User.name == "Anna"))).first()
        print(">>> c is a:", c is a)
    await engine.dispose()
```

Если пользователя с `id=1` нет, подставь `id`, который напечатал опыт 5.3.

- `session.get(User, 1)` — найти строку по первичному ключу.
- `select(User).where(User.name == "Anna")` — построить запрос. `User.name == "Anna"` — не сравнение, а кусок SQL `WHERE name = $1`: SQLAlchemy переопределил `==` у атрибутов модели.
- `session.scalars(...)` — выполнить запрос и выдавать результат объектами `User`. `.first()` — первый или `None`, `.all()` — список всех.

> **Предскажи:** сколько `SELECT` будет в логе? Что напечатают `a is b` и `c is a`?
>
> <details><summary>Ответ</summary>
>
> **Два** `SELECT`: для первого `get` и для `select`. Второй `get` в базу **не ходил**. `a is b` — `True`, `c is a` — `True` (если первая Anna в таблице — та, что с `id=1`).
>
> Внутри сессии есть **карта объектов** (identity map): «строка с таким первичным ключом → вот этот объект в памяти». `get` сначала смотрит в карту и, если объект уже загружен, возвращает его без запроса. `select` всегда идёт в базу, но, получив строку с уже известным `id`, возвращает **тот же** объект, а не копию.
>
> Зачем это нужно: в одной сессии одна строка таблицы — это всегда один объект. Не бывает так, что ты изменил `a`, а в `b` осталось старое значение.
>
> </details>

### 5.5. Меняем: просто присвой атрибут

```python
async def main():
    async with Session() as session:
        anna = await session.get(User, 1)
        anna.age = 40
        print(">>> изменённые объекты:", session.dirty)
        await session.commit()
    await engine.dispose()
```

**Ожидаемо:**

```text
>>> изменённые объекты: IdentitySet([User(id=1, name='Anna', age=40)])
... UPDATE payment_statistic.users SET age=$1::INTEGER WHERE payment_statistic.users.id = $2::INTEGER
... [generated in 0.00020s] (40, 1)
... COMMIT
```

Нет ни `save()`, ни `update()`. Сессия **сама** заметила, что у загруженного объекта поменялся атрибут (`session.dirty` — список изменённых), и на `commit` отправила `UPDATE`. Причём только с колонкой `age`: остальные не менялись. Этот механизм называется **Unit of Work** («единица работы»): сессия копит все изменения и отправляет их одной пачкой.

### 5.6. Забыли `commit`

```python
async def main():
    async with Session() as session:
        anna = await session.get(User, 1)
        anna.age = 99
    async with Session() as session:
        print(">>> возраст в базе:", (await session.get(User, 1)).age)
    await engine.dispose()
```

> **Предскажи:** что напечатается — `99` или старое значение? Найди в логе, что случилось с изменением.
>
> <details><summary>Ответ</summary>
>
> Старое значение (`40`). В логе первой сессии — `SELECT` и сразу `ROLLBACK`; `UPDATE` нет вообще. Изменение жило только в памяти, а при закрытии сессии без `commit` всё незафиксированное выбрасывается. **Ни одна ошибка об этом не сообщит** — данные просто не сохранятся. Это ловушка номер один.
>
> </details>

### 5.7. `rollback` и первая встреча с `MissingGreenlet`

```python
async def main():
    async with Session() as session:
        anna = await session.get(User, 1)
        anna.age = 77
        await session.flush()
        await session.rollback()
        print(">>> после rollback:", anna.age)
    await engine.dispose()
```

> **Предскажи:** `UPDATE` уйдёт в базу? Что напечатает последняя строка?
>
> <details><summary>Ответ</summary>
>
> `UPDATE ... (77, 1)` уйдёт на `flush`, но следом будет `ROLLBACK` — и в базе останется старое значение. А последняя строка упадёт:
>
> ```text
> sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_() here. Was IO attempted in an unexpected place?
> ```
>
> После `rollback` сессия помечает все свои объекты как **устаревшие** (expired): значения в памяти могут не совпадать с базой. При чтении устаревшего атрибута SQLAlchemy хочет **тихо** перечитать его из базы. В синхронном коде это сработало бы, а в асинхронном поход в базу без `await` невозможен — отсюда ошибка. В переводе: «ты попытался сходить в базу там, где нет `await`».
>
> Исправление — перечитать объект явно:
>
> ```python
> await session.rollback()
> await session.refresh(anna)
> print(">>> после rollback:", anna.age)   # 40
> ```
>
> </details>

`MissingGreenlet` — самая частая ошибка асинхронного SQLAlchemy. Запомни перевод: **«где-то атрибут объекта захотел сходить в базу без `await`»**. Ищи: объект после `rollback`, после `commit` (раздел 6.5) или после закрытия сессии.

### 5.8. Удаляем

```python
async def main():
    async with Session() as session:
        anna = await session.get(User, 1)
        await session.delete(anna)
        await session.commit()
    await engine.dispose()
```

**Ожидаемо:** `SELECT`, затем `DELETE FROM payment_statistic.users WHERE payment_statistic.users.id = $1::INTEGER` и `COMMIT`. Чтобы удалить, объект сначала нужно загрузить: сессия удаляет **объекты**, которые знает.

### Итог: что с `await`, а что без

| Вызов | `await` | Почему |
|---|---|---|
| `session.add(obj)` | Нет | Только кладёт объект в сессию, в базу не ходит |
| `session.get(...)`, `session.scalars(...)`, `session.execute(...)` | Да | Идут в базу |
| `session.flush()`, `session.commit()`, `session.rollback()` | Да | Идут в базу |
| `session.delete(obj)` | Да | Может понадобиться загрузить связанные данные |
| `session.refresh(obj)` | Да | Перечитывает объект из базы |
| `result.all()`, `result.first()` | Нет | Результат уже получен |
| `obj.age = 40` | Нет | Просто меняет объект в памяти |

Правило: **всё, что может пойти в базу, вызывается с `await`**. Забытый `await` не всегда падает сразу — что получается, разберём в разделе 9.

---

## 6. Сессии подробно

Сессия — центральная идея урока. Разберём её отдельно, с примерами.

### 6.1. Engine, подключение, сессия — кто есть кто

```text
Приложение
  └── engine (один)                      ← адрес базы + пул подключений
        └── пул: [подключение 1] [подключение 2] ... (по умолчанию до 5 постоянных и ещё 10 временных)
              ▲
              │ сессия берёт подключение на время транзакции и возвращает
              │
  session_factory() → сессия на запрос 1
  session_factory() → сессия на запрос 2
```

- **Engine** создаётся **один раз** при старте. Создавать engine на каждый запрос — значит каждый раз заново подключаться к базе: медленно, и можно исчерпать лимит подключений.
- **Сессия** — дешёвая. Создаётся на каждую порцию работы и закрывается после неё.
- **Подключение** сессия берёт из пула при первом запросе и возвращает при `commit`, `rollback` или закрытии.

### 6.2. `flush` и `commit`

| | `flush` | `commit` |
|---|---|---|
| Отправляет SQL в базу | Да | Да (сначала делает `flush`) |
| Фиксирует транзакцию | Нет | Да |
| Видят ли изменения другие подключения | Нет | Да |
| Можно ли отменить через `rollback` | Да | Нет |
| Когда нужен | Получить `id` новой строки; проверить ограничения базы до `commit` | Конец порции работы |

SQLAlchemy ещё и сам делает `flush` перед каждым запросом (**autoflush**): если ты добавил пользователя и сразу ищешь его через `select`, он найдётся.

### 6.3. Четыре способа открыть сессию

**Способ 1. Ручной `commit`** — так в нашем проекте:

```python
async with session_factory() as session:
    session.add(User(name="Anna", age=30))
    await session.commit()          # забудешь эту строку — ничего не сохранится
```

**Способ 2. Блок транзакции `session.begin()`** — `commit` в конце блока сам, `rollback` при исключении сам:

```python
async with session_factory() as session:
    async with session.begin():
        session.add(User(name="Tmp", age=1))
    # здесь уже был COMMIT
```

Проверь откат: добавь пользователя с `age=-5` (в таблице ограничение `age >= 0`):

```python
async with session_factory() as session:
    try:
        async with session.begin():
            session.add(User(name="Bad", age=-5))
    except Exception as e:
        print(">>>", type(e).__name__)
```

**Ожидаемо:** `>>> IntegrityError`, а в тексте ошибки — `new row for relation "users" violates check constraint "users_age_check"`. Транзакция откачена, строки `Bad` в таблице нет.

**Способ 3. Короткая запись способа 2:**

```python
async with session_factory.begin() as session:
    session.add(User(name="Anna", age=30))
```

**Способ 4. Зависимость FastAPI** — сессия на один HTTP-запрос. Это шаг 3 раздела 7:

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
```

Какой выбрать: в скриптах и фоновых задачах удобнее способ 2 или 3 — не забудешь `commit`. В FastAPI сессию даёт способ 4, а `commit` пишется в обработчике (способ 1). Почему не в зависимости — увидишь в разделе 8.

### 6.4. Жизнь объекта в сессии

| Состояние | Как попасть | Что значит |
|---|---|---|
| transient | `User(...)` | Обычный объект, сессия о нём не знает |
| pending | `session.add(obj)` | Сессия запомнит его и сделает `INSERT` на ближайшем `flush` |
| persistent | После `flush` или загрузки через `get` / `select` | Объект связан со строкой таблицы, сессия следит за изменениями |
| deleted | `await session.delete(obj)` и `flush` | Строка удалена в текущей транзакции |
| detached | Сессия закрыта | Объект в памяти остался, но сессии у него нет: изменения больше никуда не уйдут |

### 6.5. `expire_on_commit=False` — зачем эта настройка

По умолчанию после `commit` сессия помечает все объекты как устаревшие, как после `rollback` в опыте 5.7: «транзакция закончилась, другие могли поменять строку — перечитаю при следующем обращении». В асинхронном коде это перечитывание и даёт `MissingGreenlet`.

Проверь: в опыте 5.5 создай фабрику без настройки, `async_sessionmaker(engine)`, и после `commit` напечатай `anna.age`.

<details><summary>Что будет</summary>

```text
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_() here. ...
```

А в FastAPI мы как раз возвращаем объект **после** `commit`, чтобы превратить его в JSON. Поэтому в проекте фабрика создаётся с `expire_on_commit=False`: после `commit` значения в объекте остаются такими, какими были, и читаются без похода в базу.

</details>

### 6.6. После ошибки сессию нужно откатить

```python
async with session_factory() as session:
    session.add(User(name="Bad", age=-5))
    try:
        await session.commit()
    except Exception as e:
        print(">>>", type(e).__name__)
    await session.get(User, 1)
```

**Ожидаемо:** сначала `>>> IntegrityError`, затем на `get` новая ошибка:

```text
sqlalchemy.exc.PendingRollbackError: This Session's transaction has been rolled back due to a previous exception during flush. To begin a new transaction with this Session, first issue Session.rollback().
```

Сессия после ошибки в базе «заблокирована», пока ты явно не скажешь `await session.rollback()`. В FastAPI это обычно не нужно: ошибка заканчивает запрос, а сессия закрывается вместе с ним.

### 6.7. Одна сессия — одна порция работы

- **Не делай одну сессию на всё приложение.** В ней накопятся объекты всех запросов, а ошибка одного запроса сломает остальные.
- **Не используй одну сессию в параллельных задачах.** `await asyncio.gather(session.get(User, 1), session.get(User, 3))` падает с ошибкой вида `IllegalStateChangeError: Method 'close()' can't be called here; method '_connection_for_bind()' is already in progress`. Сессия рассчитана на последовательную работу: одна операция за раз. Нужно параллельно — открой на каждую задачу свою сессию.
- **В FastAPI:** одна сессия на один HTTP-запрос. Это и делает `get_session`.

---

## 7. Собираем проект по одному файлу

Теперь раскладываем опыты по файлам проекта. После каждого шага — проверка. Работаем в папке `app/` на компьютере; в Docker запускаем в шаге 10.

### Шаг 1. Зависимости — `requirements.txt`

```text
fastapi~=0.141.1
pydantic~=2.13.4
uvicorn
sqlalchemy[asyncio]~=2.1.4
asyncpg~=0.32.0
```

**Проверь:** `python -m pip install -r requirements.txt` проходит без ошибок.

### Шаг 2. Адрес базы — `app/config.py`

Вопрос 1: какой драйвер и какой адрес.

```python
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:secret@127.0.0.1:5432/pg_test_db",
)

DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
```

- Тот же приём, что в `check_db.py` из прошлого урока: адрес берётся из переменной окружения, а если её нет — используется значение для твоего компьютера. В Docker переменную задаст `compose.yaml`, и тот же код подключится к `pg_database`.
- `DB_ECHO` — включать ли печать SQL. Переменные окружения — всегда строки, поэтому сравниваем с `"true"`.
- Если в твоём `.env` другие пользователь, пароль или база — поменяй значение по умолчанию или задай переменную: в PowerShell `$env:DATABASE_URL="postgresql+asyncpg://..."`, в Linux shell `export DATABASE_URL=...`.

### Шаг 3. Engine и сессии — `app/database.py`

Вопросы 2 и 3.

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import DATABASE_URL, DB_ECHO

engine = create_async_engine(DATABASE_URL, echo=DB_ECHO)

session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
```

- `engine` и `session_factory` создаются **один раз**, при импорте модуля.
- `get_session` — **генератор с `yield`**. FastAPI вызывает его на каждый запрос: код до `yield` выполняется перед обработчиком, сессия передаётся в обработчик, код после `yield` (здесь — выход из `async with`, то есть закрытие сессии) выполняется в конце запроса.
- `AsyncIterator[AsyncSession]` — аннотация: «эта функция по одному выдаёт объекты `AsyncSession`».

**Проверь** в песочнице, что модуль импортируется и подключается. Создай `sandbox/db_check.py`:

```python
import asyncio

from sqlalchemy import text

from app.database import engine, session_factory


async def main():
    async with session_factory() as session:
        print(await session.scalar(text("SELECT version()")))
    await engine.dispose()


asyncio.run(main())
```

```sh
python -m sandbox.db_check
```

**Ожидаемо:** `PostgreSQL 18.x ...`. Запускай именно через `python -m` из корня: тогда Python найдёт пакет `app`. Если запустить `python sandbox/db_check.py`, будет `ModuleNotFoundError: No module named 'app'`.

### Шаг 4. Модель — `app/models/`

Вопрос 4. Три файла.

**`app/models/base.py`:**

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
```

Отличие от песочницы: колонка `id` объявлена в `Base`. У всех таблиц проекта целочисленный первичный ключ `id`, и каждая модель получит его, не повторяя строку. Заодно базовый репозиторий (шаг 6) сможет писать `self.model.id` для любой модели.

**`app/models/user.py`:**

```python
from sqlalchemy import CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("age >= 0", name="users_age_check"),
        {"schema": "payment_statistic"},
    )

    name: Mapped[str] = mapped_column(Text)
    age: Mapped[int]
    description: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, age={self.age!r})"
```

- `__table_args__` стал **кортежем**: сначала ограничения таблицы, последним — словарь с настройками. Такой порядок обязателен.
- `CheckConstraint` повторяет ограничение из `02_table_users.sql`. Запросы работают и без него, но модель должна честно описывать таблицу: когда позже таблицы будут создаваться миграциями из моделей, ограничение не потеряется.

**`app/models/__init__.py`:**

```python
from app.models.base import Base
from app.models.user import User

__all__ = ["Base", "User"]
```

Одна точка импорта: в остальном коде пишем `from app.models import User`. И главное — при импорте пакета `app.models` загружаются **все** модели, а значит, `Base.metadata` знает обо всех таблицах. Новую модель всегда добавляй сюда.

**Проверь:**

```sh
python -c "from app.models import Base; print(Base.metadata.tables.keys())"
```

**Ожидаемо:** `dict_keys(['payment_statistic.users'])`.

### Шаг 5. Схемы: аннотации, которые принимает и отдаёт API — `app/schemas/`

Вопрос 5. Это то, что видит клиент API и Swagger. Модель описывает таблицу, схема — **договор с клиентом**.

**`app/schemas/user.py`:**

```python
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

UserName = Annotated[str, Field(min_length=1, max_length=100, examples=["Anna"])]
UserAge = Annotated[int, Field(ge=0, le=150, examples=[30])]
UserDescription = Annotated[str | None, Field(max_length=500, examples=["Любит котов"])]


class UserBase(BaseModel):
    name: UserName
    age: UserAge
    description: UserDescription = None


class UserCreate(UserBase):
    """Что клиент присылает, чтобы создать пользователя."""


class UserUpdate(UserBase):
    """Что клиент присылает, чтобы заменить данные пользователя (PUT)."""


class UserRead(UserBase):
    """Что API отдаёт клиенту."""

    model_config = ConfigDict(from_attributes=True)

    id: int
```

Разберём, что здесь происходит.

**`Annotated[тип, правила]`** — способ приклеить к типу дополнительную информацию. Для Python `UserAge` — это просто `int`, а Pydantic и FastAPI читают правила из `Field(...)`:

| Правило | Что значит |
|---|---|
| `min_length=1`, `max_length=100` | Длина строки |
| `ge=0`, `le=150` | Число ≥ 0 и ≤ 150 (`gt`, `lt` — строго больше, строго меньше) |
| `examples=[...]` | Пример значения для Swagger |
| `pattern=r"^\d+$"` | Строка должна подходить под регулярное выражение |
| `default=...` | Значение по умолчанию |

Тип с правилами записан **один раз** (`UserAge`) и используется во всех схемах. Если правило поменяется (возраст до 120), правишь одну строку.

**Наследование схем.** Общие поля — в `UserBase`. `UserCreate` и `UserUpdate` пока такие же, но это **разные договоры**, и они начнут отличаться, когда в API появятся новые поля. `UserRead` добавляет `id`: при создании клиент его не присылает, а в ответе получает.

**`from_attributes=True`** разрешает собирать схему из **атрибутов** объекта, а не только из словаря: `UserRead.model_validate(user)`, где `user` — объект модели. Без этой настройки:

```text
Input should be a valid dictionary or instance of UserRead [type=model_type, input_value=User(id=1, name='A', age=3), input_type=User]
```

**Проверь** в Python-консоли (`python` из корня):

```python
from app.models import User
from app.schemas.user import UserCreate, UserRead

UserCreate(name="Anna", age=30)
UserCreate(name="", age=-1)                       # две ошибки сразу: длина имени и возраст
UserRead.model_validate(User(id=1, name="Anna", age=30))
UserCreate.model_json_schema()["properties"]["age"]
```

Последняя строка покажет, как правила попадут в Swagger: `{'examples': [30], 'maximum': 150, 'minimum': 0, 'title': 'Age', 'type': 'integer'}`.

**`app/schemas/__init__.py`:**

```python
from app.schemas.user import UserCreate, UserRead, UserUpdate

__all__ = ["UserCreate", "UserRead", "UserUpdate"]
```

> **Проверь себя.** В таблице у `age` есть ограничение `CHECK (age >= 0)`. Зачем ещё `ge=0` в схеме? И наоборот: зачем ограничение в базе, если есть схема?
>
> <details><summary>Ответ</summary>
>
> Схема проверяет данные **до** базы и отвечает клиенту понятной ошибкой 422 с именем поля. Без неё запрос дошёл бы до базы, там упал бы `IntegrityError`, и клиент получил бы 500. Ограничение в базе — последняя линия защиты: в базу пишут не только через API (скрипты, `psql`, будущий бот), и база не должна принять неправильные данные ни от кого.
>
> </details>

### Шаг 6. Репозитории — `app/repositories/`

Вопрос 6. Здесь живут **все** запросы к базе. Сначала общий класс, который умеет базовые операции для любой модели, потом — репозиторий пользователей.

**`app/repositories/base.py`:**

```python
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: int) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt = select(self.model).order_by(self.model.id).limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return result.all()

    async def create(self, **values: Any) -> ModelT:
        obj = self.model(**values)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, obj: ModelT, **values: Any) -> ModelT:
        for field, value in values.items():
            setattr(obj, field, value)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()
```

По строкам:

- **`ModelT = TypeVar("ModelT", bound=Base)`** — «переменная для типа»: вместо `ModelT` будет подставлена конкретная модель. `bound=Base` — «только наследник `Base`».
- **`class BaseRepository(Generic[ModelT])`** — класс-шаблон. `BaseRepository[User]` — репозиторий, у которого `get` возвращает `User | None`, `list` — список `User`. Редактор (PyCharm) это понимает и подсказывает атрибуты.
- **`model: type[ModelT]`** — у каждого наследника будет атрибут `model` с классом модели. Его задаёт наследник, а базовые методы работают через `self.model`.
- **`__init__(self, session)`** — репозиторий **не создаёт** сессию, а получает готовую. Значит, несколько репозиториев могут работать в одной сессии и одной транзакции.
- **`*` в `list(self, *, limit, offset)`** — после звёздочки параметры передаются только по имени: `users.list(limit=10)`, а не `users.list(10)`. Так вызов читается без подсказок.
- **`create(**values)`** — принимает поля как именованные аргументы: `users.create(name="Anna", age=30)`. `**values` собирает их в словарь, а `self.model(**values)` раскладывает обратно в конструктор модели.
- **`flush`, а не `commit`.** `flush` отправляет SQL, получает `id` от базы и сразу показывает ошибки ограничений, но **не завершает транзакцию**. Завершит её тот, кто открыл порцию работы.
- **`update` через `setattr`** — `setattr(obj, "age", 31)` то же, что `obj.age = 31`, только имя атрибута берётся из переменной. Сессия сама поймёт, что изменилось (опыт 5.5).

**`app/repositories/user.py`:**

```python
from collections.abc import Sequence

from sqlalchemy import select

from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def find_by_name(self, name: str) -> Sequence[User]:
        stmt = select(User).where(User.name.ilike(f"%{name}%")).order_by(User.id)
        result = await self.session.scalars(stmt)
        return result.all()
```

Всё, что умеет `BaseRepository`, `UserRepository` получил одной строкой `model = User`. Свои методы — только для запросов, специфичных для пользователей. `ilike` — поиск подстроки без учёта регистра (`ILIKE '%an%'`).

**`app/repositories/__init__.py`:**

```python
from app.repositories.base import BaseRepository
from app.repositories.user import UserRepository

__all__ = ["BaseRepository", "UserRepository"]
```

**Как писать красивые репозитории — правила:**

| Правило | Хорошо | Плохо |
|---|---|---|
| Имя метода — на языке задачи | `find_by_name`, `list_adults`, `count_active` | `query1`, `select_users_where` |
| Принимает простые значения | `find_by_name(name: str)` | `find(stmt)` — снаружи собирают SQL сами |
| Возвращает модели или простые значения | `-> Sequence[User]`, `-> int` | `-> Result` — снаружи разбирают сырой результат |
| Не знает про HTTP | Возвращает `None`, если не нашёл | `raise HTTPException(404)` — репозиторий используют ещё и бот, и скрипты |
| Не делает `commit` | `flush` | `commit` |
| Один репозиторий — одна таблица (одна модель) | `UserRepository`, `UserEventRepository` | Один `DatabaseRepository` на всё |
| Всё общее — в `BaseRepository` | `get`, `list`, `create`, `update`, `delete` | Копировать `get` в каждый репозиторий |

**Проверь** без FastAPI. Создай `sandbox/repo_check.py`:

```python
import asyncio

from app.database import engine, session_factory
from app.repositories import UserRepository


async def main():
    async with session_factory() as session:
        users = UserRepository(session)
        bob = await users.create(name="Bob", age=25)
        print("создан:", bob)
        print("поиск 'an':", await users.find_by_name("an"))
        print("все:", await users.list())
        await session.commit()
    await engine.dispose()


asyncio.run(main())
```

```sh
python -m sandbox.repo_check
```

**Ожидаемо:** `создан: User(id=..., name='Bob', age=25)` уже с `id` (это сделал `flush`), список найденных и список всех. Убери `await session.commit()` и запусти снова — Bob напечатается, но в базе его не будет. Верни строку.

### Шаг 7. Зависимости — `app/api/dependencies.py`

Вопрос 7, первая половина: как обработчик получает сессию и репозиторий. Создай пустой `app/api/__init__.py` и файл:

```python
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.repositories import UserRepository

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]


async def get_user_or_404(user_id: int, users: UserRepoDep) -> User:
    user = await users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


UserDep = Annotated[User, Depends(get_user_or_404)]
```

Здесь `Annotated` работает уже для FastAPI:

- **`Depends(get_session)`** говорит FastAPI: «чтобы получить этот параметр, вызови `get_session` и подставь результат».
- **`SessionDep = Annotated[AsyncSession, Depends(get_session)]`** — записываем это один раз. Дальше в любом обработчике пишем `session: SessionDep` — и получаем сессию. Для редактора `session` — это `AsyncSession`, со всеми подсказками.
- **Зависимости могут зависеть друг от друга.** `get_user_repository` просит `SessionDep`, `get_user_or_404` просит `UserRepoDep` и `user_id` из пути. FastAPI сам выстраивает цепочку: сессия → репозиторий → пользователь.
- **Одна сессия на запрос, даже если она нужна в трёх местах.** Если в одном запросе `SessionDep` просят и обработчик, и `get_user_repository`, FastAPI вызовет `get_session` **один раз** и отдаст обоим одну и ту же сессию. Поэтому `commit` в обработчике фиксирует то, что сделал репозиторий.
- **`UserDep`** — самая удобная аннотация: обработчик просто пишет `user: UserDep` и получает **уже загруженного** пользователя. Если его нет, до обработчика дело не дойдёт: ответ 404 отправит зависимость. Проверка «а есть ли такой пользователь» написана один раз вместо трёх.
- `HTTPException` здесь можно: `dependencies.py` — это слой API, он знает про HTTP. В репозитории — нельзя.

### Шаг 8. Эндпоинты — `app/api/users.py`

Вопрос 7, вторая половина: где фиксируется транзакция. Те же пять эндпоинтов, что были в `main.py`, с теми же адресами и параметрами.

```python
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import SessionDep, UserDep, UserRepoDep
from app.models import User
from app.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(tags=["users"])


@router.post("/create_user", response_model=UserRead, status_code=201)
async def create_user(
    data: Annotated[UserCreate, Query()],
    users: UserRepoDep,
    session: SessionDep,
) -> User:
    user = await users.create(**data.model_dump())
    await session.commit()
    return user


@router.get("/users/{user_id}", response_model=UserRead)
async def read_user(user: UserDep) -> User:
    return user


@router.get("/users", response_model=list[UserRead])
async def read_users(
    users: UserRepoDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[User]:
    return list(await users.list(limit=limit, offset=offset))


@router.delete("/users/delete/{user_id}", response_model=UserRead)
async def delete_user(user: UserDep, users: UserRepoDep, session: SessionDep) -> User:
    await users.delete(user)
    await session.commit()
    return user


@router.put("/users/update/{user_id}", response_model=UserRead)
async def update_user(
    user: UserDep,
    data: Annotated[UserUpdate, Query()],
    users: UserRepoDep,
    session: SessionDep,
) -> User:
    await users.update(user, **data.model_dump())
    await session.commit()
    return user
```

По строкам:

- **`APIRouter`** — «кусок приложения»: набор эндпоинтов, который потом подключается к `app`. `tags=["users"]` — группа в Swagger.
- **`async def`** — обработчики стали асинхронными, потому что внутри `await`.
- **`data: Annotated[UserCreate, Query()]`** — схема, поля которой берутся **из query string**: `/create_user?name=Anna&age=30`. Так адреса остались прежними, и фронтенд из урока по Nuxt работает без изменений. Если написать просто `data: UserCreate`, FastAPI будет ждать **JSON в теле запроса** — так делают в новых API (уровень 6 тренировки).
- **`data.model_dump()`** — схема → словарь `{"name": "Anna", "age": 30, "description": None}`, а `**` раскладывает его в именованные аргументы `create`.
- **`response_model=UserRead`** — что отдать клиенту. Обработчик возвращает объект модели `User`, а FastAPI превращает его в `UserRead` и потом в JSON. Лишние поля модели (будущий `password_hash`) в ответ не попадут: в `UserRead` их нет. Эту же схему Swagger показывает в разделе Responses.
- **`-> User`** — аннотация для тебя и редактора: что функция возвращает на самом деле. Для ответа важен `response_model`, он главнее.
- **`status_code=201`** — «создано»: правильный код для создания.
- **`limit`, `offset` с `Query(ge=..., le=...)`** — постраничный вывод: `GET /users?limit=10&offset=20` — пользователи с 21-го по 30-й. Значения по умолчанию сохраняют старое поведение `GET /users`.
- **`await session.commit()`** — в каждом обработчике, который что-то меняет. Читающим обработчикам `commit` не нужен.

> **Предскажи:** что придёт на `POST /create_user?name=X&age=-1`, и дойдёт ли запрос до базы?
>
> <details><summary>Ответ</summary>
>
> ```json
> {"detail":[{"type":"greater_than_equal","loc":["query","age"],"msg":"Input should be greater than or equal to 0","input":"-1","ctx":{"ge":0}}]}
> ```
>
> Код 422. До базы запрос не дошёл: в логе нет ни `BEGIN`, ни `INSERT`. Проверку сделал Pydantic по правилу `ge=0` из `UserAge`.
>
> </details>

### Шаг 9. Приложение — `app/main.py`

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.users import router as users_router
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(users_router)
```

- `main.py` стал коротким: он только собирает приложение. Код эндпоинтов — в `api/`, работа с базой — в `repositories/`.
- **`lifespan`** — что сделать при старте (до `yield`) и при остановке (после `yield`) приложения. При остановке закрываем подключения пула, чтобы база не держала «зависшие» подключения.
- **`include_router`** — подключить эндпоинты из роутера.
- Список `fake_user_database`, `global_id` и класс `User` из старого `main.py` больше не нужны: данные в базе, `id` назначает база, класс модели — в `models/`, схемы — в `schemas/`.

**Проверь на компьютере** (база в Docker, API — нет):

```sh
python -m uvicorn app.main:app --reload
```

В PowerShell, чтобы увидеть SQL, перед запуском выполни `$env:DB_ECHO="true"` (в Linux shell — `DB_ECHO=true python -m uvicorn ...`). Открой <http://127.0.0.1:8000/docs> и пройди все пять эндпоинтов: создай двух пользователей, получи список, обнови одного, удали другого, попробуй удалить его ещё раз (404). После каждого действия смотри SQL в терминале. Останови Uvicorn и запусти снова — **пользователи на месте**. Ради этого урок и был нужен.

### Шаг 10. Docker — `compose.yaml`

Сервис `api` должен знать адрес базы и стартовать только после неё:

```yaml
services:
  api:
    build: .
    image: fastapi-train:local
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./app:/my_code/app
    command: ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    environment:
      WATCHFILES_FORCE_POLLING: "true"
      DATABASE_URL: "postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@pg_database:5432/${POSTGRES_DB}"
      DB_ECHO: "true"
    depends_on:
      pg_database:
        condition: service_healthy
  pg_database:
    # без изменений
```

- **`DATABASE_URL`** собран из тех же переменных `.env`, что и у базы, поэтому пароль хранится в одном месте. Хост — **имя сервиса** `pg_database`: внутри сети Compose базу ищут по нему (раздел 6 урока по Postgres).
- **`DB_ECHO: "true"`** — SQL в логах `api`. Для учёбы удобно; в настоящем продакшене выключают.
- **`depends_on` с `condition: service_healthy`** — `api` запускается только когда `pg_database` прошла `healthcheck`.
- **`./app:/my_code/app`** — исправлена ошибка, которая была в файле: `Dockerfile` кладёт код в `WORKDIR /my_code`, а volume монтировался в `/code/app`. Uvicorn запускался из `/my_code` и правки с компьютера не видел. Теперь папка `app` с компьютера подменяет ту, что внутри образа, и `--reload` срабатывает.

Новые библиотеки в `requirements.txt` — значит, образ нужно пересобрать:

```sh
docker compose up -d --build --wait
docker compose logs -f api
```

Во втором терминале открой <http://127.0.0.1:8000/docs> и повтори проверку шага 9. **Ожидаемо:** в логах `api` видны `BEGIN (implicit)`, запросы и `COMMIT`.

Последняя проверка — данные видны из `psql`:

```sh
docker compose exec pg_database psql -U user -d pg_test_db -c "SELECT * FROM payment_statistic.users"
```

---

## 8. Один запрос целиком

Пройдём по схеме из раздела 1 с настоящими логами. Запрос `PUT /users/update/1?name=Anna&age=31&description=upd`:

```text
INFO sqlalchemy.engine.Engine BEGIN (implicit)
INFO sqlalchemy.engine.Engine SELECT payment_statistic.users.name, payment_statistic.users.age, payment_statistic.users.description, payment_statistic.users.id
FROM payment_statistic.users
WHERE payment_statistic.users.id = $1::INTEGER
INFO sqlalchemy.engine.Engine [cached since 0.03257s ago] (1,)
INFO sqlalchemy.engine.Engine UPDATE payment_statistic.users SET age=$1::INTEGER, description=$2::VARCHAR WHERE payment_statistic.users.id = $3::INTEGER
INFO sqlalchemy.engine.Engine [generated in 0.00026s] (31, 'upd', 1)
INFO sqlalchemy.engine.Engine COMMIT
INFO:     172.18.0.1:43632 - "PUT /users/update/1?name=Anna&age=31&description=upd HTTP/1.1" 200 OK
```

Что произошло, по порядку:

1. **FastAPI проверил параметры** по `UserUpdate`. Ошибся бы — ответ 422, и ни одной строки SQL.
2. **Зависимости:** `get_session` открыл сессию → `get_user_repository` создал `UserRepository(session)` → `get_user_or_404` вызвал `users.get(1)`. Это `BEGIN (implicit)` и `SELECT ... WHERE id = $1` с параметром `(1,)`.
3. **Обработчик** вызвал `users.update(user, name="Anna", age=31, description="upd")`. Репозиторий присвоил атрибуты и сделал `flush` → `UPDATE`. Обрати внимание: `name` в `UPDATE` **нет** — имя не поменялось, и сессия его не отправила.
4. **`await session.commit()`** → `COMMIT`.
5. **`response_model=UserRead`** превратил объект в JSON → `200 OK`.
6. Зависимость `get_session` закрыла сессию, подключение вернулось в пул.

`cached since ...` и `generated in ...` — SQLAlchemy один раз переводит запрос в SQL и потом берёт готовый текст из кеша.

Теперь посмотри на `GET /users/1`:

```text
INFO sqlalchemy.engine.Engine BEGIN (implicit)
INFO sqlalchemy.engine.Engine SELECT ... WHERE payment_statistic.users.id = $1::INTEGER
INFO:     172.18.0.1:43610 - "GET /users/1 HTTP/1.1" 200 OK
INFO sqlalchemy.engine.Engine ROLLBACK
```

> **Почему `ROLLBACK` напечатан после `200 OK`? И что это значит для того, где писать `commit`?**
>
> <details><summary>Ответ</summary>
>
> Код после `yield` в зависимости (закрытие сессии) выполняется **после того, как ответ уже отправлен клиенту**. Для чтения это неважно: транзакцию нечего фиксировать, `ROLLBACK` просто освобождает подключение.
>
> А вот если бы `commit` стоял в `get_session` после `yield`, клиент получал бы `201 Created` **до** того, как данные зафиксированы. Упади `commit` (база недоступна, нарушено ограничение) — клиент уже получил «успешно», а данных нет. Поэтому в проекте `commit` пишется в обработчике: если он упадёт, клиент получит ошибку 500, а не ложный успех.
>
> </details>

---

## 9. Правила, на которых ошибаются при написании с нуля

### Забыли `commit` — данные молча пропадают

Ответ 201, у пользователя даже есть `id`, а `GET /users` его не находит. В логе после `INSERT` идёт не `COMMIT`, а `ROLLBACK`. Ошибки нет. Признак: **в каждом обработчике, который меняет данные, должен быть `await session.commit()`.** Заодно увидишь, что `id` «сгорел»: следующий пользователь получит `id` на единицу больше. Последовательность `SERIAL` не откатывается вместе с транзакцией, и дырки в `id` — это нормально.

### Забыли `await`

```python
return self.session.get(self.model, id_)     # без await
```

Python не ругается: функция вернула не пользователя, а **корутину** — «обещание» выполнить запрос. Она не `None`, поэтому проверка на 404 проходит, и ошибка вылезает позже:

```text
fastapi.exceptions.ResponseValidationError: ... 'input': <coroutine object AsyncSession.get at 0x...>
RuntimeWarning: coroutine 'AsyncSession.get' was never awaited
```

Клиент получает 500. Если в ошибке есть слово `coroutine` — ищи пропущенный `await`.

### Модель не совпадает с таблицей

Модель не проверяется при старте. Добавишь в модель колонку `email`, которой нет в таблице, — приложение запустится, а первый запрос упадёт:

```text
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) column users.email does not exist
```

Сначала меняется **таблица** (SQL-скриптом или миграцией), потом **модель**.

### Нет схемы в `__table_args__`

Забыл `{"schema": "payment_statistic"}` — SQLAlchemy ищет `public.users`: `relation "users" does not exist`.

### `MissingGreenlet`

«Атрибут объекта захотел сходить в базу без `await`». Три причины: фабрика без `expire_on_commit=False`; обращение к объекту после `rollback` без `refresh`; связанные объекты (появятся, когда будут связи между таблицами), которые не загружены заранее.

### `PendingRollbackError`

После ошибки базы сессия ждёт `await session.rollback()`. В FastAPI сессия живёт один запрос, поэтому достаточно не продолжать работу с ней после пойманного исключения.

### ORM-модель как тип ответа без `response_model`

```python
@app.get("/x")
async def x() -> User: ...
```

падает **при старте**: `FastAPIError: Invalid args for response field! Hint: check that <class 'app.models.user.User'> is a valid Pydantic field type`. FastAPI умеет строить ответ только по Pydantic-схемам. Указывай `response_model=UserRead`.

### Модель как схема запроса

Никогда не принимай на вход класс модели и не отдавай модель «как есть». Схемы отделяют то, что хранится, от того, что видит клиент. Иначе однажды в ответ уйдёт `password_hash`, а на вход клиент пришлёт `id` или `is_admin=true`.

### `from_attributes`

FastAPI собирает `response_model` из объекта модели сам, поэтому эндпоинты работают даже без `from_attributes=True` в `UserRead`. Но как только ты сам напишешь `UserRead.model_validate(user)` (в боте, в скрипте, в тесте), без настройки будет ошибка. Держи её в каждой схеме, которая собирается из модели.

### Драйвер и хост в адресе

`postgresql://` вместо `postgresql+asyncpg://` → `ModuleNotFoundError: No module named 'psycopg'`. Хост `127.0.0.1` — с компьютера; `pg_database` — из контейнера. Перепутаешь в `compose.yaml` — приложение **запустится**, а первый запрос упадёт с `ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5432)`: engine подключается не при старте, а при первом запросе.

### Особые символы в пароле

Пароль подставляется прямо в адрес. Если в нём есть `@`, `:`, `/`, `#` или `%`, адрес будет прочитан неправильно. Для учёбы используй пароль из букв и цифр. Для настоящего пароля такие символы кодируют (`@` → `%40`) или собирают адрес из частей через `sqlalchemy.URL.create(...)`.

### Порядок эндпоинтов

Если `GET /users/search` объявлен **после** `GET /users/{user_id}`, запрос `/users/search?name=an` попадёт во второй: FastAPI проверяет маршруты по порядку, а `{user_id}` подходит под любое слово. Ответ: 422 `Input should be a valid integer, unable to parse string as an integer`, `"input": "search"`. Конкретные пути объявляй раньше путей с параметрами.

### Как посмотреть, что получилось

```sh
docker compose logs api | findstr "UPDATE INSERT DELETE COMMIT ROLLBACK"
```

(в Linux shell — `grep -E "UPDATE|INSERT|DELETE|COMMIT|ROLLBACK"`). По этим строкам видно, какие изменения ушли в базу и зафиксированы ли они.

---

## 10. Диагностика: сначала найди этап

Любую проблему сначала относи к этапу: **импорт и старт → подключение → SQL → сессия → ответ API**.

| Симптом | Этап | Что проверить |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | импорт | Запускаешь из корня? Скрипт в песочнице — через `python -m sandbox.имя` |
| `ModuleNotFoundError: No module named 'sqlalchemy'` / `'asyncpg'` | импорт | Активирован ли `.venv`; в Docker — пересобран ли образ (`--build`) |
| `ModuleNotFoundError: No module named 'psycopg'` | импорт | В адресе нет `+asyncpg` |
| `FastAPIError: Invalid args for response field!` | старт | Тип ответа — ORM-модель без `response_model` |
| `ConnectionRefusedError: ... ('127.0.0.1', 5432)` | подключение | Запущена ли база; в Docker — хост `pg_database`, а не `127.0.0.1` |
| `socket.gaierror` (`Name or service not known`, на Windows `getaddrinfo failed`) | подключение | Хост `pg_database` с компьютера не виден: используй `127.0.0.1` |
| `password authentication failed for user "user"` | подключение | Пароль в `DATABASE_URL` и в базе; менял после первого запуска — `ALTER USER` (урок по Postgres) |
| `database "..." does not exist` | подключение | Имя базы в адресе |
| `relation "users" does not exist` | SQL | `__table_args__` со схемой; есть ли таблица (`\dt payment_statistic.*`) |
| `column users.email does not exist` | SQL | Модель не совпадает с таблицей |
| `IntegrityError ... violates check constraint` | SQL | Данные нарушили ограничение базы. Почему их не остановила схема? |
| `MissingGreenlet` | сессия | `expire_on_commit=False`; обращение к объекту после `rollback` |
| `ResponseValidationError: <exception str() failed>`, а `COMMIT` в логе есть | сессия | Нет `expire_on_commit=False`: ответ собирается из устаревшего объекта |
| `PendingRollbackError` | сессия | Работа с сессией после ошибки без `rollback` |
| Ответ 2xx, но данных нет | сессия | `commit` в обработчике; в логе `ROLLBACK` вместо `COMMIT` |
| `ResponseValidationError ... coroutine` | ответ API | Пропущен `await` |
| 422 на правильный запрос | ответ API | Порядок маршрутов; где FastAPI ищет параметр — в query, в пути или в теле |

---

## 11. Тренировка: от простого к переносу навыка

### Уровень 1. С пустого листа

Переименуй папку `app` в `app_old`. Не открывая урок, напиши `app/` заново, опираясь только на семь вопросов из раздела 3. Запусти `docker compose up -d --build --wait`, пройди все пять эндпоинтов в Swagger. Засеки время.

**Критерий:** всё работает, в логах `api` видны `INSERT`, `UPDATE`, `DELETE` и `COMMIT`, и ты вслух объясняешь каждую строку `database.py`, `BaseRepository` и `dependencies.py`. Цель — 30 минут. Потом удали `app_old`.

### Уровень 2. Свой метод репозитория

Сделай эндпоинт `GET /users/search?name=an`, который ищет пользователей по части имени через `UserRepository.find_by_name`. Перед тем как писать, ответь: где должен стоять новый эндпоинт в `users.py` и почему?

<details><summary>Ответ</summary>

```python
@router.get("/users/search", response_model=list[UserRead])
async def search_users(
    name: Annotated[str, Query(min_length=1)],
    users: UserRepoDep,
) -> list[User]:
    return list(await users.find_by_name(name))
```

Он должен стоять **выше** `GET /users/{user_id}`, иначе `search` будет принят за `user_id` (раздел 9). `commit` не нужен: эндпоинт только читает.

</details>

### Уровень 3. Частичное обновление (PATCH)

`PUT` заменяет **все** поля. Сделай `PATCH /users/{user_id}`, который меняет **только присланные**: `PATCH /users/1?age=50` меняет возраст и не трогает имя. Нужна новая схема `UserPatch`. Подсказка: у `model_dump` есть параметр `exclude_unset`.

<details><summary>Ответ</summary>

```python
class UserPatch(BaseModel):
    name: UserName | None = None
    age: UserAge | None = None
    description: UserDescription = None
```

```python
@router.patch("/users/{user_id}", response_model=UserRead)
async def patch_user(
    user: UserDep,
    data: Annotated[UserPatch, Query()],
    users: UserRepoDep,
    session: SessionDep,
) -> User:
    await users.update(user, **data.model_dump(exclude_unset=True))
    await session.commit()
    return user
```

Все поля необязательные, но с теми же правилами (`UserName`, `UserAge`). `exclude_unset=True` оставляет в словаре только поля, которые клиент **прислал**: `{"age": 50}`. Без него получится `{"name": None, "age": 50, "description": None}`, и `UPDATE` попытается записать `NULL` в `name` — база ответит `IntegrityError: null value in column "name" of relation "users" violates not-null constraint`. В логе `UPDATE` будет только с колонкой `age`. Не забудь добавить `UserPatch` в `app/schemas/__init__.py`.

</details>

### Уровень 4. Сломай специально

По очереди внеси одну поломку, **предскажи симптом**, проверь (Swagger + `docker compose logs api`), верни рабочий вариант:

1. В `BaseRepository.get` убери `await`. Запроси несуществующего пользователя `GET /users/99`.
2. В `database.py` убери `expire_on_commit=False`. Создай пользователя.
3. В `create_user` закомментируй `await session.commit()`. Создай пользователя, потом получи список.
4. В `compose.yaml` в `DATABASE_URL` замени `pg_database` на `127.0.0.1`. Как долго приложение будет «здоровым»?
5. В модели `User` добавь `email: Mapped[str]`.
6. В модели `User` убери `{"schema": "payment_statistic"}` из `__table_args__`.

<details><summary>Ответ</summary>

1. Ответ 500, а не 404. В логе `ResponseValidationError ... <coroutine object AsyncSession.get ...>` и `RuntimeWarning: coroutine 'AsyncSession.get' was never awaited`. Корутина — не `None`, поэтому проверка на 404 её пропустила.
2. Пользователь **создан** (`INSERT` и `COMMIT` в логе), но ответ — 500, а в логе `ResponseValidationError: <exception str() failed>`. Внутри — тот же `MissingGreenlet`: после `commit` объект устарел, и когда FastAPI собирал ответ, атрибуты захотели перечитаться из базы без `await`. Клиент думает, что ничего не создалось, а строка в базе есть.
3. Ответ 201 с `id`, а в списке пользователя нет. В логе после `INSERT` — `ROLLBACK`. Следующий созданный пользователь получит `id` через один.
4. `api` стартует и работает, пока не придёт первый запрос к базе: тогда 500 и `ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5432)`. Внутри контейнера `127.0.0.1` — это сам контейнер `api`.
5. Старт без ошибок, первый же запрос — `column users.email does not exist`.
6. `relation "users" does not exist`: без схемы SQLAlchemy ищет `public.users`.

</details>

### Уровень 5. Вторая таблица и одна транзакция на два репозитория

При создании и удалении пользователя записывай событие в таблицу `logs.user_events` (схема `logs` уже создана скриптом `01_schema_logs.sql`). Удаление пользователя и запись события должны происходить **в одной транзакции**: либо оба, либо ни одного.

1. Создай `database/init/03_table_user_events.sql`:

   ```sql
   CREATE TABLE logs.user_events
   (
       id         SERIAL PRIMARY KEY,
       user_id    INTEGER     NOT NULL,
       action     TEXT        NOT NULL,
       created_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );
   ```

   Стартовые скрипты выполняются только на пустой базе. Чтобы не терять данные, выполни новый скрипт руками — папка `database/init` уже смонтирована в контейнер:

   ```sh
   docker compose exec pg_database psql -U user -d pg_test_db -f /docker-entrypoint-initdb.d/03_table_user_events.sql
   ```

2. Модель `UserEvent`, репозиторий `UserEventRepository` с методом `log(user_id, action)`, зависимость `UserEventRepoDep`.
3. В `create_user` и `delete_user` — запись события.
4. **Докажи атомарность:** временно добавь в `delete_user` между записью события и `commit` строку `raise RuntimeError("boom")`. Предскажи: удалится ли пользователь? Появится ли событие?

<details><summary>Ответ</summary>

`app/models/user_event.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserEvent(Base):
    __tablename__ = "user_events"
    __table_args__ = {"schema": "logs"}

    user_id: Mapped[int]
    action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

`server_default=func.now()` — значение назначает **база** (`DEFAULT now()`), а не Python. После `flush` SQLAlchemy получает его через `RETURNING`, и `event.created_at` сразу доступен. Добавь `UserEvent` в `app/models/__init__.py`.

`app/repositories/user_event.py`:

```python
from app.models import UserEvent
from app.repositories.base import BaseRepository


class UserEventRepository(BaseRepository[UserEvent]):
    model = UserEvent

    async def log(self, user_id: int, action: str) -> UserEvent:
        return await self.create(user_id=user_id, action=action)
```

Добавь его в `app/repositories/__init__.py`. В `dependencies.py`:

```python
def get_user_event_repository(session: SessionDep) -> UserEventRepository:
    return UserEventRepository(session)


UserEventRepoDep = Annotated[UserEventRepository, Depends(get_user_event_repository)]
```

`delete_user`:

```python
@router.delete("/users/delete/{user_id}", response_model=UserRead)
async def delete_user(
    user: UserDep,
    users: UserRepoDep,
    events: UserEventRepoDep,
    session: SessionDep,
) -> User:
    await users.delete(user)
    await events.log(user_id=user.id, action="deleted")
    await session.commit()
    return user
```

В `create_user` после `users.create(...)` — `await events.log(user_id=user.id, action="created")`. `user.id` уже есть: его получил `flush` внутри `create`.

Атомарность: с `raise RuntimeError("boom")` ответ 500, **пользователь на месте, события `deleted` нет**. `DELETE` и `INSERT` ушли в базу (`flush`), но `commit` не случился, и при закрытии сессии транзакция откатилась целиком. Это работает потому, что оба репозитория получили **одну и ту же** сессию (раздел 7, шаг 7), и ни один из них не делает `commit` сам. Если бы `UserRepository.delete` делал `commit`, пользователь удалился бы, а событие — нет.

Проверь: `docker compose exec pg_database psql -U user -d pg_test_db -c "SELECT * FROM logs.user_events"`. Не забудь убрать `raise`.

</details>

### Уровень 6. Тело запроса вместо query string

Сделай так, чтобы `POST /create_user` принимал данные **JSON-телом**: `{"name": "Anna", "age": 30}`. Какая одна строка меняется? Что поменяется в Swagger? Что сломается во фронтенде из урока по Nuxt и как это исправить?

<details><summary>Ответ</summary>

`data: Annotated[UserCreate, Query()]` → `data: UserCreate`. Схема без `Query()` — значит, тело запроса. В Swagger вместо трёх полей параметров появится блок **Request body** с примером JSON (его FastAPI собрал из `examples` в схеме).

Фронтенд отправляет параметры через `query: {...}`, теперь получит 422 `Field required`, `"loc": ["body"]`. Исправление во фронтенде — `$fetch('/create_user', { method: 'POST', body: {...} })`. Для учёбы сделай это в отдельной ветке: в основной адреса и параметры остаются прежними.

</details>

### Уровень 7. Data Mapper в чистом виде

Перепиши `app/models/` на **императивный** стиль из раздела 2: `User` — обычный `@dataclass`, таблица — `Table(...)`, связь — `registry().map_imperatively(User, users_table)`. Репозитории, зависимости и эндпоинты **менять нельзя** (кроме одной строки — найди её сам).

<details><summary>Ответ</summary>

`app/models/base.py`:

```python
from sqlalchemy import MetaData
from sqlalchemy.orm import registry

metadata = MetaData()
mapper_registry = registry(metadata=metadata)
```

`app/models/user.py`:

```python
from dataclasses import dataclass

from sqlalchemy import CheckConstraint, Column, Integer, Table, Text

from app.models.base import mapper_registry, metadata


@dataclass
class User:
    name: str
    age: int
    description: str | None = None
    id: int | None = None


users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("age", Integer, CheckConstraint("age >= 0"), nullable=False),
    Column("description", Text),
    schema="payment_statistic",
)

mapper_registry.map_imperatively(User, users_table)
```

В `app/models/__init__.py` остаётся только `User`. Та самая строка — в `repositories/base.py`: `Base` больше нет, поэтому `ModelT = TypeVar("ModelT")` без `bound`, и импорт `Base` убрать.

Всё остальное работает без изменений. В этом и смысл слоёв: эндпоинты знают только про репозиторий, репозиторий — про сессию и модель, а **как** модель связана с таблицей, знает только `models/`. Верни декларативный вариант — он короче.

</details>

---

## 12. Закрепление по памяти

Навык «написать с нуля» появляется не от прочтения, а от повторного вспоминания. Повтори Уровень 1 (пустая папка, без урока, с таймером):

| Когда | Что делать |
|---|---|
| Сегодня | Раздел 5 целиком, уровни 1–4 |
| Через 1 день | Уровень 1 + Уровень 5 |
| Через 3 дня | Уровень 1 + Уровень 6 + Уровень 7 |
| Через 7 дней | Уровень 1 + новая таблица с репозиторием и эндпоинтами по своей идее |

После каждой попытки сравни с разделом 7 и запиши, **в чём ошибся** — это твой личный список ловушек. Документацию в процессе открывать можно, но только чтобы уточнить синтаксис, а не за готовым решением.

### Самопроверка

- [ ] Объясняю разницу Active Record и Data Mapper и почему у нас Data Mapper.
- [ ] Могу назвать семь вопросов и в каком файле ответ на каждый.
- [ ] Отличаю engine, подключение, сессию и транзакцию.
- [ ] Знаю, когда уходит `INSERT`: на `add`, `flush` или `commit`.
- [ ] Объясняю карту объектов (identity map): почему два `get` дают один объект и один `SELECT`.
- [ ] Знаю, что значит `MissingGreenlet`, и зачем `expire_on_commit=False`.
- [ ] Знаю, что с `await`, а что без.
- [ ] Пишу модель по существующей таблице, включая схему PostgreSQL и `NULL` / `NOT NULL`.
- [ ] Пишу `BaseRepository` с `Generic` и наследника с одной строкой `model = ...`.
- [ ] Объясняю, почему репозиторий делает `flush`, а не `commit`, и почему в нём нет `HTTPException`.
- [ ] Пишу схемы с `Annotated` и `Field`, отличаю схему на вход от схемы на выход.
- [ ] Пишу зависимости `SessionDep`, `UserRepoDep`, `UserDep` и объясняю, почему сессия в запросе одна.
- [ ] Объясняю, почему `commit` — в обработчике, а не после `yield` в `get_session`.
- [ ] Написал `app/` с нуля за 30 минут.

Когда сделаешь задания, сохрани решения отдельным коммитом. Проверь в `git status`, что `sandbox/` и `.env` в коммит **не** попали.

### Что дальше

- **Миграции (Alembic).** Сейчас таблицы создают SQL-скрипты, которые работают только на пустой базе, а новые таблицы ты добавляешь руками через `psql`. Alembic сравнивает модели с базой и сам пишет скрипты изменений, которые применяются по порядку и к пустой базе, и к базе с данными.
- **Связи между таблицами.** `relationship()`, внешние ключи, загрузка связанных объектов через `selectinload` — и третья причина `MissingGreenlet` из раздела 9.
- **Тесты.** Отдельная тестовая база, сессия, которая откатывается после каждого теста, и подмена зависимостей через `app.dependency_overrides`.
- **Слой сервисов.** Когда в обработчике станет много логики (проверить, записать в два места, отправить уведомление), её выносят в отдельный класс-сервис, а обработчик только принимает запрос и отдаёт ответ.

Добавляй каждое, только поняв, какую проблему оно решает.

---

## 13. Шпаргалка — открывать только после попыток

<details><summary>Engine, сессия, зависимость</summary>

```python
engine = create_async_engine("postgresql+asyncpg://<польз>:<пароль>@<хост>:5432/<база>", echo=<bool>)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

</details>

<details><summary>Модель</summary>

```python
class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)


class <Модель>(Base):
    __tablename__ = "<таблица>"
    __table_args__ = {"schema": "<схема>"}

    <поле>: Mapped[str] = mapped_column(Text)               # NOT NULL
    <поле>: Mapped[int]                                     # NOT NULL, тип из аннотации
    <поле>: Mapped[str | None] = mapped_column(Text)        # можно NULL
    <поле>: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

</details>

<details><summary>Схемы</summary>

```python
<Тип> = Annotated[<тип>, Field(<правила>, examples=[...])]


class <Модель>Base(BaseModel):
    <поле>: <Тип>


class <Модель>Create(<Модель>Base): ...


class <Модель>Read(<Модель>Base):
    model_config = ConfigDict(from_attributes=True)
    id: int
```

</details>

<details><summary>Репозиторий и зависимость</summary>

```python
class <Модель>Repository(BaseRepository[<Модель>]):
    model = <Модель>

    async def <метод_по_смыслу>(self, <значение>) -> Sequence[<Модель>]:
        stmt = select(<Модель>).where(<Модель>.<поле> == <значение>)
        return (await self.session.scalars(stmt)).all()


def get_<модель>_repository(session: SessionDep) -> <Модель>Repository:
    return <Модель>Repository(session)


<Модель>RepoDep = Annotated[<Модель>Repository, Depends(get_<модель>_repository)]
```

</details>

<details><summary>Эндпоинт, который меняет данные</summary>

```python
@router.post("/<путь>", response_model=<Модель>Read, status_code=201)
async def create_<модель>(
    data: <Модель>Create,                  # тело; Annotated[<Модель>Create, Query()] — query string
    repo: <Модель>RepoDep,
    session: SessionDep,
) -> <Модель>:
    obj = await repo.create(**data.model_dump())
    await session.commit()
    return obj
```

</details>

<details><summary>Запросы SQLAlchemy</summary>

| Хочу | Код |
|---|---|
| По первичному ключу | `await session.get(User, 1)` |
| Все | `(await session.scalars(select(User))).all()` |
| Первый или `None` | `(await session.scalars(stmt)).first()` |
| Условие | `select(User).where(User.age >= 18)` |
| Несколько условий («и») | `.where(User.age >= 18, User.name == "Anna")` |
| «Или» | `.where(or_(User.age < 18, User.age > 60))` |
| Подстрока без учёта регистра | `.where(User.name.ilike("%an%"))` |
| Сортировка | `.order_by(User.age.desc())` |
| Страница | `.limit(10).offset(20)` |
| Количество | `await session.scalar(select(func.count()).select_from(User))` |
| Одна колонка | `(await session.scalars(select(User.name))).all()` |

</details>

<details><summary>Методы сессии</summary>

| Метод | Что делает |
|---|---|
| `session.add(obj)` | Положить новый объект в сессию (без `await`) |
| `await session.flush()` | Отправить изменения в базу, не фиксируя |
| `await session.commit()` | Зафиксировать транзакцию |
| `await session.rollback()` | Отменить транзакцию; объекты устаревают |
| `await session.refresh(obj)` | Перечитать объект из базы |
| `await session.delete(obj)` | Пометить объект на удаление |
| `session.dirty`, `session.new`, `session.deleted` | Изменённые, новые и удаляемые объекты |
| `async with session.begin():` | Блок транзакции: `commit` в конце, `rollback` при ошибке |

</details>

### Где искать синтаксис

| Хочу | Что искать |
|---|---|
| Как описать модель и колонки | SQLAlchemy ORM Quick Start; Declarative Mapping |
| Как писать `select`, `where`, `order_by` | SQLAlchemy Unified Tutorial → Working with Data |
| Как работает сессия | SQLAlchemy → Session Basics; State Management |
| Асинхронный режим и `MissingGreenlet` | SQLAlchemy → Asynchronous I/O (asyncio) |
| Правила полей схемы | Pydantic → Fields |
| Зависимости и `Annotated` | FastAPI → Dependencies |
| Схема в query string | FastAPI → Query Parameter Models |
| `response_model` | FastAPI → Response Model |

Официальные материалы:

- [SQLAlchemy Unified Tutorial](https://docs.sqlalchemy.org/en/21/tutorial/index.html) — основы с нуля: engine, сессия, `select`.
- [SQLAlchemy: ORM Quick Start](https://docs.sqlalchemy.org/en/21/orm/quickstart.html) — модели в стиле `Mapped` / `mapped_column`.
- [SQLAlchemy: Session Basics](https://docs.sqlalchemy.org/en/21/orm/session_basics.html) — `flush`, `commit`, состояния объектов.
- [SQLAlchemy: Asynchronous I/O](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html) — `AsyncSession`, `expire_on_commit`, `MissingGreenlet`.
- [SQLAlchemy: Imperative Mapping](https://docs.sqlalchemy.org/en/21/orm/mapping_styles.html#imperative-mapping) — Data Mapper в чистом виде.
- [Pydantic: Fields](https://docs.pydantic.dev/latest/concepts/fields/) — `Field`, ограничения, `Annotated`.
- [FastAPI: Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) — `Depends`, цепочки зависимостей, `yield`.
- [FastAPI: Query Parameter Models](https://fastapi.tiangolo.com/tutorial/query-param-models/) — схема в query string.
- [FastAPI: Response Model](https://fastapi.tiangolo.com/tutorial/response-model/) — `response_model`.
- [Martin Fowler: Data Mapper](https://martinfowler.com/eaaCatalog/dataMapper.html) и [Active Record](https://martinfowler.com/eaaCatalog/activeRecord.html) — первоисточник обоих паттернов.
