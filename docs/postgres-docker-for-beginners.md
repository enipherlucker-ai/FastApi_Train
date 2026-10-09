# Свой сервер PostgreSQL в Docker для чайников 😄

**Цель урока:** после него ты пишешь сервис PostgreSQL в `compose.yaml` **с пустого файла**, без копирования шаблона, подключаешься к базе из терминала, из Python и из соседнего контейнера и можешь объяснить каждую строку.

Урок построен на этом репозитории. Итоговый `compose.yaml` будет запускать четыре сервиса: бэкенд (`api`, FastAPI), фронтенд (`web`, Nuxt), базу данных (`db`, PostgreSQL) и Telegram-бота (`bot`). **В этом уроке мы делаем только `db`**, но пишем его так, чтобы остальные три сервиса потом встали рядом без переделок. Команды выполняются **из корня репозитория** (там, где лежит `compose.yaml`) и одинаково работают в PowerShell и в Linux shell. Всё проверено на PostgreSQL 18.6 (образ `postgres:18`), Docker 29, Docker Compose v2 и psycopg 3.3.

## 0. Как проходить урок

Правила те же, что в [уроке по Docker](docker-for-beginners.md):

1. **Печатай руками.** Не копируй блоки кода из урока в файлы. Опечатки и ошибки — часть обучения.
2. **Одна настройка — одна проверка.** Сервис базы собирается по шагам; после каждого шага ты запускаешь его и проверяешь, что изменилось именно то, что ожидал.
3. **Сначала предскажи — потом запусти.** Перед каждой командой скажи себе, что должно произойти. Расхождение с реальностью — самое ценное место урока.
4. **Ответы — в свёрнутых блоках.** Открывай их только после своей попытки.

И одно новое правило:

5. **Держи открытыми два терминала.** В первом всё время идут логи базы (`docker compose logs -f db`), во втором ты выполняешь команды. Любой вопрос «почему не работает» начинается с того, что ты смотришь в логи.

План: понять модель (разделы 1–2) → запустить базу руками через `docker run` и увидеть, где теряются данные (3–4) → превратить это в сервис Compose по шагам (5) → подключиться тремя способами (6) → выучить правила, на которых все ошибаются (7) → бэкап (8) → диагностика (9) → тренировка с нарастающей сложностью (10) → повторение по памяти (11).

---

## 1. Что именно мы создаём

| Объект | Что это | Аналогия |
|---|---|---|
| Сервер PostgreSQL | Программа (процесс `postgres`), которая хранит данные и отвечает на SQL-запросы по сети, порт 5432 | Библиотека |
| База данных (database) | Отдельный набор таблиц внутри сервера. На одном сервере может быть много баз | Отдельный зал библиотеки |
| Пользователь (роль) | Имя и пароль, с которыми подключаются к серверу | Читательский билет |
| Таблица | Строки одного вида: `users`, `orders` | Каталожный ящик |
| Папка данных | Файлы на диске, где сервер хранит все базы | Здание со всеми книгами |
| Клиент | Тот, кто подключается: `psql`, Python-код, PyCharm, другой контейнер | Читатель |
| Образ `postgres:18` | Готовая программа PostgreSQL 18 для Docker. Свой Dockerfile не нужен | Типовой проект здания |
| Volume | Хранилище Docker для папки данных; живёт отдельно от контейнера | Фундамент, который остаётся, когда сносят дом |

**Образ отвечает на вопрос «какая программа?». Volume отвечает на вопрос «где лежат данные?». Переменные окружения отвечают на вопрос «с каким пользователем, паролем и базой сервер создаётся в первый раз?».**

Ещё три факта, которые понадобятся дальше:

- **Контейнер и данные — разные вещи.** Контейнер можно удалить и создать заново за секунду. Данные при этом должны остаться, поэтому они лежат не в контейнере, а в volume.
- **Первый запуск особенный.** Если папка данных пустая, образ сначала создаёт сервер: пользователя, пароль, базу, выполняет твои стартовые скрипты. При всех следующих запусках он видит, что данные уже есть, и **ничего из этого не повторяет**. На этом ломается половина новичков (раздел 7).
- **К базе подключаются по адресу `хост:порт` + имя пользователя + пароль + имя базы.** Какой хост писать — зависит от того, **откуда** подключаешься: с твоего компьютера или из соседнего контейнера. Это главная мысль урока.

### Как это выглядит в реальной работе

Один `compose.yaml` поднимает всё приложение одной командой. Вот куда мы идём:

```text
Твой компьютер: браузер, PyCharm, psql, check_db.py
   │ 127.0.0.1:3000      │ 127.0.0.1:8000      │ 127.0.0.1:5432
┌──┼─────────────────────┼─────────────────────┼──── сеть Compose ───┐
│  ▼                     ▼                     ▼                     │
│ web (Nuxt) ──HTTP──> api (FastAPI) ──db:5432──> db (PostgreSQL) ──> volume pg_data
│                                                 ▲                  │
│                        bot (Telegram) ──db:5432─┘                  │
└────────────────────────────────────────────────────────────────────┘
```

- `api` и `bot` ходят в базу **по имени сервиса** `db` внутри сети Compose.
- `web` в базу **не ходит никогда**: фронтенд работает в браузере пользователя, и пароль от базы туда попасть не должен. Фронтенд просит данные у `api`.
- Порт `127.0.0.1:5432` на компьютере нужен **только тебе** — чтобы смотреть в базу из PyCharm или скриптом во время разработки.

---

## 2. Алгоритм: семь вопросов перед любым сервисом базы данных

Сервис базы не пишут «сверху вниз по памяти». Его пишут, **ответив на вопросы**. Запомни эти семь вопросов — это и есть навык:

1. Какой сервер и какая версия? → `image`
2. С каким пользователем, паролем и базой сервер создаётся? → `environment`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
3. Где хранить пароль, чтобы он не попал в git? → файл `.env` и `${...}` в `compose.yaml`
4. Где лежат данные и должны ли они пережить удаление контейнера? → `volumes` (named volume)
5. Кто подключается и откуда? → `ports` (с компьютера) и имя сервиса (из других контейнеров)
6. Как понять, что база готова принимать подключения? → `healthcheck` + `depends_on` у тех, кто подключается
7. Что должно быть в базе с самого первого запуска? → стартовые скрипты в `/docker-entrypoint-initdb.d`

Ответы для нашего проекта:

| Вопрос | Ответ |
|---|---|
| Сервер и версия | PostgreSQL 18 → `postgres:18` |
| Пользователь, пароль, база | `app` / свой пароль / `fastapi_train` |
| Где пароль | `.env` в корне, файл в `.gitignore` |
| Данные | Named volume `pg_data` → папка `/var/lib/postgresql` в контейнере |
| Кто подключается | Ты с компьютера (`127.0.0.1:5432`); позже `api` и `bot` (`db:5432`) |
| Готовность | `pg_isready` в `healthcheck` |
| Стартовые данные | Таблица `users` из `db/init/01_schema.sql` |

