# Discord bot

## Описание функционала бота
- Из каждого токена из `discord.txt` создаётся отдельный бот.
- При наличии файла `proxy.txt` бот может работать через заданный прокси (если прокси нет, то бот напишет, какой токен запущен без прокси).
- Учитывает предыдущую историю диалога, загружая уже сохранённые сообщения и ответы из соответствующего JSON-файла.
- При поступлении нового сообщения формируется запрос к OpenAI: системный `prompt` (из `config.promt`) плюс вся история общения с конкретным пользователем на данном сервере.
- Ответ дополняет историю, чтобы учесть контекст в дальнейшем.
- При запуске скрипт ждёт случайное время (10–60 сек), чтобы не активировать всех ботов мгновенно и избежать подозрительной активности.
- Игнорирует собственные сообщения и каналы, не входящие в `allowed_channels`.
- Если бота упомянули (@бот), он генерирует ответ, имитирует время «печати» (задержка на длину ответа) и отправляет сообщение методом `reply`.
- Периодически просматривает случайно выбранные разрешённые каналы, выбирает из последних 20 сообщений одно случайное и отвечает на него реплаем либо обычным сообщением (случайный выбор).
- После успешной отправки ставит «cooldown» на канал (переменная `default_sleep`), чтобы не спамить.
- При отправке ответа бот делает имитацию печати, пропорциональную длине текста.

## Хранение и контроль сообщений
- История переписки записывается в виде JSON: для каждого пользователя на каждом сервере создаётся свой файл.
- Файл `processed_messages.txt` содержит ID сообщений, на которые бот уже ответил, чтобы избежать дублирующихся реакций.
- При удачной отправке ответ добавляется в историю, и ID сообщения вносится в список обработанных.

## Логирование и цветной вывод в консоль
- Бот детально логирует все действия: какой канал, кто написал, какой ответ сгенерирован, сколько секунд бот «отдыхает» и т.д.
- Используется библиотека `colorama` для наглядного цветового форматирования сообщений в терминале.

## Итог
Каждый экземпляр бота работает как selfbot, обращается к GPT с учётом всей предыдущей истории диалога, отвечает на упоминания и случайные сообщения, соблюдая ограничения (cooldown, таймеры), а также хранит всю переписку и статус обработки, сохраняя независимость от других экземпляров.

## Для запуска
- `discord.txt` - одна строка — один токен (без кавычек и запятых).
- `proxy.txt` - одна строка — один прокси (`ip:port:login:password`). Берём тут: [https://proxyshard.com?ref=44](https://proxyshard.com?ref=44) (спасибо @capitanike).
- Выполните команду: `pip install -r requirements.txt`
- Затем запустите: `python3 main.py`

## Переменные
- `allowed_channels` - ID нужных каналов через запятую.
- `default_sleep` - таймаут для каждого канала.
- `gpt_model` - модель GPT (по умолчанию «gpt-4o-mini»).
- `openai_api` - ключ API (берём тут: [https://platform.openai.com/settings/organization/api-keys](https://platform.openai.com/settings/organization/api-keys)).
- `prompt` - Ваш промпт для общения.
