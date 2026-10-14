# Telegram-бот на голом Bot API: фото QR-кода → API → база — для чайников 😄

**Цель урока:** после него ты сам пишешь Telegram-бота без библиотек вроде `aiogram` или `python-telegram-bot`: только HTTP-запросы к Bot API через `httpx`. Ты понимаешь, откуда бот узнаёт о новых сообщениях, как скачать присланную картинку, как вытащить из неё строку QR-кода и как передать её своему API так, чтобы ошибки на любом шаге превращались в понятный ответ пользователю, а не в молчание бота.

Урок построен на этом репозитории. Сейчас в `compose.yaml` два сервиса: `api` (FastAPI) и `pg_database` (PostgreSQL). Чек добавляется так: ты открываешь `/docs`, вставляешь в `POST /create_receipt` строку вида `t=20261010T2119&s=5099.62&fn=...` и нажимаешь Execute. К концу урока появится третий сервис `bot`: ты фотографируешь QR-код на чеке, отправляешь фото боту, бот сам достаёт из картинки строку, отправляет её в `POST /create_receipt`, и в базе появляются чек и его позиции. Готового кода в репозитории нет: всё, что описано в разделе 7, пишешь ты.

Команды выполняются **из корня репозитория** (там, где лежит `compose.yaml`) и одинаково работают в PowerShell и в Linux shell, если не сказано иначе. Всё проверено на Python 3.12, `httpx` 0.28, `pydantic-settings` 2.16, `pillow` 12.3, `zxing-cpp` 3.1, Docker 29 и Docker Compose v2. Bot API — это внешний сервис Telegram: если какой-то ответ выглядит не так, как в уроке, сверься с официальной страницей core.telegram.org/bots/api.

## 0. Как проходить урок

Правила те же, что в [уроке по Docker](docker-for-beginners.md), [уроке по Postgres](postgres-docker-for-beginners.md), [уроке по ORM](orm-sqlalchemy-for-beginners.md) и [уроке по OpenAI](openai-categorizer-for-beginners.md):

1. **Печатай руками.** Не копируй блоки кода из урока в файлы.
2. **Одна настройка — одна проверка.** После каждого шага запускай и смотри, что изменилось именно то, что ожидал.
3. **Сначала предскажи — потом запусти.**
4. **Ответы — в свёрнутых блоках.** Открывай их только после своей попытки.

И два новых правила:

5. **Смотри на сырой JSON.** Bot API отвечает JSON-ом, и всё, что делает бот, — это чтение полей из этого JSON. Прежде чем писать `message["photo"][-1]["file_id"]`, открой настоящий ответ Telegram и найди это поле глазами.
6. **Токен бота — это пароль.** Кто знает токен, тот управляет ботом: читает сообщения, которые ему пишут, и отвечает от его имени. Токен живёт только в `.env` и в переменной окружения, никогда в коде и никогда в логах.

План: что мы строим и зачем (раздел 1) → почему без библиотек (2) → шесть вопросов перед написанием бота (3) → инструменты и токен (4) → Bot API руками в браузере и в песочнице (5) → безопасность: токен и чужие люди (6) → собрать проект по одному файлу (7) → проследить одно фото целиком (8) → правила, на которых ошибаются (9) → диагностика (10) → тренировка (11) → повторение по памяти (12) → шпаргалка (13).

---

## 1. Что мы строим и зачем

| Объект | Что это | Аналогия |
|---|---|---|
| Bot API | HTTP-сервис Telegram по адресу `https://api.telegram.org`. Всё, что умеет бот, — это запросы туда | Окошко почты, куда приходишь за письмами и отдаёшь свои |
| BotFather | Официальный бот Telegram, который создаёт других ботов и выдаёт им токены | Паспортный стол для ботов |
| Токен | Строка вида `123456789:AAH...`. Входит прямо в адрес каждого запроса: `/bot<токен>/getMe` | Ключ от абонентского ящика |
| Метод | Действие Bot API: `getMe`, `getUpdates`, `sendMessage`, `getFile`. Пишется в конце адреса | Окошко с табличкой «Выдача писем» |
| Update | Одно событие для бота: пришло сообщение, кто-то нажал кнопку. У каждого есть номер `update_id` | Одно письмо в ящике |
| `offset` | Параметр `getUpdates`: «я уже прочитал всё до этого номера, выдай новые». Так Telegram понимает, что update можно забыть | Отметка «получено» в журнале почты |
| Long polling | `getUpdates` с параметром `timeout=30`: Telegram держит запрос открытым до 30 секунд и отвечает сразу, как только появится update | Ждать у окошка, пока письмо не принесут |
| Webhook | Обратный способ: Telegram сам шлёт update на твой публичный HTTPS-адрес | Курьер, который приносит письма домой (нужен адрес) |
| `chat_id` и `from.id` | Номер чата, куда отвечать, и номер пользователя, который написал. В личке они совпадают | Адрес отправителя на конверте |
| `file_id` и `file_path` | Telegram не присылает картинку в update. Он присылает `file_id`, по нему `getFile` выдаёт `file_path`, а по `file_path` файл уже скачивается | Квитанция на посылку → номер ячейки → сама посылка |
| QR-код | Картинка, в которой закодирована строка. На кассовом чеке это `t=...&s=...&fn=...&i=...&fp=...&n=...` | Штрихкод, только квадратный |
| `zxing-cpp` | Библиотека, которая находит QR-коды на картинке и возвращает их текст. Это не обёртка Telegram, а «глаза» бота | Сканер на кассе |

**Бот — это обычная программа, которая в цикле спрашивает у Telegram «что нового?», делает работу и отвечает. Никакой магии в ботах нет, есть только HTTP-запросы.**

Ещё три факта, которые понадобятся дальше:

- **Боту не нужен открытый порт.** При long polling бот сам ходит в Telegram, а не Telegram в бота. Поэтому у сервиса `bot` в `compose.yaml` не будет `ports`, и бот прекрасно работает на твоём ноутбуке за роутером.
- **Бот не ходит в базу.** В [уроке по Postgres](postgres-docker-for-beginners.md) на схеме бот подключался к `db` напрямую. Теперь у нас есть `POST /create_receipt`, в котором уже живёт вся логика: проверка дубля, сервис проверки чеков, группы через OpenAI, запись в базу одной транзакцией. Если бот будет писать в базу сам, эту логику придётся повторить и потом чинить в двух местах. Поэтому бот — это ещё один **клиент** API, такой же, как страница `/docs`.
- **Каждое внешнее звено может не ответить.** Telegram, твой API, сервис проверки чеков. Бот должен на любую ошибку отвечать человеку понятной фразой и продолжать работать.

### Как это выглядит в реальной работе

```text
Телефон: фото QR-кода
   │
   ▼
api.telegram.org ◄──── 1. getUpdates (long polling) ──── bot
                 ◄──── 2. getFile + скачивание фото ──── bot
                                                          │ 3. zxing-cpp: картинка → "t=...&s=...&fn=..."
                                                          │ 4. POST http://api:8000/create_receipt
                                                          ▼
                                                         api ──► сервис проверки чеков, OpenAI
                                                          │
                                                          ▼
                                                     pg_database
                 ◄──── 5. sendMessage "Чек сохранён, id 42" ── bot
```

И то же самое в `compose.yaml`:

```text
Интернет: api.telegram.org
   ▲
   │ исходящие HTTPS-запросы (портов наружу не нужно)
┌──┼────────────────────────── сеть Compose ─────────────────────────┐
│ bot ──http://api:8000──> api ──pg_database:5432──> pg_database     │
└────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 127.0.0.1:8000 (ты, браузер, /docs)
```

---

## 2. Почему без библиотек

Популярные библиотеки (`aiogram`, `python-telegram-bot`) удобные, но они прячут ровно то, что полезно один раз сделать руками.

<details><summary>Вопрос 1. Что именно делает за тебя библиотека?</summary>

- Крутит цикл `getUpdates` и правильно двигает `offset`.
- Превращает JSON update в объекты (`message.photo[-1].file_id`).
- Раскладывает update по обработчикам (`@router.message(F.photo)`).
- Скачивает файлы в два шага (`getFile` → скачивание).
- Повторяет запрос при сетевых ошибках и при `429 Too Many Requests`.

Всё это — 60–80 строк твоего кода. Когда ты один раз напишешь их сам, библиотека перестанет быть чёрным ящиком: ты будешь знать, что происходит под `@router.message`, и сможешь читать её ошибки.
</details>

<details><summary>Вопрос 2. Значит, библиотеки не нужны вообще?</summary>

Нужны, когда бот вырастет: кнопки, диалоги из нескольких шагов, сотни пользователей, webhook за балансировщиком. Сейчас у бота одна задача, и голый Bot API решает её проще, чем любая библиотека. Это та же мысль, что с pandas в [уроке по OpenAI](openai-categorizer-for-beginners.md): инструмент берут под задачу, а не потому что «так принято».
</details>

<details><summary>Вопрос 3. А zxing-cpp — это не та же «готовая библиотека»?</summary>

Нет. Ограничение было «не брать готовые обёртки Telegram». Распознать QR-код на фотографии — отдельная задача из компьютерного зрения: найти три квадрата по углам, выровнять перспективу, разобрать биты, исправить ошибки. Писать это самому — тема для отдельного курса. `zxing-cpp` ничего не знает про Telegram: она получает картинку и возвращает строку.
</details>

---

## 3. Алгоритм: шесть вопросов перед написанием бота

Любой бот собирается из ответов на шесть вопросов. Ответь на них сам, прежде чем открывать подсказки.