> **Проверь себя.** В [уроке по Docker](docker-for-beginners.md) для `api` мы писали Dockerfile. Почему для `db` его не нужно?
>
> <details><summary>Ответ</summary>Dockerfile нужен, чтобы положить в образ **свой** код или поставить в него программы. В `db` мы ничего своего не добавляем: программа PostgreSQL уже есть в готовом образе `postgres:18`, настройки передаются переменными окружения, данные лежат в volume, стартовые скрипты подключаются как папка. Поэтому в Compose вместо `build` пишем `image`.</details>

---

## 3. Подготовь инструменты

Нужны Docker Desktop (на Windows — с Linux-контейнерами) и Docker Compose. Если ты прошёл [урок по Docker](docker-for-beginners.md), всё уже есть. Проверь:

```sh
docker version
docker compose version
```

**Ожидаемо:** в выводе `docker version` есть оба блока — `Client` и `Server`. Если `Server` нет, вернись в раздел 3 урока по Docker.

**Свободен ли порт 5432.** На Windows часто уже стоит «настоящий» PostgreSQL, установленный когда-то инсталлятором, — он занимает тот же порт. Проверь в PowerShell:

```powershell
netstat -ano | findstr :5432
```

**Ожидаемо:** пустой вывод — порт свободен. Если есть строка с `LISTENING`, порт занят. Тогда во всех командах урока, где порт стоит **слева** (`127.0.0.1:5432:5432`), пиши `5433` вместо левого `5432`: `127.0.0.1:5433:5432` — и подключайся с компьютера к `5433`. Почему меняется только левое число — разберём в уровне 2 тренировки.

**Скачай образ заранее** (около 150 МБ):

```sh
docker pull postgres:18
```

> Почему `18`, а не `latest`? `latest` — это «самая новая версия на момент скачивания». Осенью 2026 года выйдет PostgreSQL 19, и `latest` молча начнёт означать 19. А PostgreSQL 19 не умеет запускаться на папке данных от PostgreSQL 18 без переноса данных. Для базы данных **всегда фиксируй мажорную версию** в теге.

---

## 4. Шаг ноль: запусти базу руками через `docker run`

Это главный приём, как и в уроке по Docker: **сначала делаешь руками, потом записываешь в файл.** Заодно своими глазами увидишь, где теряются данные.

### 4.1. Запуск без пароля

```sh
docker run --rm postgres:18
```

> **Предскажи до запуска:** что произойдёт?
>
> <details><summary>Ответ</summary>
>
> Контейнер сразу завершится с ошибкой:
>
> ```text
> Error: Database is uninitialized and superuser password is not specified.
>        You must specify POSTGRES_PASSWORD to a non-empty value for the
>        superuser. For example, "-e POSTGRES_PASSWORD=password" on "docker run".
> ```
>
> Образ отказывается создавать сервер без пароля. Ошибку стоит прочитать до конца: Docker-образы обычно прямо пишут, чего им не хватает.
>
> </details>

### 4.2. Запуск с паролем

```sh
docker run -d --name pg-hand -e POSTGRES_PASSWORD=secret -p 127.0.0.1:5432:5432 postgres:18
docker logs -f pg-hand
```

| Часть | Смысл |
|---|---|
| `-d` | В фоне: терминал сразу освобождается |
| `--name pg-hand` | Имя контейнера для `docker logs`, `docker exec`, `docker rm` |
| `-e POSTGRES_PASSWORD=secret` | Переменная окружения: пароль суперпользователя `postgres` |
| `-p 127.0.0.1:5432:5432` | Порт 5432 компьютера (только для тебя, не для всей сети) → порт 5432 контейнера |
| `postgres:18` | Образ |

**Ожидаемо:** в конце логов — `database system is ready to accept connections`. Выход из логов: Ctrl+C (контейнер продолжит работать).

> Найди в логах строку `ready to accept connections`. Сколько раз она встречается и почему?
>
> <details><summary>Ответ</summary>Два раза. Первый раз сервер запускается **временно**, только для настройки: создаёт базу, выполняет стартовые скрипты (`PostgreSQL init process complete; ready for start up.`). Потом он останавливается и запускается уже **по-настоящему**. Ориентируйся на последнюю строку. При втором и следующих запусках настройки нет, и строка будет одна.</details>

### 4.3. Зайди в базу и создай таблицу

```sh
docker exec -it pg-hand psql -U postgres
```

`docker exec` выполняет команду в **работающем** контейнере. `psql` — консольный клиент PostgreSQL, он уже есть в образе. `-U postgres` — под каким пользователем подключиться.

Приглашение сменится на `postgres=#`. Ты внутри базы. Выполни по одной команде и смотри на результат (SQL-команды заканчиваются точкой с запятой; команды с `\` — это команды самого `psql`, без точки с запятой):

```sql
\l
CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL);
INSERT INTO users (name, age) VALUES ('Anna', 30);
SELECT * FROM users;
\dt
\d users
\q
```

| Команда | Что делает |
|---|---|
| `\l` | Список баз на сервере. Пока там только служебные: `postgres`, `template0`, `template1` |
| `\dt` | Список таблиц в текущей базе |
| `\d users` | Колонки таблицы `users` |
| `\q` | Выйти из `psql` |

> Почему `psql` не спросил пароль?
>
> <details><summary>Ответ</summary>Подключения **изнутри контейнера** через локальный сокет образ разрешает без пароля (в логах при первом запуске было `initdb: warning: enabling "trust" authentication for local connections`). Подключения **по сети** — с твоего компьютера или из другого контейнера — требуют пароль. Проверишь это в разделе 6.</details>

### 4.4. Пересоздай контейнер

```sh
docker rm -f pg-hand
docker run -d --name pg-hand -e POSTGRES_PASSWORD=secret -p 127.0.0.1:5432:5432 postgres:18
docker exec -it pg-hand psql -U postgres -c "SELECT * FROM users;"
```

`-c "..."` — выполнить одну команду и выйти, без интерактивного режима. Если сразу после запуска пришла ошибка `the database system is starting up`, подожди пару секунд и повтори.

> **Предскажи до запуска:** что выведет последняя команда?
>
> <details><summary>Ответ</summary>
>
> ```text
> ERROR:  relation "users" does not exist
> ```
>
> Таблицы нет. Новый контейнер — новая пустая папка данных. Где же старые данные? Выполни `docker volume ls`: там лежат volumes с длинными именами из цифр и букв. Образ `postgres` сам объявляет папку данных volume'ом, и **каждый новый контейнер получает новый безымянный (anonymous) volume**. Старый остался на диске, но никто его больше не подключит — это мусор. Чтобы данные переживали пересоздание контейнера, volume нужно **назвать** и подключать его явно.
>
> </details>

Убери за собой — `-v` удаляет вместе с контейнером его безымянный volume:

```sh
docker rm -f -v pg-hand
docker volume prune
```

`docker volume prune` спросит подтверждение и удалит безымянные volumes, которые не подключены ни к одному контейнеру. Названные volumes он не трогает.

Запиши свои ручные действия — **следующий раздел превращает каждое из них в строку `compose.yaml`**:

| Ручное действие | В `compose.yaml` |
|---|---|
| `postgres:18` | `image: postgres:18` |
| `-e POSTGRES_PASSWORD=secret` | `environment:` |
| `-p 127.0.0.1:5432:5432` | `ports:` |
| Данные терялись при пересоздании | `volumes:` с **именованным** volume |
| Ждал строку `ready to accept connections` | `healthcheck:` |
| Создавал таблицу руками в `psql` | Стартовый скрипт в `db/init/` |
| `--name`, `--rm`, `-d` | Не нужны: Compose сам именует контейнеры, а `-d` пишется в `docker compose up -d` |

---

## 5. Собираем сервис `db` по одной настройке

Открой `compose.yaml` в корне. В нём уже есть сервис `api` из урока по Docker. Новый сервис `db` пишется **рядом с ним**, на том же уровне отступа, внутри `services:`. Если файла нет — создай его с первой строкой `services:`.

На каждом шаге цикл одинаковый: **дописал → `docker compose up -d db` → проверил**. Имя `db` в конце команды значит «запусти только этот сервис»: `api` нам сейчас не нужен.

### Шаг 1. Сервер — `image`, `environment`, `ports`

```yaml
services:
  # api: ... — сервис из урока по Docker, не трогай его

  db:
    image: postgres:18
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: change_me
      POSTGRES_DB: fastapi_train
    ports:
      - "127.0.0.1:5432:5432"