| № | Вопрос | Ответ для нашего проекта |
|---|---|---|
| 1 | **Как бот узнаёт о новых сообщениях?** | |
| 2 | **Кому бот вообще отвечает?** | |
| 3 | **Как из сообщения получить нужные данные?** | |
| 4 | **Куда бот отправляет результат?** | |
| 5 | **Что бот отвечает на каждую ошибку?** | |
| 6 | **Где хранится токен?** | |

<details><summary>Ответы</summary>

1. Long polling: `getUpdates` с `timeout=30` в бесконечном цикле, `offset` = последний `update_id` + 1.
2. Только Telegram-id из списка `allowed_user_ids`. Всем остальным — «Нет доступа» и их id. Без этого любой, кто найдёт бота поиском, добавит свои чеки в твою базу.
3. Фото: самый большой размер из `photo` → `getFile` → скачивание → `zxing-cpp` → строка, у которой есть ключи `t, s, fn, i, fp, n`. Ещё принимаем картинку, отправленную файлом, и саму строку текстом.
4. `POST /create_receipt` по адресу `http://api:8000` внутри Compose.
5. `201` → «Чек сохранён, id N»; `409` → «Этот чек уже есть»; `400/502/500` → текст ошибки из API; API не отвечает → «API недоступно»; QR не найден → подсказка, как прислать лучше.
6. В `.env` (`TELEGRAM_SETTINGS__TOKEN`), который не попадает в git. В коде, логах и `repr` настроек токена нет.
</details>

---

## 4. Подготовь инструменты

1. **Создай бота.** В Telegram найди `@BotFather` (с синей галочкой), отправь `/newbot`, придумай имя (любое) и username (должен заканчиваться на `bot`, например `fastapi_train_receipts_bot`). BotFather пришлёт токен. Сохрани его в менеджер паролей или хотя бы в отдельный файл вне репозитория.
2. **Нажми Start.** Открой своего бота по ссылке из ответа BotFather и нажми «Start» (или отправь `/start`). Бот не может написать человеку первым: пока ты не начал диалог, `sendMessage` тебе вернёт ошибку.
3. **Токен — в переменную окружения терминала.** Для песочницы:

   ```powershell
   # PowerShell
   $env:TG_TOKEN = "123456789:AAH..."
   ```

   ```bash
   # Linux / macOS
   export TG_TOKEN="123456789:AAH..."
   ```

4. **Библиотеки.** В локальном `.venv` поставь:

   ```bash
   pip install "httpx~=0.28" "pillow~=12.3" "zxing-cpp~=3.1" "qrcode[pil]"
   ```

   `qrcode` нужна только в песочнице, чтобы нарисовать тестовый QR-код. В проект она не пойдёт.

5. **Папка `sandbox/`** уже есть в `.gitignore`. Все эксперименты раздела 5 делай там.
6. **Чек под рукой.** Возьми любой бумажный чек с QR-кодом. Если чека нет, в разделе 5.6 ты нарисуешь QR-код сам.

<details><summary>Вопрос: если токен утёк, что делать?</summary>

Открой `@BotFather` → `/mybots` → твой бот → «API Token» → «Revoke current token». Старый токен перестанет работать сразу, BotFather выдаст новый. Поменяй его в `.env` и перезапусти бота. Удалить коммит с токеном недостаточно, нужно именно отозвать токен: GitHub сканируют боты, и токен успевают найти за минуты.
</details>

---

## 5. Шаг ноль: Bot API руками

Прежде чем писать бота, поговори с Telegram сам: сначала прямо из браузера, потом из одного файла Python. В адресах ниже `<ТОКЕН>` замени на свой токен **целиком, вместе с угловыми скобками**. Слово `bot` перед токеном остаётся: `https://api.telegram.org/bot123456789:AAH.../getMe`.

> Адрес с токеном останется в истории браузера. Для своего компьютера это допустимо, но не делай так на чужом и не отправляй скриншоты адресной строки. Если хочешь без браузера, те же адреса можно открыть командой `curl "https://api.telegram.org/bot$TG_TOKEN/getMe"` в Linux или `Invoke-RestMethod "https://api.telegram.org/bot$($env:TG_TOKEN)/getMe" | ConvertTo-Json -Depth 10` в PowerShell.

### 5.1. Кто я: getMe

Открой в браузере:

```text
https://api.telegram.org/bot<ТОКЕН>/getMe
```

**Предскажи:** что придёт в ответ?

<details><summary>Что ты увидел</summary>

```json
{"ok": true, "result": {"id": 123456789, "is_bot": true, "first_name": "...", "username": "fastapi_train_receipts_bot", ...}}
```

У **каждого** ответа Bot API одинаковая обёртка: поле `ok` и либо `result` (если всё хорошо), либо `error_code` и `description` (если нет). Это главное, что нужно запомнить о Bot API: сначала смотрим `ok`, потом берём `result`.

Обрати внимание: `id` бота совпадает с числом в начале токена.
</details>

Теперь испорть токен: поменяй последнюю букву и обнови страницу. А потом удали слово `bot` перед токеном.

<details><summary>Что ты увидел</summary>

- Неверный токен: `{"ok": false, "error_code": 401, "description": "Unauthorized"}`.
- Без `bot` в адресе: `{"ok": false, "error_code": 404, "description": "Not Found"}`. Telegram даже не понял, что это запрос к боту.

Эти два ответа ты ещё увидишь в логах бота. Теперь ты знаешь, что они значат.
</details>

### 5.2. Что нового: getUpdates

Напиши своему боту в Telegram «привет». Бот промолчит: программы ещё нет. Открой:

```text
https://api.telegram.org/bot<ТОКЕН>/getUpdates
```

Найди глазами в ответе: `update_id`, текст сообщения, `id` того, кто написал, и `id` чата.

<details><summary>Как устроен update</summary>

```json
{
  "ok": true,
  "result": [
    {
      "update_id": 815372001,
      "message": {
        "message_id": 2,
        "from": {"id": 987654321, "is_bot": false, "first_name": "Jenifer", "language_code": "ru"},
        "chat": {"id": 987654321, "first_name": "Jenifer", "type": "private"},
        "date": 1792000000,
        "text": "привет"
      }
    }
  ]
}
```

- `result` — **список**: update может быть несколько.
- `message.from.id` — кто написал. Запиши это число: это **твой Telegram-id**, он понадобится в разделе 6.
- `message.chat.id` — куда отвечать. В личке он равен `from.id`, в группе будет другим (отрицательным).
- `message.message_id` — номер сообщения внутри чата. Нужен, чтобы ответить «цитатой» на конкретное сообщение.
- `date` — время в секундах Unix.
</details>

Обнови страницу ещё раз. **Предскажи:** сообщение «привет» исчезнет?

<details><summary>Ответ</summary>

Нет. Telegram отдаёт update снова и снова, пока ты не скажешь, что прочитал его. Говорят это параметром `offset`. Возьми `update_id` из ответа, прибавь 1 и открой:

```text
https://api.telegram.org/bot<ТОКЕН>/getUpdates?offset=815372002
```

Список пуст. Теперь открой адрес **без** `offset`: тоже пусто. Telegram запомнил подтверждение и удалил всё, что было до этого номера.

Если бот забудет двигать `offset`, он будет обрабатывать одно и то же сообщение бесконечно. Если подтвердить update и упасть до обработки, сообщение потеряется. Запомни: `offset` = «последний обработанный `update_id` + 1».

Ещё одна деталь: неподтверждённые update Telegram хранит 24 часа. Если бот был выключен сутки, старые сообщения пропадут.
</details>

### 5.3. Long polling: ждём у окошка

Открой:

```text
https://api.telegram.org/bot<ТОКЕН>/getUpdates?offset=815372002&timeout=30
```

(подставь свой `offset`). Страница «повисла». Через 10 секунд напиши боту что-нибудь в Telegram.

<details><summary>Что произошло</summary>

Страница ответила **сразу**, как только пришло сообщение. Если бы ты ничего не написал, через 30 секунд пришёл бы пустой `result: []`.

Это и есть long polling. Без `timeout` бот спрашивал бы «что нового?» без остановки: десятки запросов в секунду впустую. С `timeout=30` — один запрос в 30 секунд, когда тихо, и мгновенная реакция, когда пишут.

Отсюда важное правило для кода: **таймаут HTTP-клиента должен быть больше `timeout` в `getUpdates`**. Если `httpx` ждёт ответа 10 секунд, а Telegram держит запрос 30, бот будет падать по `ReadTimeout` каждые 10 секунд тишины.
</details>

### 5.4. Ответить: sendMessage

Подставь свой `chat_id`:

```text
https://api.telegram.org/bot<ТОКЕН>/sendMessage?chat_id=987654321&text=Hello
```

Сообщение пришло в Telegram от имени бота. Теперь поменяй `chat_id` на случайное число.

<details><summary>Что ты увидел</summary>

`{"ok": false, "error_code": 400, "description": "Bad Request: chat not found"}`. Бот может писать только в чаты, где с ним уже начали диалог. Если человек заблокировал бота, будет `403 Forbidden: bot was blocked by the user`.

Браузер отправляет параметры в адресе (GET). Из кода мы будем отправлять их телом запроса в JSON (POST): так проще передавать вложенные объекты и не нужно думать про кодирование русских букв в адресе. Bot API принимает оба способа.
</details>

### 5.5. Картинка: photo → getFile → скачивание

Отправь боту фотографию QR-кода с чека (обычным фото, не файлом). Открой `getUpdates` (с текущим `offset`).

<details><summary>Как выглядит фото в update</summary>

```json
"message": {
  "message_id": 5,
  "from": {"id": 987654321, ...},
  "chat": {"id": 987654321, ...},
  "photo": [
    {"file_id": "AgACAgIAAxkB...AAQ", "file_unique_id": "AQAD...", "file_size": 1293, "width": 90, "height": 51},
    {"file_id": "AgACAgIAAxkB...AAg", "file_unique_id": "AQAD...", "file_size": 15837, "width": 320, "height": 180},
    {"file_id": "AgACAgIAAxkB...AAw", "file_unique_id": "AQAD...", "file_size": 98124, "width": 1280, "height": 720}
  ]
}
```

Никакой картинки в update нет, есть только список **размеров** одного фото, от маленького к большому. Для QR-кода нужен самый большой: `photo[-1]`. И у сообщения с фото нет поля `text` (подпись, если есть, лежит в `caption`).
</details>

Скопируй `file_id` последнего размера и открой:

```text
https://api.telegram.org/bot<ТОКЕН>/getFile?file_id=AgACAgIAAxkB...AAw
```

В ответе есть `file_path`, например `photos/file_3.jpg`. Теперь открой:

```text
https://api.telegram.org/file/bot<ТОКЕН>/photos/file_3.jpg
```

<details><summary>Что ты увидел и на что обратить внимание</summary>

Браузер показал (или скачал) твою фотографию. Два шага, потому что `file_id` — это постоянная «квитанция», а ссылка для скачивания живёт около часа.

Обрати внимание на адрес: `/file/bot<ТОКЕН>/...` — сначала `file`, потом `bot`. Это **другой** адрес, не тот, что у методов. Перепутать их — классическая ошибка.

Ограничение: через `getFile` бот может скачать файл до 20 МБ. Фото из Telegram всегда меньше.
</details>

Теперь отправь то же фото **файлом** (в мобильном Telegram: скрепка → «Файл»; на компьютере — снять галочку «Сжать изображение»). Посмотри в `getUpdates`, чем отличается сообщение.

<details><summary>Ответ</summary>

Вместо `photo` пришло поле `document` с одним `file_id`, именем файла и `mime_type`, например `"image/jpeg"`. Telegram не сжимал картинку, поэтому мелкий QR-код на таком файле читается лучше. Бот будет принимать оба варианта, а файлы, у которых `mime_type` не начинается с `image/`, — игнорировать.
</details>

### 5.6. QR-код руками: картинка → строка

Создай `sandbox/make_qr.py`, который рисует тестовый QR-код (пригодится, если чека нет под рукой, и для тестов):

```python
import qrcode

RAW = "t=20261010T2119&s=5099.62&fn=7380440903609803&i=22385&fp=3751356996&n=1"
qrcode.make(RAW).save("sandbox/receipt_qr.png")
print("Готово: sandbox/receipt_qr.png")
```

И `sandbox/qr_try.py`, который читает QR-код с картинки:

```python
import sys

import zxingcpp
from PIL import Image

image = Image.open(sys.argv[1])
barcodes = zxingcpp.read_barcodes(image)
print("Найдено кодов:", len(barcodes))
for barcode in barcodes:
    print(barcode.format, "→", barcode.text)
```

Запусти: `python sandbox/make_qr.py`, потом `python sandbox/qr_try.py sandbox/receipt_qr.png`. Затем — на фото чека, которое ты скачал в 5.5.

**Предскажи:** что вернёт `read_barcodes` для картинки без QR-кода? А для чека, на котором два QR-кода?

<details><summary>Ответы</summary>

- Без кода: пустой список `[]`, а не ошибка. Значит, в коде проверяем «список пустой?», а не ловим исключение.
- Два кода: список из двух элементов. Такое бывает: на некоторых чеках рядом с налоговым QR-кодом печатают рекламный со ссылкой на сайт магазина. Поэтому бот не берёт «первый попавшийся» код, а ищет тот, который **похож на чек**.

Как понять, что строка похожа на чек? У налогового QR-кода всегда есть шесть параметров: `t` (время), `s` (сумма), `fn` (номер фискального накопителя), `i` (номер документа), `fp` (фискальный признак), `n` (тип операции). Проверь в песочнице:

```python
from urllib.parse import parse_qs

print(parse_qs("t=20261010T2119&s=5099.62&fn=7380440903609803&i=22385&fp=3751356996&n=1").keys())
print(parse_qs("https://shop.example/promo").keys())
```

Если все шесть ключей на месте, строка подходит.
</details>

<details><summary>Если на настоящем фото кодов «Найдено: 0»</summary>

- QR-код слишком мелкий на фото: подойди ближе, чтобы код занимал хотя бы четверть кадра.
- Фото смазано или чек помят: разгладь, сфотографируй при хорошем свете.
- Telegram сильно сжал фото: отправь файлом (5.5).
- Попробуй `image.convert("L")` (перевести в оттенки серого) перед `read_barcodes`. Обычно `zxing-cpp` справляется и с цветной картинкой, но серый вариант надёжнее и работает с любыми форматами (PNG с прозрачностью, палитра).
</details>

### 5.7. Эхо-бот из одного файла

Теперь то же самое из Python. Создай `sandbox/tg_try.py`:

```python
import asyncio
import os

import httpx

TOKEN = os.environ["TG_TOKEN"]
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


async def call(client: httpx.AsyncClient, method: str, params: dict | None = None, timeout: float = 10) -> dict:
    response = await client.post(f"{BASE_URL}/{method}", json=params or {}, timeout=timeout)
    data = response.json()
    print(method, "→", data)
    return data


async def main() -> None:
    async with httpx.AsyncClient() as client:
        await call(client, "getMe")
        offset = 0
        while True:
            data = await call(client, "getUpdates", {"offset": offset, "timeout": 30}, timeout=40)
            for update in data["result"]:
                offset = update["update_id"] + 1
                message = update.get("message")
                if message and "text" in message:
                    await call(client, "sendMessage", {
                        "chat_id": message["chat"]["id"],
                        "text": "Эхо: " + message["text"],
                    })


asyncio.run(main())
```

Запусти `python sandbox/tg_try.py` и напиши боту пару сообщений. Остановка — `Ctrl+C`.

<details><summary>Вопрос: зачем timeout=40, если в getUpdates timeout=30?</summary>

Это два разных таймаута. `"timeout": 30` в параметрах — это просьба к Telegram держать запрос до 30 секунд. `timeout=40` у `httpx` — сколько твой клиент готов ждать ответа. Если второй меньше первого, `httpx` бросит `ReadTimeout` раньше, чем Telegram успеет ответить пустым списком (5.3). Запас в 10 секунд — на сеть.
</details>

<details><summary>Вопрос: почему offset двигается до обработки сообщения, а не после?</summary>

Присваивание `offset = ...` само по себе ничего не отправляет в Telegram. Подтверждение уйдёт только со **следующим** `getUpdates`, а он вызывается после того, как обработаны все update из текущей пачки. Так что если программа упадёт посреди обработки, Telegram отдаст эти update снова при следующем запуске. Для нашего бота это безопасно: если один и тот же чек придёт дважды, API ответит `409`.
</details>

**Расширь эхо-бота:** если в сообщении есть `photo`, вызови `getFile`, скачай файл (`client.get(...)` по адресу из 5.5), прогони байты через `zxing-cpp` и ответь текстом QR-кода. Картинку из байтов открывает `Image.open(io.BytesIO(data))`.

<details><summary>Один из вариантов</summary>

```python
                if message and "photo" in message:
                    file_id = message["photo"][-1]["file_id"]
                    file = (await call(client, "getFile", {"file_id": file_id}))["result"]
                    response = await client.get(f"https://api.telegram.org/file/bot{TOKEN}/{file['file_path']}")
                    image = Image.open(io.BytesIO(response.content))
                    texts = [b.text for b in zxingcpp.read_barcodes(image)]
                    await call(client, "sendMessage", {
                        "chat_id": message["chat"]["id"],
                        "text": "\n".join(texts) or "QR-код не найден",
                    })
```

Не забудь импорты: `io`, `zxingcpp`, `from PIL import Image`. Это уже почти весь бот. В проекте мы разложим то же самое по файлам и добавим обработку ошибок.
</details>

### 5.8. Сломай специально

Сделай по очереди и запиши, что увидел:

1. Запусти `tg_try.py` в **двух** терминалах одновременно.
2. Поставь `timeout=5` у `httpx` для `getUpdates` и ничего не пиши боту.
3. Выключи интернет (или впиши в `BASE_URL` адрес `https://api.telegram.invalid`) и запусти.
4. Вызови `getFile` с `file_id="abc"`.
5. Отправь боту стикер.

<details><summary>Ответы</summary>

1. Второй `getUpdates` выбивает первый: `{"ok": false, "error_code": 409, "description": "Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"}`. У одного токена может быть только один получатель update. Запомни этот текст: в Docker он появится, если бот запущен и в контейнере, и в PyCharm одновременно.
2. Через 5 секунд — `httpx.ReadTimeout`, и скрипт падает.
3. `httpx.ConnectError`. Скрипт падает. В проекте мы поймаем это и повторим через несколько секунд.
4. `{"ok": false, "error_code": 400, "description": "Bad Request: invalid file_id"}`. HTTP-код ответа тоже 400, но тело всё равно JSON с описанием. Поэтому в проекте мы не вызываем `raise_for_status()` для методов Bot API, а читаем `ok` и `description`: там написано, что именно не так.
5. Ничего: у стикера нет поля `text`, эхо-бот его пропустил. Посмотри в `getUpdates`, как выглядит стикер. Каждый тип сообщения — это своё поле (`text`, `photo`, `document`, `sticker`, `voice`...).
</details>