```

- `image` вместо `build`: образ готовый, собирать нечего.
- `POSTGRES_USER` — имя суперпользователя. Если не задать, будет `postgres`.
- `POSTGRES_PASSWORD` — его пароль. Единственная обязательная переменная.
- `POSTGRES_DB` — какую базу создать при первом запуске. Если не задать, она будет называться так же, как пользователь.
- Пароль прямо в файле — **временно**, на шаге 3 мы его оттуда уберём.

Запусти и проверь:

```sh
docker compose config
docker compose up -d db
docker compose ps
docker compose exec db psql -U app -d fastapi_train -c "\conninfo"
```

**Ожидаемо:** `config` печатает конфигурацию без ошибок; `ps` показывает `db` со статусом `Up`; последняя команда печатает таблицу `Connection Information`, в которой `Database | fastapi_train` и `Client User | app`.

`docker compose exec db ...` — то же, что `docker exec`, только вместо имени контейнера пишется **имя сервиса**.

> Выполни `docker compose exec db psql -U app` без `-d fastapi_train`. Что получилось и почему?
>
> <details><summary>Ответ</summary>
>
> ```text
> FATAL:  database "app" does not exist
> ```
>
> Если базу не указать, `psql` подключается к базе с тем же именем, что и пользователь. Базы `app` нет — есть `fastapi_train`. Указывай базу явно.
>
> </details>

### Шаг 2. Данные — именованный volume

Допиши в сервис `db` (отступ — четыре пробела, на уровне `ports`):

```yaml
    volumes:
      - pg_data:/var/lib/postgresql
```

И **в самый конец файла**, без отступа, на уровне `services:`:

```yaml
volumes:
  pg_data:
```

- `pg_data:/var/lib/postgresql` — слева **имя** volume, справа папка в контейнере. Если слева стоит имя, а не путь (`./...`), это named volume: Docker хранит его у себя и подключает к любому новому контейнеру сервиса.
- Блок `volumes:` в конце файла **объявляет** volume. Без него `docker compose config` выдаст ошибку, что volume `pg_data` не определён.
- Справа именно `/var/lib/postgresql`, без `/data` на конце. Начиная с PostgreSQL 18 образ хранит данные в подпапке `/var/lib/postgresql/18/docker`. Во всех старых статьях и ответах в интернете написано `/var/lib/postgresql/data` — для `postgres:18` это **ошибка**, сервер не запустится (уровень 4 тренировки).

Запусти, создай данные и **пересоздай** контейнер:

```sh
docker compose up -d db
docker compose exec db psql -U app -d fastapi_train -c "CREATE TABLE notes (id SERIAL PRIMARY KEY, text TEXT);"
docker compose exec db psql -U app -d fastapi_train -c "INSERT INTO notes (text) VALUES ('выжил');"
docker compose down
docker compose up -d db
docker compose exec db psql -U app -d fastapi_train -c "SELECT * FROM notes;"
```

> **Предскажи до запуска:** переживёт ли строка `выжил` команду `down`, которая **удаляет** контейнер?
>
> <details><summary>Ответ</summary>Да. `docker compose down` удаляет контейнеры и сеть, но **не** named volumes. Новый контейнер подключил тот же `pg_data` и увидел старые данные. Сравни с разделом 4.4: там каждый раз был новый безымянный volume.</details>

Посмотри, как Docker назвал volume:

```sh
docker volume ls
```

**Ожидаемо:** `fastapi_train_pg_data`. Compose добавляет в начало имя проекта — по умолчанию это имя папки в нижнем регистре. Так volumes разных проектов не путаются.

### Шаг 3. Пароль — в `.env`

Пароль в `compose.yaml` попадёт в git, а значит — ко всем, у кого есть доступ к репозиторию. Перенесём его в отдельный файл.

Создай в корне репозитория файл **`.env`** (именно так: точка в начале, без расширения). Создавай его **в PyCharm** (правый клик по корню проекта → New → File), а не командой `echo ... > .env` в PowerShell: Windows PowerShell 5.1 пишет такие файлы в кодировке UTF-16, и Compose их не прочитает.

```text
POSTGRES_USER=app
POSTGRES_PASSWORD=change_me
POSTGRES_DB=fastapi_train
```

В `.env` нет кавычек и пробелов вокруг `=`. В пароле используй только латинские буквы, цифры и `_`: символы `@ : / # ?` сломают адрес подключения в разделе 6.

Замени значения в `compose.yaml` на подстановки:

```yaml
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
```

`${ИМЯ}` — подстановка: Compose ищет переменную `ИМЯ` в окружении терминала и в файле `.env` рядом с `compose.yaml` и вставляет её значение **до** запуска. Сам файл `.env` в контейнер не попадает — туда попадают только переменные из `environment`.

Добавь `.env` в `.gitignore` (новой строкой):

```text
.env
```

И создай **`.env.example`** — его коммитят, чтобы другой человек (или ты на другом компьютере) знал, какие переменные нужны:

```text
POSTGRES_USER=app
POSTGRES_PASSWORD=
POSTGRES_DB=fastapi_train
```

Проверь:

```sh
docker compose config
git status
```

**Ожидаемо:** в выводе `config` вместо `${POSTGRES_PASSWORD}` стоит `change_me` — подстановка сработала. В `git status` есть `.env.example`, но **нет** `.env`.