---

## 6. Безопасность: токен и чужие люди

Бот публичен: любой человек может найти его поиском по username и написать. А наш API пока пишет **все** чеки от имени админа (`ADMIN_USER_ID` в `app/constants.py`). Без проверки любой незнакомец добавит свои чеки в твою статистику.

Поэтому первое, что бот делает с сообщением, — проверяет `message["from"]["id"]` по списку разрешённых. Тем, кого нет в списке, бот отвечает «Нет доступа» и сообщает их id. Это удобно: чтобы добавить себя (или кого-то из семьи), достаточно написать боту, получить id и вписать его в `.env`.

<details><summary>Вопрос: почему проверяем from.id, а не chat.id?</summary>

`chat.id` — это чат. Если бота добавят в группу, `chat.id` будет общим для всех участников группы, а писать будут разные люди. `from.id` — это всегда конкретный человек.
</details>

Вторая опасность — токен в логах. Токен входит **в адрес** каждого запроса: `https://api.telegram.org/bot123456789:AAH.../getUpdates`. А адреса попадают в два места:

- **Логи `httpx`.** Если включить логирование на уровне `INFO`, `httpx` пишет строку `HTTP Request: POST https://api.telegram.org/bot123456789:AAH.../getUpdates "HTTP/1.1 200 OK"` на каждый запрос. Логи контейнера читает любой, у кого есть доступ к Docker, а ещё их любят вставлять в чаты, когда просят помощи.
- **Текст исключений.** `response.raise_for_status()` бросает `HTTPStatusError` с текстом `Client error '404 Not Found' for url 'https://api.telegram.org/file/bot123456789:AAH.../photos/file_3.jpg'`. Если такое исключение попадёт в `logger.exception`, токен окажется в логе вместе с трейсбеком.

Защита в разделе 7: уровень логов `httpx` поднимаем до `WARNING`, а исключения `httpx` в клиенте Telegram заменяем своими, в которых нет адреса.

<details><summary>Вопрос: а строку QR-кода можно отправлять в API без проверки?</summary>

API сам её проверит: схема `ReceiptBase` и сервис проверки чеков. Проверка в боте нужна не для безопасности, а для удобства: если на фото рекламный QR-код со ссылкой, бот сразу скажет «не нашёл QR-код чека», вместо того чтобы гонять запрос через API и внешний сервис и получать `400`. Правило то же, что в уроке по OpenAI: всё, что пришло снаружи (от модели, от пользователя, с картинки), проверяется перед использованием.
</details>

---

## 7. Собираем проект по одному файлу

Создай ветку под работу от свежего `main`:

```bash
git checkout main
git pull
git checkout -b telegram-bot
```

Бот — отдельная программа со своими зависимостями (ему не нужны SQLAlchemy и OpenAI, а API не нужны Pillow и zxing-cpp). Поэтому он живёт в отдельной папке `bot/` рядом с `app/` и собирается в свой образ. Структура в конце:

```text
bot/
├── __init__.py          пустой
├── requirements.txt     зависимости бота
├── Dockerfile           образ бота
├── config.py            настройки из .env
├── telegram_api.py      TelegramApi: свой маленький клиент Bot API
├── qr.py                картинка → строки QR-кодов, проверка «похоже на чек»
├── receipt_api.py       ReceiptApi: клиент нашего FastAPI
├── handlers.py          что делать с одним сообщением
└── main.py              цикл long polling
```

Запускать бота будем как пакет: `python -m bot.main` из корня репозитория. Тогда импорты внутри выглядят так же, как в API: `from bot.config import get_settings` (у API — `from app.config import get_settings`).

### Шаг 1. Папка и зависимости — `bot/requirements.txt`

Создай папку `bot/`, в ней пустой `__init__.py` и `requirements.txt`:

```text
httpx~=0.28
pydantic-settings~=2.16
pillow~=12.3
zxing-cpp~=3.1
```

Поставь их в свой `.venv`: `pip install -r bot/requirements.txt`.

<details><summary>Вопрос: почему не дописать эти строки в общий requirements.txt?</summary>

Тогда образ API потащит Pillow и zxing-cpp, которые ему не нужны, а образ бота — SQLAlchemy, asyncpg и openai. Образы станут больше, сборка дольше, а обновление библиотеки для одного сервиса будет пересобирать оба. Один сервис — один список зависимостей.
</details>

### Шаг 2. Настройки — `bot/config.py` и `.env`

По образцу `app/config.py`:

```python
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramSettings(BaseModel):
    token: str = Field(repr=False)
    base_url: str = "https://api.telegram.org"
    allowed_user_ids: list[int] = []
    poll_timeout: int = 30


class ReceiptApiSettings(BaseModel):
    url: str = "http://127.0.0.1:8000"
    timeout: int = 90


class BotSettings(BaseSettings):
    telegram_settings: TelegramSettings
    receipt_api_settings: ReceiptApiSettings = ReceiptApiSettings()

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()
```

В `.env` добавь:

```env
TELEGRAM_SETTINGS__TOKEN=123456789:AAH...
TELEGRAM_SETTINGS__ALLOWED_USER_IDS=[987654321]
RECEIPT_API_SETTINGS__URL=http://127.0.0.1:8000
```

И те же имена (без настоящего токена) — в `.env.example`.

Проверь, что настройки читаются: `python -c "from bot.config import get_settings; print(get_settings())"`.

<details><summary>Что должно напечататься</summary>

```text
telegram_settings=TelegramSettings(base_url='https://api.telegram.org', allowed_user_ids=[987654321], poll_timeout=30) receipt_api_settings=ReceiptApiSettings(url='http://127.0.0.1:8000', timeout=90)
```

Токена в выводе нет: это `repr=False`. Если вместо этого ошибка `Field required ... telegram_settings`, в `.env` нет `TELEGRAM_SETTINGS__TOKEN` или ты запускаешь не из корня репозитория.
</details>

<details><summary>Вопрос: почему список id записан как [987654321]?</summary>

`pydantic-settings` читает сложные типы (списки, словари) из переменной окружения как JSON. Поэтому список — в квадратных скобках, через запятую: `[987654321,123456789]`. Если написать просто `987654321`, будет ошибка `Input should be a valid list`.
</details>

<details><summary>Вопрос: .env общий у API и бота. API не сломается от новых переменных?</summary>

Нет: у обоих `extra="ignore"`. API пропустит `TELEGRAM_SETTINGS__*`, бот пропустит `POSTGRES_SETTINGS__*` и `OPEN_AI_SETTINGS__*`.
</details>

<details><summary>Вопрос: зачем timeout API 90 секунд? Это же очень долго</summary>

Посчитай, сколько может идти `POST /create_receipt`: сервис проверки чеков (до 30 секунд по `CHECK_RECEIPT_SETTINGS__TIMEOUT`) плюс OpenAI (до 30 секунд и один повтор). Если бот сдастся через 10 секунд, он скажет «API не отвечает», а API тем временем спокойно сохранит чек. Человек отправит фото ещё раз и получит «Этот чек уже есть». Таймаут клиента должен быть больше, чем самый долгий нормальный ответ сервера.
</details>

<details><summary>Вопрос: зачем base_url, если адрес Telegram всегда один?</summary>

Для тестов и для особых случаев. В тестах (уровень 5 тренировки) ты подставишь адрес своего фейкового сервера и проверишь бота без интернета. А ещё Telegram позволяет поднять свой локальный сервер Bot API, и тогда адрес будет другим. В обычной работе в `.env` эту строку не пишут, и действует значение по умолчанию.
</details>

### Шаг 3. Клиент Bot API — `bot/telegram_api.py`

Это твоя замена библиотеке: один общий метод `call` и несколько удобных методов поверх него.

```python
from typing import Any

import httpx


class TelegramError(Exception):
    """Telegram не ответил или ответил ok=false."""


class TelegramApi:
    def __init__(self, token: str, base_url: str, client: httpx.AsyncClient) -> None:
        self.token = token
        self.base_url = base_url
        self.client = client

    async def call(self, method: str, params: dict | None = None, http_timeout: float = 10) -> Any:
        url = f"{self.base_url}/bot{self.token}/{method}"
        try:
            response = await self.client.post(url, json=params or {}, timeout=http_timeout)
            data = response.json()
        except httpx.HTTPError as exc:
            raise TelegramError(f"{method}: нет связи с Telegram ({type(exc).__name__})") from None
        except ValueError:
            raise TelegramError(f"{method}: Telegram вернул не JSON, HTTP {response.status_code}") from None

        if not data.get("ok"):
            raise TelegramError(f"{method}: {data.get('error_code')} {data.get('description')}")
        return data["result"]

    async def get_updates(self, offset: int, timeout: int) -> list[dict]:
        params = {"offset": offset, "timeout": timeout, "allowed_updates": ["message"]}
        return await self.call("getUpdates", params, http_timeout=timeout + 10)

    async def send_message(self, chat_id: int, text: str, reply_to: int | None = None) -> dict:
        params: dict = {"chat_id": chat_id, "text": text}
        if reply_to is not None:
            params["reply_parameters"] = {"message_id": reply_to}
        return await self.call("sendMessage", params)

    async def send_chat_action(self, chat_id: int, action: str = "typing") -> None:
        await self.call("sendChatAction", {"chat_id": chat_id, "action": action})

    async def download_file(self, file_id: str) -> bytes:
        file = await self.call("getFile", {"file_id": file_id})
        url = f"{self.base_url}/file/bot{self.token}/{file['file_path']}"
        try:
            response = await self.client.get(url, timeout=30)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TelegramError(f"Не удалось скачать файл ({type(exc).__name__})") from None
        return response.content
```