> Переименуй `.env` в `env.txt` и снова выполни `docker compose config`. Что изменилось? Верни имя обратно.
>
> <details><summary>Ответ</summary>Compose предупреждает: `The "POSTGRES_PASSWORD" variable is not set. Defaulting to a blank string.` — и подставляет пустые строки. Это **предупреждение, а не ошибка**: `up` всё равно попытается запуститься. Если хочешь, чтобы без пароля Compose отказывался работать, пиши `${POSTGRES_PASSWORD:?задай POSTGRES_PASSWORD в .env}` — тогда `config` и `up` остановятся с этим текстом.</details>

### Шаг 4. Готовность — `healthcheck`

Статус `Up` значит только «процесс запущен». Сервер базы после старта ещё несколько секунд не принимает подключения (а при первом запуске — дольше: идёт настройка). Сервисам `api` и `bot` нужно знать, когда база **готова**. Для этого в образе есть программа `pg_isready`.

Допиши в сервис `db`:

```yaml
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s
```

- `test` — команда проверки. Код выхода 0 — здоров, иначе — нет. `CMD-SHELL` — выполнить строку через shell внутри контейнера.
- `$$` — экранированный `$`. Одиночный `$` Compose подставил бы сам из `.env`; двойной он превращает в одиночный и оставляет shell'у **внутри контейнера**, где эти переменные тоже есть (мы передали их в `environment`).
- `interval` — как часто проверять; `timeout` — сколько ждать ответа; `retries` — сколько неудач подряд до статуса `unhealthy`; `start_period` — время на запуск, когда неудачи не считаются.

Проверь:

```sh
docker compose up -d db
docker compose ps
```

**Ожидаемо:** сначала `Up ... (health: starting)`, через несколько секунд — `Up ... (healthy)`.

Удобная команда: `docker compose up -d --wait db` — запустить и **дождаться** `healthy`, прежде чем вернуть терминал. Пригодится в скриптах.

Как этим воспользуются другие сервисы — в уровне 5 тренировки (`depends_on` с `condition: service_healthy`).

### Шаг 5. Стартовые данные — `/docker-entrypoint-initdb.d`

Таблицу `users` можно создать руками в `psql`, но тогда на новом компьютере её придётся создавать снова. Запишем её в файл. Образ `postgres` при **первом** запуске выполняет все файлы `*.sql` (и `*.sh`) из папки `/docker-entrypoint-initdb.d` — по алфавиту.

Создай папку `db/init/` и в ней файл **`01_schema.sql`**:

```sql
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    name        TEXT    NOT NULL,
    age         INTEGER NOT NULL CHECK (age >= 0),
    description TEXT
);

INSERT INTO users (name, age, description) VALUES ('Anna', 30, 'Первый пользователь');
```

Колонки повторяют модель `User` из `app/main.py`: `description` может быть пустым (`None` в Python → `NULL` в SQL), остальные — нет. `SERIAL` — число, которое база сама увеличивает при каждой вставке: замена `global_id` из `main.py`.

Подключи папку в сервис `db` — второй строкой в `volumes`:

```yaml
    volumes:
      - pg_data:/var/lib/postgresql
      - ./db/init:/docker-entrypoint-initdb.d:ro
```

`./db/init` начинается с `./` — это bind mount, папка с твоего компьютера. `:ro` — только для чтения: контейнер не сможет менять твои скрипты.

```sh
docker compose up -d db
docker compose exec db psql -U app -d fastapi_train -c "SELECT * FROM users;"
```

> **Предскажи до запуска:** появится ли таблица `users`?
>
> <details><summary>Ответ</summary>
>
> Нет: `relation "users" does not exist`. Volume `pg_data` уже содержит данные с шага 2, поэтому образ считает, что сервер давно настроен, и папку `/docker-entrypoint-initdb.d` **не смотрит**. Стартовые скрипты выполняются **только на пустой папке данных**.
>
> Чтобы их выполнить, нужно удалить данные. Команда ниже **безвозвратно** удаляет volume `pg_data` — сейчас там только учебная таблица `notes`, её не жалко:
>
> ```sh
> docker compose down -v
> docker compose up -d --wait db
> docker compose logs db
> docker compose exec db psql -U app -d fastapi_train -c "SELECT * FROM users;"
> ```
>
> В логах появится `running /docker-entrypoint-initdb.d/01_schema.sql`, `CREATE TABLE`, `INSERT 0 1`, а `SELECT` вернёт Anna.
>
> </details>

### Шаг 6. Автозапуск — `restart`

```yaml
    restart: unless-stopped
```

Если процесс базы упал, Docker поднимет его снова. И когда Docker Desktop запускается вместе с Windows, база тоже поднимется сама — если ты не остановил её руками (`docker compose stop db`). Для базы, которой пользуются другие сервисы, это удобно.

### Итоговый сервис `db`

Сверь со своим. Комментарии — это то, что ты должен уметь сказать про каждую строку (цифры — номера вопросов из раздела 2):

```yaml
services:
  # api, web, bot — появятся здесь же, рядом с db

  db:
    # 1. Готовый сервер PostgreSQL 18; мажорная версия зафиксирована
    image: postgres:18
    # 2–3. Пользователь, пароль и база при ПЕРВОМ запуске; значения — из .env
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    # 5. Подключение с компьютера, только с него самого
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      # 4. Данные переживают удаление контейнера (для 18+ — без /data)
      - pg_data:/var/lib/postgresql
      # 7. Скрипты, которые выполнятся на пустой папке данных
      - ./db/init:/docker-entrypoint-initdb.d:ro
    # 6. «Готов принимать подключения», а не просто «процесс запущен»
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s
    restart: unless-stopped

volumes:
  pg_data:
```

Плюс файлы рядом: `.env` (не в git), `.env.example` (в git), `db/init/01_schema.sql` (в git), строка `.env` в `.gitignore`.

---

## 6. Подключаемся к базе тремя способами

Любое подключение описывается **одной строкой** — адресом базы (connection string). Его понимают Python, SQLAlchemy, большинство библиотек и программ:

```text
postgresql://app:change_me@127.0.0.1:5432/fastapi_train
           │   │         │         │    │
           │   │         │         │    └ имя базы
           │   │         │         └ порт
           │   │         └ хост: КУДА подключаться (зависит от того, ОТКУДА)
           │   └ пароль
           └ пользователь
```

### Способ 1. `psql` внутри контейнера

Уже знаком по разделу 5:

```sh
docker compose exec db psql -U app -d fastapi_train
```

Ничего ставить не нужно, пароль не спрашивают. Это главный инструмент «посмотреть, что в базе».

### Способ 2. Python на твоём компьютере

Это то, как будет подключаться бэкенд, пока ты запускаешь его без Docker. Активируй `.venv` проекта и установи драйвер PostgreSQL для Python:

```sh
python -m pip install "psycopg[binary]"
```

`psycopg` — драйвер, который умеет говорить с PostgreSQL. `[binary]` — вариант с уже собранной библиотекой внутри: на Windows не нужно ничего компилировать.

Создай в корне файл **`check_db.py`**:

```python
import os

import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://app:change_me@127.0.0.1:5432/fastapi_train",
)

with psycopg.connect(DATABASE_URL) as conn:
    print(conn.execute("SELECT version()").fetchone()[0])
    for row in conn.execute("SELECT id, name, age FROM users ORDER BY id"):
        print(row)
```

- Адрес берётся из переменной окружения `DATABASE_URL`, а если её нет — используется значение по умолчанию для твоего компьютера. Так один и тот же код работает и на компьютере, и в контейнере: меняется только переменная.
- `with psycopg.connect(...) as conn` — открыть подключение и **закрыть** его в конце блока.
- `conn.execute(...)` возвращает курсор; `fetchone()` — одна строка результата; по курсору можно пройти циклом `for`.

```sh
python check_db.py
```

**Ожидаемо:** строка `PostgreSQL 18.6 ...` и `(1, 'Anna', 30)`.

> Подставь в адрес хост `db` вместо `127.0.0.1` и запусти снова. Что произошло и почему?
>
> <details><summary>Ответ</summary>
>
> ```text
> psycopg.OperationalError: failed to resolve host 'db': ...
> ```
>
> Имя `db` существует **только внутри сети Compose**. Твой компьютер о нём ничего не знает: для него база доступна через опубликованный порт `127.0.0.1:5432` (строка `ports`).
>
> </details>

**PyCharm.** Если в твоём PyCharm есть окно **Database** (оно есть в платной версии), подключись и там: `+` → Data Source → PostgreSQL; Host `127.0.0.1`, Port `5432`, User `app`, Password — из `.env`, Database `fastapi_train`. При первом подключении PyCharm предложит скачать драйвер — соглашайся. Это те же пять частей адреса, только в отдельных полях.

### Способ 3. Из другого контейнера в сети Compose

Так будут подключаться `api` и `bot`. Запусти **временный** контейнер с `psql` в той же сети, что и `db`:

```sh
docker network ls
docker run --rm -it --network fastapi_train_default postgres:18 psql -h db -U app -d fastapi_train
```

- `docker network ls` покажет сеть, которую Compose создал для проекта: `<имя проекта>_default`. Если имя другое — подставь своё.
- `--network fastapi_train_default` — подключить временный контейнер к этой сети.
- `postgres:18 psql ...` — образ берём только ради программы `psql`, сервер в этом контейнере не запускается: команда после имени образа заменяет стандартную.
- `-h db` — хост: имя сервиса.

**Ожидаемо:** `psql` **спросит пароль** (это подключение по сети, а не через локальный сокет), после ввода — приглашение `fastapi_train=>`. Выйти: `\q`.

> Повтори команду с `-h localhost`. Предскажи результат.
>
> <details><summary>Ответ</summary>
>
> ```text
> connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused
> ```
>
> `localhost` внутри контейнера — это **сам этот контейнер**, а в нём сервер не запущен. Ни базы, ни твоего компьютера по этому адресу нет. Ровно та же ошибка будет у `api` или `bot`, если оставить в их `DATABASE_URL` хост `127.0.0.1`.
>
> </details>

### Итог: какой хост писать

| Кто подключается | Где работает | Адрес |
|---|---|---|
| Ты: `psql` в контейнере базы | Внутри `db` | Без хоста (локальный сокет), без пароля |
| `check_db.py`, бэкенд без Docker, PyCharm | Твой компьютер | `127.0.0.1:5432` — опубликованный порт |
| `api` в Compose | Контейнер в сети Compose | `db:5432` — имя сервиса |
| `bot` в Compose | Контейнер в сети Compose | `db:5432` — имя сервиса |
| `web` (Nuxt) | Браузер и Nuxt-сервер | **Никак.** Только через API |

Внутри сети Compose порт всегда **порт контейнера** (5432), даже если на компьютер ты опубликовал его как 5433.

---

## 7. Правила, на которых ошибаются при написании с нуля

### `POSTGRES_*` работают только при первом запуске

`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` и скрипты из `/docker-entrypoint-initdb.d` применяются **только когда папка данных пустая**. Дальше пользователь и пароль хранятся **в самой базе**, в volume.

| Что сделал | Что будет |
|---|---|
| Поменял `POSTGRES_PASSWORD` в `.env`, `up -d` | В контейнере переменная новая, но в базе пароль старый. Подключение по сети с новым паролем: `password authentication failed` |
| Поменял `POSTGRES_USER` или `POSTGRES_DB` | Ничего не создастся: `role "..." does not exist` / `database "..." does not exist` |
| Добавил `02_*.sql` в `db/init` | Не выполнится, пока в volume есть данные |

Как менять, не теряя данные, — **SQL-командами** в `psql`:

```sql
ALTER USER app PASSWORD 'new_secret';
CREATE DATABASE other;
```

Как менять, теряя данные, — `docker compose down -v` и снова `up`. Это удобно, пока данные учебные, и катастрофа, когда они настоящие.

### Путь volume для PostgreSQL 18+

| Запись | Результат |
|---|---|
| `pg_data:/var/lib/postgresql` | Правильно для `postgres:18` и новее |
| `pg_data:/var/lib/postgresql/data` | Для 18+ контейнер завершается с ошибкой `in 18+, these Docker images are configured to store database data in a format which is compatible with "pg_ctlcluster"...` |
| Нет `volumes` вообще | Работает, но каждый новый контейнер — новая пустая база (раздел 4.4) |

### Версия образа — это формат данных

Папка данных PostgreSQL 18 не откроется сервером 17 или 19. Поэтому:

- В `image` пиши мажорную версию: `postgres:18`. Не `postgres` и не `postgres:latest`.
- Минорные обновления (18.6 → 18.7) безопасны: `docker compose pull db` и `docker compose up -d db`.
- Переход на новую мажорную версию — это **перенос данных** (раздел 8: дамп из старой, восстановление в новую), а не смена цифры в теге.

### `ports` — только для твоего компьютера

| Запись | Кто может подключиться |
|---|---|
| `"127.0.0.1:5432:5432"` | Только твой компьютер |
| `"5432:5432"` | **Любой** компьютер в твоей сети (Wi-Fi в кафе, офис). С паролем `change_me` — плохая идея |
| Нет `ports` | Только контейнеры в сети Compose |

Другим сервисам в Compose `ports` не нужны: они ходят напрямую по имени `db`. На сервере (production) у базы обычно `ports` нет вовсе.

### `depends_on` не ждёт готовности без `condition`

```yaml
    depends_on:
      - db                        # только порядок старта: «запусти db раньше»

    depends_on:
      db:
        condition: service_healthy  # «дождись, пока healthcheck db скажет healthy»
```

С первой записью бот или API запускаются, когда процесс базы стартовал, но ещё не принимает подключения, и падают с `Connection refused` (уровень 4 тренировки). Для сервисов, которые подключаются к базе при старте, пиши вторую.