<details><summary>Вопрос: почему from None, а не from exc, как в CheckReceipt?</summary>

`from exc` сохраняет исходное исключение внутри нового, и при печати трейсбека Python покажет оба: «The above exception was the direct cause of...». А в тексте исходного исключения `httpx` может быть **адрес с токеном** (раздел 6). `from None` обрезает эту цепочку: в логе останется только наш `TelegramError`, где есть имя метода и тип ошибки, но нет адреса.

В `CheckReceipt` токен передаётся в теле запроса, а не в адресе, поэтому там `from exc` безопасен.
</details>

<details><summary>Вопрос: почему в call нет raise_for_status(), а в download_file есть?</summary>

Методы Bot API при ошибке отвечают HTTP 400/401/403/409, но **тело** у них всё равно JSON с `description` (5.8, пункт 4). Если вызвать `raise_for_status()`, мы потеряем это описание и увидим только «400 Bad Request». Поэтому смотрим на `ok`.

Скачивание файла — это не метод Bot API, а просто выдача файла. Там JSON нет, и единственный признак ошибки — HTTP-код.
</details>

<details><summary>Вопрос: что такое allowed_updates и reply_parameters?</summary>

- `allowed_updates: ["message"]` — просьба присылать только новые сообщения, без правок, реакций и прочего. Меньше лишних update. Telegram запоминает эту настройку для бота.
- `reply_parameters: {"message_id": 5}` — ответить «цитатой» на сообщение номер 5. Если человек отправил три фото подряд, по цитате видно, к какому из них относится «Чек сохранён».
</details>

<details><summary>Вопрос: почему httpx.AsyncClient передаётся снаружи?</summary>

Та же мысль, что с клиентом OpenAI: бот делает запрос каждые 30 секунд круглые сутки, и открывать новое соединение каждый раз незачем. Один клиент на всю программу создаётся в `main.py`, а `TelegramApi` и `ReceiptApi` им пользуются. Бонус: в тестах можно подсунуть клиент с `MockTransport`.
</details>

### Шаг 4. QR-код — `bot/qr.py`

То, что ты делал в 5.6, только в виде двух функций:

```python
import io
from urllib.parse import parse_qs

import zxingcpp
from PIL import Image, UnidentifiedImageError

RECEIPT_KEYS = {"t", "s", "fn", "i", "fp", "n"}


def read_qr_codes(image_bytes: bytes) -> list[str]:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("L")
    except (UnidentifiedImageError, OSError):
        return []
    barcodes = zxingcpp.read_barcodes(image, formats=zxingcpp.BarcodeFormat.QRCode)
    return [barcode.text for barcode in barcodes]


def is_receipt(text: str) -> bool:
    return RECEIPT_KEYS <= parse_qs(text.strip()).keys()
```

Проверь в песочнице:

```bash
python -c "from pathlib import Path; from bot.qr import read_qr_codes, is_receipt; codes = read_qr_codes(Path('sandbox/receipt_qr.png').read_bytes()); print(codes, [is_receipt(c) for c in codes])"
```

<details><summary>Вопрос: что значит RECEIPT_KEYS <= ...keys()?</summary>

Для множеств `<=` означает «является подмножеством»: все шесть ключей чека есть среди ключей строки. Лишние ключи не мешают. Это короче, чем шесть проверок `"t" in params and "s" in params and ...`.
</details>

<details><summary>Вопрос: зачем ловить UnidentifiedImageError?</summary>

Человек может отправить файлом что угодно с `mime_type: image/...`: битый файл, HEIC с айфона (Pillow его без дополнительного плагина не открывает). Без `except` бот упал бы на этом сообщении. С ним функция просто вернёт `[]`, и бот ответит «не нашёл QR-код».
</details>

<details><summary>Вопрос: зачем formats=QRCode?</summary>

По умолчанию `zxing-cpp` ищет все виды кодов: и QR, и обычные штрихкоды. Иногда в кадр попадает штрихкод товара. Ограничение по формату работает быстрее и не возвращает лишнего.
</details>

### Шаг 5. Клиент нашего API — `bot/receipt_api.py`

Устройство то же, что у `CheckReceipt` в API: свои ошибки и один метод.

```python
import httpx


class ReceiptApiError(Exception):
    """Базовая ошибка API чеков. Текст можно показать пользователю."""


class ApiUnavailableError(ReceiptApiError):
    pass


class ReceiptDuplicateError(ReceiptApiError):
    pass


class ReceiptRejectedError(ReceiptApiError):
    pass


class ReceiptApi:
    def __init__(self, url: str, timeout: int, client: httpx.AsyncClient) -> None:
        self.url = url
        self.timeout = timeout
        self.client = client

    async def create_receipt(self, raw_receipt: str) -> int:
        try:
            response = await self.client.post(
                f"{self.url}/create_receipt",
                json={"raw_receipt": raw_receipt},
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"API недоступно ({type(exc).__name__})") from exc

        if response.status_code == 201:
            return response.json()["id"]
        if response.status_code == 409:
            raise ReceiptDuplicateError("Этот чек уже добавлен")

        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = response.text
        raise ReceiptRejectedError(f"API ответило {response.status_code}: {detail}")
```

<details><summary>Вопрос: откуда бот знает, что значат 201, 409, 400 и 502?</summary>

Из твоего же кода: открой `app/api/receipt.py`. `201` и `{"id": ...}` — это `status_code=201` и `ReceiptCreated`. `409` — «Этот чек уже добавлен». `400` — чек не найден в сервисе проверки. `502` — сервис проверки недоступен. Все ошибки FastAPI отдаёт как `{"detail": "..."}`. Клиент API всегда пишется по контракту сервера, а самый точный контракт — это `/docs` или код эндпоинта.
</details>

<details><summary>Вопрос: зачем try вокруг response.json() для ошибок?</summary>

Если в API случится необработанное исключение, uvicorn ответит `500` с телом `Internal Server Error` обычным текстом, не JSON. `response.json()` на таком теле бросит `ValueError`. Бот не должен падать от того, что упал API.
</details>

<details><summary>Вопрос: почему 409 — отдельное исключение?</summary>

Потому что для человека это не ошибка, а нормальная ситуация: «уже добавлен, всё хорошо». Бот ответит на него спокойно, без слов «не получилось». Отдельный класс позволяет поймать его отдельным `except`.
</details>

### Шаг 6. Что делать с сообщением — `bot/handlers.py`

Здесь вся логика бота: кто написал, что прислал, что ответить.

```python
import logging

from bot.qr import is_receipt, read_qr_codes
from bot.receipt_api import ReceiptApi, ReceiptApiError, ReceiptDuplicateError
from bot.telegram_api import TelegramApi

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Пришли фото QR-кода с чека, и я добавлю чек в базу.\n"
    "Если фото не читается, пришли картинку файлом (без сжатия) "
    "или текст из QR-кода: t=...&s=...&fn=...&i=...&fp=...&n=..."
)


def get_image_file_id(message: dict) -> str | None:
    if "photo" in message:
        return message["photo"][-1]["file_id"]
    document = message.get("document")
    if document and document.get("mime_type", "").startswith("image/"):
        return document["file_id"]
    return None


async def find_raw_receipt(message: dict, tg: TelegramApi) -> str | None:
    text = message.get("text")
    if text and is_receipt(text):
        return text.strip()

    file_id = get_image_file_id(message)
    if file_id is None:
        return None
    image_bytes = await tg.download_file(file_id)
    for code in read_qr_codes(image_bytes):
        if is_receipt(code):
            return code
    return None


async def handle_message(message: dict, tg: TelegramApi, api: ReceiptApi, allowed_user_ids: list[int]) -> None:
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    user_id = message.get("from", {}).get("id")

    if user_id not in allowed_user_ids:
        await tg.send_message(chat_id, f"Нет доступа. Твой Telegram id: {user_id}")
        return

    if message.get("text") in ("/start", "/help"):
        await tg.send_message(chat_id, HELP_TEXT)
        return

    await tg.send_chat_action(chat_id)
    raw_receipt = await find_raw_receipt(message, tg)
    if raw_receipt is None:
        await tg.send_message(chat_id, "Не нашёл QR-код чека. " + HELP_TEXT, reply_to=message_id)
        return

    try:
        receipt_id = await api.create_receipt(raw_receipt)
    except ReceiptDuplicateError:
        await tg.send_message(chat_id, "Этот чек уже есть в базе.", reply_to=message_id)
        return
    except ReceiptApiError as exc:
        logger.warning("Чек не добавлен: %s", exc)
        await tg.send_message(chat_id, f"Не получилось добавить чек. {exc}", reply_to=message_id)
        return

    await tg.send_message(chat_id, f"Чек сохранён, id {receipt_id}.", reply_to=message_id)
```

<details><summary>Вопрос: почему проверка доступа идёт самой первой?</summary>

Чтобы чужое сообщение не стоило тебе ничего: ни скачивания файла, ни распознавания, ни запроса в API (а значит, ни запроса в платный сервис проверки чеков и в OpenAI). Дешёвые проверки — раньше дорогих.
</details>

<details><summary>Вопрос: зачем send_chat_action?</summary>

`sendChatAction` с `typing` показывает в Telegram «печатает...» на 5 секунд. Распознавание и `create_receipt` могут занять десятки секунд, и без этого человеку кажется, что бот завис. Это не обязательно, но так бот ощущается живым.
</details>