### `down`, `down -v`, `stop`, `restart`

| Команда | Контейнер | Данные в `pg_data` |
|---|---|---|
| `docker compose stop db` | Остановлен, не удалён | Целы |
| `docker compose restart db` | Перезапущен; **изменения `compose.yaml` и `.env` не применяются** | Целы |
| `docker compose up -d db` | Пересоздаётся, если поменялись настройки | Целы |
| `docker compose down` | Удалён | Целы |
| `docker compose down -v` | Удалён | **Удалены безвозвратно** |

Не пиши `-v` по привычке. Перед `down -v` на настоящих данных — бэкап (раздел 8).

### Ошибка в стартовом скрипте не повторяется

Если `01_schema.sql` упал с ошибкой, контейнер завершается. Но папка данных к этому моменту **уже создана**. При следующем старте (вручную или из-за `restart: unless-stopped`) образ видит непустую папку, пропускает настройку — и база становится `healthy` **без твоих таблиц**. Ошибку видно только в логах первого запуска. Правило: после правки скриптов в `db/init` всегда `down -v` + `up` + чтение `docker compose logs db`.

### Как посмотреть, что получилось

| Хочу узнать | Команда |
|---|---|
| Статус и здоровье | `docker compose ps` |
| Логи базы | `docker compose logs -f db` |
| Что Compose подставил из `.env` | `docker compose config` |
| Какие переменные видит контейнер | `docker compose exec db env` |
| Какие базы есть | `docker compose exec db psql -U app -d fastapi_train -c "\l"` |
| Какие таблицы есть | `docker compose exec db psql -U app -d fastapi_train -c "\dt"` |
| Какие volumes есть | `docker volume ls` |
| Где образ хранит данные | `docker image inspect postgres:18 --format "{{json .Config.Env}}"` → `PGDATA=...` |
| Готов ли сервер | `docker compose exec db pg_isready -U app -d fastapi_train` |

---

## 8. Бэкап и восстановление

Бэкап базы — это SQL-файл, который заново создаёт все таблицы и данные. Делает его программа `pg_dump`, она тоже есть в образе.

**Сделать бэкап.** Пишем файл внутри контейнера, затем копируем его на компьютер:

```sh
docker compose exec db pg_dump -U app -d fastapi_train -f /tmp/backup.sql
docker compose cp db:/tmp/backup.sql ./backup.sql
```

Открой `backup.sql` в PyCharm: там `CREATE TABLE`, `COPY ... FROM stdin` с твоими строками и служебные команды.

Почему не одной командой `docker compose exec db pg_dump ... > backup.sql`? В Windows PowerShell 5.1 оператор `>` перекодирует вывод в UTF-16, и такой файл потом не восстановится. Копирование через `docker compose cp` переносит файл байт в байт в любом терминале.

**Восстановить** (например, в новую пустую базу после `down -v`):

```sh
docker compose cp ./backup.sql db:/tmp/backup.sql
docker compose exec db psql -U app -d fastapi_train -f /tmp/backup.sql
```

`backup.sql` содержит твои данные, ему не место в git. Добавь в `.gitignore` строку `/backup.sql` — косая черта в начале значит «только этот файл в корне». Не пиши `*.sql`: так git перестанет видеть и `db/init/01_schema.sql`.

---

## 9. Диагностика: сначала найди этап

Любую проблему сначала относи к этапу: **конфигурация → старт сервера → подключение → SQL**.

| Симптом | Этап | Что проверить |
|---|---|---|
| `The "POSTGRES_PASSWORD" variable is not set` | конфигурация | Есть ли `.env` рядом с `compose.yaml`, его имя и кодировка (UTF-8) |
| `volume "pg_data" ... undefined` | конфигурация | Блок `volumes:` в конце файла без отступа |
| `Database is uninitialized and superuser password is not specified` | старт | Дошёл ли `POSTGRES_PASSWORD` до контейнера: `docker compose config` |
| `in 18+, these Docker images are configured...` | старт | Путь volume: `/var/lib/postgresql`, без `/data` |
| `port is already allocated` / `bind: ... address already in use` | старт | Порт 5432 занят: локальный PostgreSQL или другой контейнер. Левый порт → 5433 |
| `db` в статусе `Restarting` или `Exited` | старт | `docker compose logs db` — причина в последних строках |
| Таблиц из `db/init` нет | старт | Скрипты выполняются только на пустом volume; ошибки — в логах первого запуска |
| `Connection refused` с компьютера | подключение | Запущен ли `db`; есть ли `ports`; тот ли порт в адресе |
| `Connection refused` из контейнера | подключение | Хост `db`, а не `localhost`; `depends_on` с `condition: service_healthy` |
| `failed to resolve host 'db'` | подключение | Ты подключаешься с компьютера: нужен `127.0.0.1` |
| `password authentication failed` | подключение | Пароль меняли после первого запуска? `ALTER USER` (раздел 7) |
| `database "..." does not exist` | подключение | Имя базы в адресе; без `-d` `psql` берёт имя пользователя |
| `relation "users" does not exist` | SQL | Та ли база (`\conninfo`); есть ли таблица (`\dt`) |
| `the database system is starting up` | подключение | Сервер ещё запускается — подожди `healthy` |

---

## 10. Тренировка: от простого к переносу навыка

### Уровень 1. С пустого листа

Удали (или переименуй) сервис `db` из `compose.yaml`, файлы `.env`, `.env.example` и папку `db/`. Не открывая урок, напиши их заново, опираясь только на семь вопросов из раздела 2. Затем `docker compose down -v`, `docker compose up -d --wait db`, `python check_db.py`. Засеки время.

**Критерий:** `check_db.py` печатает Anna, и ты вслух объясняешь каждую строку сервиса. Цель — уложиться в 10 минут.

### Уровень 2. Порт на компьютере

Сделай так, чтобы с компьютера база была доступна на порту `5433`. До запуска скажи: какое число меняется в `compose.yaml`? Что меняется в `check_db.py`? А что поменялось бы в `DATABASE_URL` у сервиса `api` внутри Compose?

<details><summary>Ответ</summary>

В `compose.yaml`: `"127.0.0.1:5433:5432"` — меняется **левое** число, порт компьютера. Сервер внутри контейнера по-прежнему слушает 5432.

В `check_db.py` (или в переменной `DATABASE_URL` на компьютере): `127.0.0.1:5433`.

У `api` — **ничего**: `db:5432`. Внутри сети Compose контейнеры ходят друг к другу напрямую, мимо опубликованных портов.

</details>

### Уровень 3. Смена пароля

Поменяй `POSTGRES_PASSWORD` в `.env` на `new_secret` и выполни `docker compose up -d db`. Предскажи, с каким паролем теперь подключится `check_db.py`. Проверь. Затем сделай так, чтобы работал новый пароль, **не потеряв** данные.

<details><summary>Ответ</summary>

Работает **старый** пароль, новый — `password authentication failed for user "app"`. Хотя `docker compose exec db env` показывает `POSTGRES_PASSWORD=new_secret`: переменная дошла до контейнера, но образ использует её только при первом запуске.

Исправление:

```sh
docker compose exec db psql -U app -d fastapi_train -c "ALTER USER app PASSWORD 'new_secret';"
```

`psql` внутри контейнера пароль не спрашивает — поэтому этим путём можно поменять пароль, даже если старый забыт.

</details>

### Уровень 4. Сломай специально

По очереди внеси одну поломку, **предскажи симптом**, проверь (`docker compose up -d db`, `docker compose ps -a`, `docker compose logs db`), верни рабочий вариант:

1. В `volumes` напиши `pg_data:/var/lib/postgresql/data`.
2. Убери строку `POSTGRES_PASSWORD` и выполни `docker compose down -v` перед `up`.
3. Убери `POSTGRES_PASSWORD`, но **без** `down -v`.
4. В `01_schema.sql` напиши `CREAT TABLE` вместо `CREATE TABLE`, затем `down -v` и `up`. Подожди 20 секунд и посмотри `docker compose ps`.
5. В `ports` напиши `"127.0.0.1:5432:5433"`.
6. В `check_db.py` замени `127.0.0.1` на `localhost`.

<details><summary>Ответ</summary>

1. Контейнер завершается сразу. В логах: `Error: in 18+, these Docker images are configured to store database data in a format which is compatible with "pg_ctlcluster"...` и совет: `place a single mount at /var/lib/postgresql`.
2. Контейнер завершается: `Database is uninitialized and superuser password is not specified.` Папка данных пустая — нужно создавать сервер, а без пароля образ отказывается.
3. **Всё работает.** Данные уже есть, настройка не нужна, пароль в базе — старый. Неочевидно, но логично: переменная нужна только при первом запуске.
4. В логах: `ERROR:  syntax error at or near "CREAT"`, контейнер завершился. Но из-за `restart: unless-stopped` Docker запустил его снова, папка данных уже не пустая, настройка пропущена — и через несколько секунд `db` **healthy**, а таблицы `users` нет. Здоровье сервера не значит, что в базе то, что ты ждёшь.
5. Контейнер работает и `healthy`, но `check_db.py` получает ошибку подключения (`Connection refused` или `server closed the connection unexpectedly`): Docker пробрасывает соединение на порт 5433 контейнера, а сервер слушает 5432.
6. Работает. На твоём компьютере `localhost` — это и есть твой компьютер (`127.0.0.1` или `::1`). Сравни с разделом 6: там `localhost` писали **внутри** контейнера.

</details>

### Уровень 5. Второй сервис: заготовка для Telegram-бота

Настоящий бот появится позже. Сейчас сделай сервис `bot`, который при старте подключается к базе, печатает пользователей и завершается. Это ровно то, что бот будет делать первым делом: подключиться к `db`.

- Папка `bot/` с файлами `main.py` (скопируй туда `check_db.py`) и `Dockerfile`.
- В образе нужен `psycopg[binary]`.
- Адрес базы передай через `DATABASE_URL` в `environment`, собрав его из тех же переменных `.env`.
- `bot` должен стартовать только после того, как `db` станет `healthy`.

Перед тем как писать, ответь: какой хост будет в `DATABASE_URL` бота?

<details><summary>Ответ</summary>

`bot/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /code
RUN python -m pip install --no-cache-dir "psycopg[binary]~=3.3"
COPY main.py ./
CMD ["python", "main.py"]
```

В `compose.yaml`, в `services`, рядом с `db`:

```yaml
  bot:
    build: ./bot
    environment:
      DATABASE_URL: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
    depends_on:
      db:
        condition: service_healthy
```

```sh
docker compose up --build bot
```

`up bot` сам поднимет `db` (это зависимость), дождётся `healthy` и запустит бота. В выводе: `bot-1  | PostgreSQL 18.6 ...`, `bot-1  | (1, 'Anna', 30)`, затем `bot-1 exited with code 0` — скрипт закончился, и контейнер вместе с ним.

- Хост — `db`: бот работает в сети Compose.
- `${...}` в `DATABASE_URL` подставляет Compose из `.env` — пароль по-прежнему записан в одном месте.
- `ports` боту не нужны: он сам подключается к другим (к базе, к серверам Telegram), а к нему никто не подключается.
- Код бота не изменился по сравнению с `check_db.py`: изменилась только переменная окружения.

Бонус: замени `depends_on` на короткую форму `depends_on: [db]`, выполни `docker compose down -v` и `docker compose up --build bot`. Бот упадёт с `Connection refused`: он стартовал, пока база ещё настраивалась.

</details>

### Уровень 6. Отдельная база для бота

Боту нужна своя база `bot` со своим пользователем `bot`, чтобы он не мог случайно испортить таблицы бэкенда. Сервер — тот же. Сделай это стартовым скриптом. Что нужно выполнить, чтобы скрипт сработал?

<details><summary>Ответ</summary>

`db/init/02_bot.sql`:

```sql
CREATE USER bot WITH PASSWORD 'bot_secret';
CREATE DATABASE bot OWNER bot;
```

Скрипт выполнится только на пустом volume: `docker compose down -v`, затем `docker compose up -d --wait db`. Без `down -v` — те же две команды руками в `psql` (так делают, когда данные терять нельзя).

У бота: `DATABASE_URL: "postgresql://bot:bot_secret@db:5432/bot"`. Пароль бота тоже стоит вынести в `.env`, но в `.sql`-файле переменные Compose не подставляются — для этого пишут стартовый скрипт `.sh`, и это следующий шаг, когда понадобится.

Проверка: `docker compose exec db psql -U app -d fastapi_train -c "\l"` показывает базы `bot` (владелец `bot`) и `fastapi_train` (владелец `app`).

</details>

### Уровень 7. Бэкап

1. Добавь в `users` двух пользователей через `psql`.
2. Сделай бэкап (раздел 8).
3. `docker compose down -v`, `docker compose up -d --wait db`. Сколько строк в `users`?
4. Восстанови бэкап. Сколько строк теперь?

<details><summary>Ответ</summary>

После `down -v` и `up` — одна строка (Anna): база создана заново из `01_schema.sql`.

После восстановления — **всё ещё одна**. `psql` выведет ошибки:

```text
ERROR:  relation "users" already exists
ERROR:  duplicate key value violates unique constraint "users_pkey"
```

Бэкап пытается создать таблицу, которую уже создал стартовый скрипт, а потом вставить строку с `id = 1`, которая уже есть. Одна ошибка в `COPY` отменяет всю вставку — ни одна из трёх строк не попала. При этом `psql` по умолчанию не останавливается на ошибках, так что их легко пропустить: всегда читай вывод восстановления.

Вывод: восстанавливают в **пустую** базу. Или делают бэкап с флагами `--clean --if-exists`:

```sh
docker compose exec db pg_dump --clean --if-exists -U app -d fastapi_train -f /tmp/backup.sql
```