<details><summary>Вопрос: почему ReceiptDuplicateError ловится раньше ReceiptApiError?</summary>

`except` проверяются сверху вниз, и срабатывает первый подходящий. `ReceiptDuplicateError` — наследник `ReceiptApiError`. Если поставить `except ReceiptApiError` первым, он поймает и дубль, и до второго `except` дело не дойдёт.
</details>

<details><summary>Вопрос: почему здесь не ловится TelegramError?</summary>

Если Telegram не дал скачать файл или не принял `sendMessage`, ответить человеку мы всё равно не сможем: ответ идёт через тот же Telegram. Такую ошибку разумно поймать уровнем выше, в цикле `main.py`, записать в лог и перейти к следующему сообщению.
</details>

### Шаг 7. Цикл — `bot/main.py`

```python
import asyncio
import logging

import httpx

from bot.config import get_settings
from bot.handlers import handle_message
from bot.receipt_api import ReceiptApi
from bot.telegram_api import TelegramApi, TelegramError

logger = logging.getLogger("bot")


async def run() -> None:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        tg = TelegramApi(
            token=settings.telegram_settings.token,
            base_url=settings.telegram_settings.base_url,
            client=client,
        )
        api = ReceiptApi(
            url=settings.receipt_api_settings.url,
            timeout=settings.receipt_api_settings.timeout,
            client=client,
        )

        me = await tg.call("getMe")
        logger.info("Бот @%s запущен, API: %s", me["username"], settings.receipt_api_settings.url)

        offset = 0
        while True:
            try:
                updates = await tg.get_updates(offset, settings.telegram_settings.poll_timeout)
            except TelegramError as exc:
                logger.warning("%s. Повтор через 5 секунд", exc)
                await asyncio.sleep(5)
                continue

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message")
                if message is None:
                    continue
                try:
                    await handle_message(message, tg, api, settings.telegram_settings.allowed_user_ids)
                except Exception:
                    logger.exception("Не обработан update %s", update["update_id"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")


if __name__ == "__main__":
    main()
```

**Запусти локально.** Подними API и базу (`docker compose up -d`), остановись (если ещё запущен) `sandbox/tg_try.py`, затем:

```bash
python -m bot.main
```

В терминале: `INFO bot: Бот @fastapi_train_receipts_bot запущен, API: http://127.0.0.1:8000`. Отправь боту фото QR-кода с чека.

<details><summary>Что должно произойти</summary>

1. В Telegram «печатает...», потом ответ цитатой: «Чек сохранён, id 42.»
2. То же фото ещё раз: «Этот чек уже есть в базе.»
3. Фото кошки: «Не нашёл QR-код чека...»
4. Напиши боту с другого аккаунта (попроси кого-нибудь): «Нет доступа. Твой Telegram id: ...».

Если вместо этого в логе `Не получилось добавить чек. API недоступно (ConnectError)`, проверь, что API отвечает на `http://127.0.0.1:8000/docs`.
</details>

<details><summary>Вопрос: почему getMe не в try, а getUpdates — в try?</summary>

`getMe` вызывается один раз при старте. Если он не прошёл (неверный токен, нет сети), продолжать бессмысленно: лучше упасть сразу с понятной ошибкой `TelegramError: getMe: 401 Unauthorized`, чем крутиться в цикле повторов. Это принцип «падай рано».

`getUpdates` вызывается вечно. Сеть пропадёт на минуту, Telegram ответит `502` — это не повод останавливать бота. Пауза 5 секунд и новая попытка. Пауза нужна, чтобы при длинном сбое не отправлять сотни запросов в секунду.
</details>

<details><summary>Вопрос: зачем except Exception вокруг handle_message? Разве ловить всё подряд не плохо?</summary>

Обычно плохо: так прячутся ошибки. Но здесь это граница: одно сообщение не должно ронять бота для всех остальных. Мы не прячем ошибку, а пишем её в лог с трейсбеком (`logger.exception`) и идём дальше. Ровно так же FastAPI поступает с запросом: исключение в эндпоинте превращается в `500`, а сервер продолжает работать.
</details>

<details><summary>Вопрос: зачем logging, если можно print?</summary>

`logging` пишет время, уровень и источник каждой строки, и уровень можно настроить отдельно для каждой библиотеки (как мы сделали с `httpx`). А ещё `print` в Docker без дополнительной настройки буферизуется, и строки появляются в `docker compose logs` с опозданием или пачкой. `logging` пишет в stderr, а он не буферизуется.
</details>

### Шаг 8. Образ — `bot/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /my_code
COPY bot/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/

CMD ["python", "-m", "bot.main"]
```

<details><summary>Вопрос: почему COPY bot/... с префиксом, если Dockerfile лежит в bot/?</summary>

Пути в `COPY` считаются от **контекста сборки**, а не от места, где лежит Dockerfile. Контекстом мы сделаем корень репозитория (шаг 9), чтобы в образе получилась папка `/my_code/bot` и работал `python -m bot.main`, ровно как с `app` у API.
</details>

<details><summary>Вопрос: почему requirements копируется и ставится до COPY bot/?</summary>

Кэш слоёв из [урока по Docker](docker-for-beginners.md): если поменялся только код, Docker возьмёт готовый слой с установленными библиотеками и пересоберёт только последний `COPY`. Сравни с `Dockerfile` API: там код копируется **до** `pip install`, и любая правка в `app/` заново ставит все библиотеки. Можешь заодно поправить и его.
</details>

### Шаг 9. Сервис — `compose.yaml`

Добавь в `services` рядом с `api`:

```yaml
  bot:
    build:
      context: .
      dockerfile: bot/Dockerfile
    environment:
      TELEGRAM_SETTINGS__TOKEN: ${TELEGRAM_SETTINGS__TOKEN:?добавь TELEGRAM_SETTINGS__TOKEN в .env}
      TELEGRAM_SETTINGS__ALLOWED_USER_IDS: ${TELEGRAM_SETTINGS__ALLOWED_USER_IDS:-[]}
      RECEIPT_API_SETTINGS__URL: http://api:8000
    volumes:
      - ./bot:/my_code/bot
    depends_on:
      - api
    stop_signal: SIGINT
    restart: unless-stopped
```

Проверь конфигурацию без запуска: `docker compose config`. Потом **останови локального бота** (`Ctrl+C`) и запусти контейнер:

```bash
docker compose up -d --build bot
docker compose logs -f bot
```

<details><summary>Вопрос: почему адрес API здесь http://api:8000, а в .env http://127.0.0.1:8000?</summary>

Это главная мысль [урока по Postgres](postgres-docker-for-beginners.md), только для HTTP. `127.0.0.1` внутри контейнера — это сам контейнер `bot`, а API в нём нет. Соседний контейнер доступен по **имени сервиса** в сети Compose: `api`. Порт — `8000`, внутренний порт контейнера, а не тот, что опубликован в `ports`.

В `.env` остаётся `127.0.0.1`: он нужен, когда ты запускаешь бота из PyCharm на своём компьютере. А `environment` в `compose.yaml` важнее значений из `.env`, поэтому в контейнере адрес будет `api:8000`.
</details>

<details><summary>Вопрос: почему environment с ${...}, а не env_file: .env, как у api?</summary>

`env_file: .env` передал бы в контейнер бота **все** переменные из `.env`: пароль базы, токен сервиса проверки чеков, ключ OpenAI. Боту они не нужны. Чем меньше секретов знает сервис, тем меньше утечёт, если с ним что-то случится. Поэтому передаём только то, что нужно, а значения Compose сам подставит из `.env` (так же, как пароль у `pg_database`).

- `${VAR:?текст}` — если переменной нет, `docker compose` откажется запускаться и напечатает этот текст. Без этого бот получил бы пустой токен и падал бы с непонятным `404 Not Found`.
- `${VAR:-[]}` — если переменной нет, подставится `[]` (пустой список: доступа нет ни у кого, но бот запустится и скажет каждому его id).
</details>

<details><summary>Вопрос: почему у bot нет ports?</summary>

Никто не подключается к боту. Бот сам ходит в Telegram и в API. Открывать порт незачем: это лишняя дверь в контейнер.
</details>

<details><summary>Вопрос: зачем stop_signal: SIGINT?</summary>

Проверь сам: убери эту строку, запусти бота и выполни `docker compose stop bot`. Остановка займёт ровно 10 секунд.

Внутри контейнера твоя программа — процесс номер 1. Linux не применяет к процессу номер 1 действия по умолчанию для сигналов: если программа не установила свой обработчик `SIGTERM` (а Python его не ставит), сигнал просто игнорируется. Docker ждёт 10 секунд и убивает процесс через `SIGKILL`. У API такой проблемы нет: uvicorn сам обрабатывает `SIGTERM`.

`SIGINT` — это тот же сигнал, что `Ctrl+C`. Для него Python обработчик ставит всегда: бросает `KeyboardInterrupt`. Он аккуратно закрывает `httpx.AsyncClient`, и в логе появляется «Бот остановлен». Остановка занимает доли секунды.

Другой способ — `init: true`: тогда процессом номер 1 становится маленький `init` от Docker, он передаёт сигнал Python, и Python останавливается сразу (но без нашего «Бот остановлен»).
</details>

<details><summary>Вопрос: зачем volumes, если код и так копируется в образ?</summary>

Для разработки, как у `api`: правишь `bot/handlers.py` в PyCharm, и файл в контейнере меняется сразу. Но у бота нет `--reload`, как у uvicorn, поэтому после правки перезапусти его: `docker compose restart bot`.
</details>

### Шаг 10. Проверка целиком

Отправь боту фото нового чека и посмотри, что легло в базу:

```sql
-- чек
SELECT id, period, retail_place, total_sum, qrraw
FROM payment_statistic.receipt
ORDER BY id DESC
LIMIT 5;