Тогда в файле перед каждым `CREATE` стоит `DROP ... IF EXISTS`: восстановление сначала удаляет существующие таблицы и создаёт их из бэкапа. Проверь: строк станет три.

</details>

### Уровень 8. Все четыре сервиса в одном файле

Используя [урок по Docker](docker-for-beginners.md) и уровень 8 [урока по Nuxt](nuxt-fastapi-for-beginners.md) (если ты его проходишь), собери скелет `compose.yaml` на четыре сервиса: `api`, `web`, `db`, `bot`. Код бэкенда пока не умеет работать с базой — это нормально: сейчас важно, чтобы **конфигурация** была правильной. Ответь по каждому сервису: нужны ли ему `ports`, нужен ли `DATABASE_URL`, от кого он зависит?

<details><summary>Ответ</summary>

```yaml
services:
  api:
    build: .
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      DATABASE_URL: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
    depends_on:
      db:
        condition: service_healthy

  web:
    build: ./frontend
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      NUXT_API_BASE_SERVER: "http://api:8000"
      NUXT_PUBLIC_API_BASE: "http://127.0.0.1:8000"
    depends_on:
      - api

  db:
    image: postgres:18
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql
      - ./db/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s
    restart: unless-stopped

  bot:
    build: ./bot
    environment:
      DATABASE_URL: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pg_data:
```

| Сервис | `ports` | `DATABASE_URL` | Зависит от |
|---|---|---|---|
| `api` | Да: к нему ходит браузер | Да, хост `db` | `db` (healthy) |
| `web` | Да: его открывает браузер | **Нет**: в базу не ходит | `api` |
| `db` | Только для тебя, `127.0.0.1` | — | — |
| `bot` | Нет | Да, хост `db` | `db` (healthy) |

Когда появится настоящий бот, в его `environment` добавится токен Telegram — тоже через `.env` (`BOT_TOKEN: ${BOT_TOKEN}`), и `restart: unless-stopped`, потому что бот, в отличие от заготовки, работает постоянно.

Проверка конфигурации без запуска: `docker compose config`. Если папки `frontend/` или `bot/` ещё нет, запускай только существующие сервисы: `docker compose up -d --build db api`.

</details>

---

## 11. Закрепление по памяти

Навык «написать с нуля» появляется не от прочтения, а от повторного вспоминания. Повтори Уровень 1 (пустой файл, без урока, с таймером):

| Когда | Что делать |
|---|---|
| Сегодня | Уровни 1–4 |
| Через 1 день | Уровень 1 + Уровень 5 |
| Через 3 дня | Уровень 1 + Уровень 6 + Уровень 7 |
| Через 7 дней | Уровень 8 с пустого листа |

После каждой попытки сравни с итоговым сервисом из раздела 5 и запиши, **в чём ошибся** — это твой личный список ловушек. Документацию в процессе открывать можно, но только чтобы уточнить синтаксис, а не за готовым решением.

### Самопроверка

- [ ] Могу назвать семь вопросов и какой строке `compose.yaml` соответствует каждый.
- [ ] Отличаю сервер, базу, пользователя и таблицу.
- [ ] Объясняю, почему без named volume данные пропадают при пересоздании контейнера, а с ним — нет.
- [ ] Знаю, что для `postgres:18` volume подключается к `/var/lib/postgresql`, и почему не к `.../data`.
- [ ] Знаю, что `POSTGRES_*` и `db/init` работают только на пустой папке данных, и меняю пароль через `ALTER USER`.
- [ ] Держу пароль в `.env`, а в git — только `.env.example`.
- [ ] Для любого клиента сразу говорю хост: `127.0.0.1` с компьютера, `db` из контейнера, и почему не `localhost`.
- [ ] Объясняю разницу `depends_on: [db]` и `condition: service_healthy`.
- [ ] Знаю, что удаляет `down`, а что `down -v`.
- [ ] Делаю бэкап и восстанавливаю его.
- [ ] Написал сервис `db` с нуля за 10 минут.

Когда сделаешь задания, сохрани `compose.yaml`, `.env.example`, `db/init/` и изменения `.gitignore` отдельным коммитом. Проверь в `git status`, что `.env` и `backup.sql` в коммит **не** попали.

### Что дальше

Для рабочего приложения следующие шаги: подключить FastAPI к базе вместо списка `fake_user_database` (SQLAlchemy или psycopg, адрес — из `DATABASE_URL`), миграции схемы (Alembic) вместо правки `01_schema.sql`, отдельный пользователь без прав суперпользователя для приложения, бэкапы по расписанию, пароль через `POSTGRES_PASSWORD_FILE` и Docker secrets вместо переменной. Добавляй каждое, только поняв, какую проблему оно решает.

---

## 12. Шпаргалка — открывать только после попыток

<details><summary>Скелет сервиса базы</summary>

```yaml
services:
  <имя сервиса>:
    image: postgres:<мажорная версия>
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "127.0.0.1:<порт компьютера>:5432"
    volumes:
      - <имя volume>:/var/lib/postgresql
      - ./<папка со скриптами>:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  <имя volume>:
```

</details>

<details><summary>Сервис, который подключается к базе</summary>

```yaml
  <имя сервиса>:
    build: ./<папка>
    environment:
      DATABASE_URL: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@<имя сервиса базы>:5432/${POSTGRES_DB}"
    depends_on:
      <имя сервиса базы>:
        condition: service_healthy
```

</details>

<details><summary>Команды psql</summary>

| Команда | Что делает |
|---|---|
| `\l` | Список баз |
| `\c <база>` | Переключиться на другую базу |
| `\dt` | Список таблиц |
| `\d <таблица>` | Колонки таблицы |
| `\du` | Список пользователей |
| `\conninfo` | Куда и под кем я подключён |
| `\q` | Выйти |

</details>

### Где искать синтаксис

| Хочу | Что искать |
|---|---|
| Переменные образа, путь данных, стартовые скрипты | Docker Hub → postgres → How to use this image |
| Проверка здоровья | Compose file reference → healthcheck |
| Ждать готовности другого сервиса | Compose file reference → depends_on |
| Подстановка из `.env` | Compose → Interpolation |
| SQL-команды | PostgreSQL documentation → SQL Commands |
| Подключение из Python | psycopg 3 documentation → Basic module usage |

Официальные материалы:

- [postgres на Docker Hub](https://hub.docker.com/_/postgres) — переменные `POSTGRES_*`, `/docker-entrypoint-initdb.d`, изменения в 18+.
- [Compose: healthcheck](https://docs.docker.com/reference/compose-file/services/#healthcheck) и [depends_on](https://docs.docker.com/reference/compose-file/services/#depends_on).
- [Compose: interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/) — `${...}` и файл `.env`.
- [Compose: volumes](https://docs.docker.com/reference/compose-file/volumes/) — named volumes.
- [psql](https://www.postgresql.org/docs/18/app-psql.html) — консольный клиент.
- [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html) — бэкапы.
- [psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/usage.html) — подключение из Python.