-- его позиции и группы
SELECT c.name, c.sum, g.name AS group_name
FROM payment_statistic.receipt_compound c
JOIN payment_statistic.groups g ON g.id = c.group_id
WHERE c.receipt_id = 42  -- id из ответа бота
ORDER BY c.id;
```

<details><summary>Что проверить</summary>

- `id` в ответе бота совпадает с последним `id` в `receipt`.
- `qrraw` — та же строка, что распознал бот.
- В `logs.api_logs` появилась запись `proverka_cheka_api` (и `openai`, если ключ есть).
- В `docker compose logs bot` нет токена ни в одной строке. Проверь поиском по началу своего токена (число до двоеточия): `docker compose logs bot | grep "123456789:"` в Linux или `docker compose logs bot | Select-String "123456789:"` в PowerShell. Вывод должен быть пустым.
</details>

Не забудь закоммитить: `bot/`, `compose.yaml`, `.env.example`. Перед коммитом посмотри `git status`: `.env` в списке быть не должно.

---

## 8. Одно фото целиком

Пройди путь фотографии вслух, от телефона до базы, и только потом открой ответ.

<details><summary>Путь фото</summary>

1. Телефон отправляет фото в Telegram. Telegram сохраняет его, сжимает в несколько размеров и кладёт update в очередь бота.
2. Бот висит в `getUpdates(offset, timeout=30)`. Telegram сразу отвечает списком из одного update.
3. `offset = update_id + 1` (в Telegram подтверждение уйдёт со следующим `getUpdates`).
4. `handle_message`: `from.id` есть в `allowed_user_ids` → дальше. Не `/start`.
5. `sendChatAction(typing)` → у человека «печатает...».
6. `find_raw_receipt`: текста нет → `get_image_file_id` берёт `photo[-1].file_id`.
7. `download_file`: `getFile` → `file_path` → `GET /file/bot<токен>/photos/file_3.jpg` → байты.
8. `read_qr_codes`: Pillow открывает байты, переводит в серый, `zxing-cpp` находит QR-коды → список строк.
9. `is_receipt` отбирает строку с ключами `t, s, fn, i, fp, n`.
10. `ReceiptApi.create_receipt` → `POST http://api:8000/create_receipt {"raw_receipt": "t=..."}`.
11. API: проверка дубля → сервис проверки чеков → группы (память и OpenAI) → `INSERT` чека и позиций → `COMMIT` → `201 {"id": 42}`.
12. Бот: `sendMessage(chat_id, "Чек сохранён, id 42.", reply_parameters={message_id})`.
13. Цикл: снова `getUpdates` с новым `offset`. Telegram удаляет обработанный update.
</details>

---

## 9. Правила, на которых ошибаются

### Токен в коде, в git или в логах

Токен только в `.env`, а `.env` в `.gitignore`. Логи `httpx` — не ниже `WARNING`. Исключения с адресом — через `from None`. Если токен утёк: `/revoke` в BotFather (раздел 4), удаления коммита недостаточно.

### Забыли двигать offset

Бот отвечает на одно и то же сообщение бесконечно. `offset = update["update_id"] + 1` для **каждого** update, даже того, который бот пропустил (стикер, сообщение от чужого).

### Таймаут HTTP меньше timeout в getUpdates

`ReadTimeout` каждые N секунд тишины. HTTP-таймаут = `timeout` + запас.

### Два бота на одном токене

`409 Conflict: terminated by other getUpdates request`. Бот запущен в Docker **и** в PyCharm (или в песочнице). Остановить один из них.

### localhost внутри контейнера

`API недоступно (ConnectError)` в Docker, хотя локально всё работает. В контейнере адрес API — `http://api:8000`.

### Адрес файла перепутан с адресом метода

Методы: `/bot<токен>/getFile`. Файлы: `/file/bot<токен>/<file_path>`. Скачивание по адресу метода вернёт `404`.

### photo[0] вместо photo[-1]

Первый размер — превью 90 пикселей. QR-код на нём не читается, и бот на каждое фото отвечает «не нашёл QR-код».

### raise_for_status() на методах Bot API

Ты теряешь `description` и видишь только «400 Bad Request» вместо «Bad Request: invalid file_id».

### Нет проверки доступа

Любой, кто нашёл бота поиском, добавляет чеки в твою базу от имени админа и тратит запросы платных сервисов.

### Одно плохое сообщение роняет бота

Без `try/except` вокруг `handle_message` любая неожиданность (битая картинка, `KeyError` в странном update) останавливает цикл, и бот молчит для всех. Не ловить всё — правило для обычного кода; граница цикла — исключение из правила.

### Бот пишет в базу сам

Логика проверки, групп и транзакций дублируется в двух местах и обязательно разъедется. Бот — клиент API.

### Docker останавливает бота 10 секунд

Python — процесс номер 1 и игнорирует `SIGTERM`. `stop_signal: SIGINT` или `init: true`.

---

## 10. Диагностика: сначала найди этап

| Симптом | Где искать | Что проверить |
|---|---|---|
| `docker compose up` пишет `добавь TELEGRAM_SETTINGS__TOKEN в .env` | Шаг 9 | Нет переменной в `.env` или опечатка в имени |
| При старте `TelegramError: getMe: 401 Unauthorized` | Токен | Токен неверный или отозван. Сверь с BotFather |
| При старте `getMe: 404 Not Found` | Токен / адрес | Пустой токен или `base_url` с лишним `/bot` в конце |
| При старте `getMe: нет связи с Telegram (ConnectError)` или `ConnectTimeout` | Сеть | Открывается ли `https://api.telegram.org` в браузере на этом компьютере. В Docker: `docker compose exec bot python -c "import httpx; print(httpx.get('https://api.telegram.org').status_code)"` |
| В логе раз в 5 секунд `getUpdates: 409 Conflict: terminated by other getUpdates request` | Два бота | Где ещё запущен бот с этим токеном: PyCharm, песочница, второй компьютер |
| `getUpdates: 409 Conflict: can't use getUpdates method while webhook is active` | Webhook | Когда-то ставили webhook. Открой в браузере `.../bot<ТОКЕН>/deleteWebhook` |
| Бот молчит, в логе пусто | Где сообщения | Пишешь тому ли боту? `docker compose ps`: бот `Up` или перезапускается? `docker compose logs bot` целиком |
| «Нет доступа. Твой Telegram id: ...» тебе самому | Шаг 2 | Этого id нет в `TELEGRAM_SETTINGS__ALLOWED_USER_IDS`. Формат `[id]`. После правки `.env` — `docker compose up -d bot` (не `restart`: `restart` не перечитывает переменные) |
| `Input should be a valid list` при старте | Шаг 2 | Список id без квадратных скобок |
| «Не нашёл QR-код чека» на нормальном фото | Шаг 4 | Сохрани это фото и прогони `sandbox/qr_try.py`. Если и там 0 кодов — качество фото (5.6). Если код есть, но не чек — смотри, что за строка |
| «Не получилось добавить чек. API недоступно (ConnectError)» | Шаг 9 | В Docker адрес `http://api:8000`, локально `http://127.0.0.1:8000`. API запущен? `docker compose ps` |
| «API недоступно (ReadTimeout)», а потом «Этот чек уже есть» | Шаг 2 | `RECEIPT_API_SETTINGS__TIMEOUT` меньше, чем идёт `create_receipt` |
| «API ответило 400: Чек не найден» | API | Строка распозналась, но сервис проверки чеков её не знает. Чек слишком свежий (сервис узнаёт о чеке не сразу) или с ошибкой в QR |
| «API ответило 502: Сервис проверки чеков недоступен» | API | Проблема не в боте. Смотри `CHECK_RECEIPT_SETTINGS__*` и логи `api` |
| «API ответило 500: Internal Server Error» | API | `docker compose logs api`, ищи трейсбек |
| `Не обработан update ...` с трейсбеком в логе бота | Шаг 6 | Читай трейсбек снизу вверх: какая строка `handlers.py` и какое поле update |
| `docker compose stop` идёт 10 секунд | Шаг 9 | Нет `stop_signal: SIGINT` |
| Правка в `bot/*.py` не действует | Шаг 9 | `docker compose restart bot`. Если менял `requirements.txt` — `docker compose up -d --build bot` |

---

## 11. Тренировка: от простого к переносу навыка

### Уровень 1. С пустого листа

Закрой урок и напиши `sandbox/tg_try.py` из раздела 5.7 по памяти: `getMe`, цикл `getUpdates` с `offset` и `timeout`, эхо через `sendMessage`.

### Уровень 2. Команда /last

Сделай команду `/last`: бот отвечает списком пяти последних чеков (дата, магазин, сумма). Для этого в API нужен новый эндпоинт `GET /receipts?limit=5`, а в `ReceiptApi` — новый метод. Подумай: где форматировать текст для Telegram, в API или в боте?

<details><summary>Подсказка</summary>

API отдаёт данные (JSON со списком чеков), бот решает, как их показать человеку. Если завтра появится фронтенд на Nuxt, он возьмёт тот же JSON и покажет его таблицей. Текст «для Telegram» в API — это смешивание слоёв.
</details>

### Уровень 3. Свой пользователь вместо админа

Сейчас все чеки пишутся от имени `ADMIN_USER_ID`. Добавь в `payment_statistic.users` колонку `telegram_id BIGINT UNIQUE`, в `POST /create_receipt` — необязательное поле `telegram_id`, и пусть API сам находит пользователя по нему. Бот передаёт `message["from"]["id"]`. Тогда `allowed_user_ids` можно заменить проверкой «есть ли такой пользователь в базе».

<details><summary>Вопрос, над которым стоит подумать</summary>

Если API доверяет полю `telegram_id` из тела запроса, то любой, кто может достучаться до API, напишет чек от чужого имени. Пока API открыт только на `127.0.0.1` и внутри Compose, это терпимо. Но перед тем как открывать API наружу, понадобится авторизация. Это тема отдельного урока.
</details>

### Уровень 4. Сломай специально

По очереди: неверный токен в `.env`, пустой `ALLOWED_USER_IDS`, остановленный `api` (`docker compose stop api`), бот в Docker и одновременно в PyCharm, фото без QR-кода, PDF-файл, текст «t=1&s=2». Для каждого случая предскажи, что ответит бот и что будет в логах, потом проверь.

### Уровень 5. Тест без интернета и без Telegram

`TelegramApi` и `ReceiptApi` получают `httpx.AsyncClient` снаружи. Подставь `httpx.AsyncClient(transport=httpx.MockTransport(handler))`, где `handler` по `request.url.path` решает, что ответить, и проверь `handle_message`:

- сообщение от чужого id → один `sendMessage` с текстом «Нет доступа»;
- фото с QR-кодом чека (картинка из `sandbox/receipt_qr.png`) → `POST /create_receipt` с правильной строкой;
- API ответил `409` → «Этот чек уже есть в базе».

<details><summary>Подсказка: скелет handler</summary>

```python
sent = []

def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/getFile"):
        return httpx.Response(200, json={"ok": True, "result": {"file_path": "photos/1.jpg"}})
    if path.endswith("/photos/1.jpg"):
        return httpx.Response(200, content=Path("sandbox/receipt_qr.png").read_bytes())
    if path.endswith("/sendMessage") or path.endswith("/sendChatAction"):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {}})
    if path == "/create_receipt":
        return httpx.Response(201, json={"id": 1})
    return httpx.Response(404)
```

`message` для теста собери руками по образцу из 5.5: `{"message_id": 1, "from": {"id": 111}, "chat": {"id": 111}, "photo": [{"file_id": "x"}]}`.

Положи тест в `sandbox/bot_test.py` и запускай из корня репозитория как модуль: `python -m sandbox.bot_test`. Если запустить `python sandbox/bot_test.py`, Python не найдёт пакет `bot`: он ищет импорты рядом со скриптом, а не в текущей папке.
</details>

### Уровень 6. Не ждать API последовательно

Сейчас, пока `create_receipt` идёт 30 секунд, бот не читает новые сообщения: цикл стоит на `await`. Сделай так, чтобы каждое сообщение обрабатывалось в своей задаче (`asyncio.create_task`). Подумай: что будет с задачами при остановке бота? Что будет, если одна задача упадёт? Как ограничить число одновременных запросов к API (`asyncio.Semaphore`)?

### Уровень 7. Webhook вместо polling

Прочитай в документации Bot API про `setWebhook`. Ответь письменно: что нужно, чтобы Telegram мог достучаться до бота (адрес, порт, сертификат)? Почему для бота на домашнем компьютере это сложнее, чем long polling? Как бот на webhook узнаёт, что запрос пришёл именно от Telegram (`secret_token`)?

### Уровень 8. Бот ждёт готовности API

Сейчас `depends_on: [api]` ждёт только **запуска** контейнера `api`, а не того, что API готов отвечать. Добавь в `api` `healthcheck` (запрос к `/docs` через `python -c "import urllib.request; ..."`, в образе нет `curl`), а у бота — `depends_on` с `condition: service_healthy`, как у `api` для базы.

---

## 12. Закрепление по памяти

Через день, не открывая урок, ответь письменно:

1. Шесть вопросов из раздела 3 и ответы на них для нашего проекта.
2. Как выглядит адрес метода Bot API и адрес скачивания файла? Чем отличаются?
3. Что такое `offset` и что будет, если его не двигать? Если подтвердить update до обработки и упасть?
4. Почему HTTP-таймаут для `getUpdates` больше параметра `timeout`?
5. Почему адрес API в Docker — `http://api:8000`, а с компьютера — `http://127.0.0.1:8000`?
6. Почему бот ходит в API, а не в базу?
7. Где токен может утечь в логи и как это закрыто?
8. Почему контейнер с Python останавливается 10 секунд и как это исправить?

### Самопроверка

- [ ] Могу без библиотек получить сообщения бота и ответить на них.
- [ ] Могу скачать присланную картинку в два шага.
- [ ] Могу вытащить строку QR-кода из картинки и отличить чек от рекламы.
- [ ] Бот отвечает чужим «Нет доступа» и не тратит на них запросы.
- [ ] На каждую ошибку API бот отвечает понятной фразой и продолжает работать.
- [ ] Токена нет в коде, в git, в логах и в `repr` настроек.
- [ ] Бот работает в Docker и останавливается мгновенно.

### Что дальше

- Кнопки (`reply_markup` с `inline_keyboard`) и `callback_query`: например, «Поменять группу» под каждой позицией чека.
- Авторизация в API и свой пользователь для каждого Telegram-id.
- Тесты на `pytest` с `MockTransport` для бота, сервиса проверки чеков и OpenAI.

---

## 13. Шпаргалка — открывать только после попыток

```text
bot/
├── __init__.py
├── requirements.txt     httpx, pydantic-settings, pillow, zxing-cpp
├── Dockerfile           python:3.12-slim, requirements → код, python -m bot.main
├── config.py            TelegramSettings, ReceiptApiSettings, BotSettings, get_settings
├── telegram_api.py      TelegramError, TelegramApi.call / get_updates / send_message / send_chat_action / download_file
├── qr.py                read_qr_codes, is_receipt
├── receipt_api.py       ReceiptApiError (+ ApiUnavailable, Duplicate, Rejected), ReceiptApi.create_receipt
├── handlers.py          get_image_file_id, find_raw_receipt, handle_message
└── main.py              run (getMe, цикл getUpdates), main (logging, KeyboardInterrupt)
compose.yaml             + сервис bot: build context ., environment ${...}, RECEIPT_API_SETTINGS__URL=http://api:8000, stop_signal SIGINT
.env / .env.example      + TELEGRAM_SETTINGS__TOKEN, TELEGRAM_SETTINGS__ALLOWED_USER_IDS=[id], RECEIPT_API_SETTINGS__URL
```

**Адреса Bot API:**

```text
https://api.telegram.org/bot<ТОКЕН>/<метод>            методы, ответ {"ok": ..., "result" | "error_code" + "description"}
https://api.telegram.org/file/bot<ТОКЕН>/<file_path>   скачивание файла, ответ — сами байты
```

**Методы, которые использует бот:**

| Метод | Параметры | Что возвращает |
|---|---|---|
| `getMe` | — | Информация о боте (`username`) |
| `getUpdates` | `offset`, `timeout`, `allowed_updates` | Список update |
| `sendMessage` | `chat_id`, `text`, `reply_parameters` | Отправленное сообщение |
| `sendChatAction` | `chat_id`, `action` (`typing`) | `true` |
| `getFile` | `file_id` | Объект с `file_path` |
| `deleteWebhook` | — | `true`. Нужен, если когда-то ставили webhook |

**Где что лежит в update:**

```text
update["update_id"]                       → offset = update_id + 1
update["message"]["from"]["id"]           → кто написал (проверка доступа)
update["message"]["chat"]["id"]           → куда отвечать
update["message"]["message_id"]           → на что отвечать цитатой
update["message"]["text"]                 → текст (у фото его нет)
update["message"]["photo"][-1]["file_id"] → самый большой размер фото
update["message"]["document"]["mime_type"], ["file_id"] → картинка файлом
```

**Частые ошибки Bot API:**

| Ответ | Когда |
|---|---|
| `401 Unauthorized` | Неверный или отозванный токен |
| `404 Not Found` | Неправильный адрес: нет `bot` перед токеном, пустой токен, опечатка в методе |
| `400 Bad Request: chat not found` | Неверный `chat_id` или человек ещё не начинал диалог с ботом |
| `400 Bad Request: invalid file_id` | Опечатка в `file_id` или чужой `file_id` (от другого бота) |
| `403 Forbidden: bot was blocked by the user` | Человек заблокировал бота |
| `409 Conflict: terminated by other getUpdates request` | Два процесса с одним токеном |
| `409 Conflict: can't use getUpdates method while webhook is active` | Нужен `deleteWebhook` |
| `429 Too Many Requests: retry after N` | Слишком часто отправляешь сообщения, подожди N секунд |

**Распознать QR-код:**

```python
image = Image.open(io.BytesIO(image_bytes)).convert("L")
texts = [b.text for b in zxingcpp.read_barcodes(image, formats=zxingcpp.BarcodeFormat.QRCode)]
is_receipt = {"t", "s", "fn", "i", "fp", "n"} <= parse_qs(text).keys()
```

### Где искать синтаксис

- Документация Bot API: core.telegram.org/bots/api — все методы, все поля update, раздел «Making requests» и «Getting updates».
- [Урок по Docker](docker-for-beginners.md): контекст сборки, кэш слоёв, `docker compose logs`.
- [Урок по Postgres](postgres-docker-for-beginners.md): адреса внутри сети Compose, `depends_on` с `healthcheck`.
- [Урок по OpenAI](openai-categorizer-for-beginners.md): свой клиент внешнего сервиса, свои исключения, `MockTransport`.
