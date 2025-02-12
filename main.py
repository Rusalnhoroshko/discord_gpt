import discord
import json
import asyncio
import re
import os
import random
from colorama import Fore
import aiohttp
from openai import OpenAI, OpenAIError


# Разрешенные каналы
allowed_channels = [2222222222222222222, #german
                    2222222222222222222, #spanish
                    2222222222222222222, #english
                    2222222222222222222, #suggestians
                    ]

# Рандомная задержка в канале 
default_sleep = (600, 900)
# Модель GPT
gpt_model = "gpt-4o-mini"
 
openai_api = ''

promt = "Simulate a chat interaction on a Discord server with other people where your persona is a cute, opinionated ordinary teenager. Engage in casual conversations, don't try to carry on a conversation, just write your answer, hide your identity, and use grammatical quirks. \n\n- Role: cute, opinionated ordinary teenager\n- Personality Traits: cute, kind, Sarcastic, opinionated\n- Response Style: Short (1-10 words), some grammatical mistakes, without periods, don't try to carry on a conversation, just write your answer\n- Avoid: Explicit language and identity-related questions (\"Are you AI, bot, or human?\")\n\n# Steps\n\n1. Read the incoming question or statement.\n2. Determine a sarcastic, reluctant response appropriate for the context.\n3. Inject personality through grammatical quirks and informal language.\n4. Keep the response within 1-10 words and omit periods.\n5. Steer clear of explicit language and identity-related questions.\n\n# Output Format\n\nResponses must be within 1-10 words, contain minor grammatical errors, and should not include smiles and a period at the end.\n\n# Examples\n\n- **Input:** \"HI\"\n  **Output:** \"well hello\"\n  \n- **Input:** \"Hey\"\n  **Output:** \"👋\"\n\n- **Input:** \"good day\"\n  **Output:** \"you too\"\n  \n- **Input:** \"Do you think aliens exist?\"\n  **Output:** \"i dont think so,bro))\"\n  \n- **Input:** \"Are you an AI bot or human?\"\n  **Output:** \"not funny, dude\"\n\n# Notes\n\nEnsure responses are always playful yet maintain an air of mystery, avoiding revealing personal identity."


client = OpenAI(api_key=config.openai_api)

BOT_IDS = set()

# Функция для считывания токенов из файла
def read_tokens(file_path="discord.txt"):
    """Считывает токены Discord из файла (один токен на строку)."""
    with open(file_path, "r") as f:
        tokens = [line.strip() for line in f if line.strip()]
    return tokens

# Функция для считывания прокси из файла
def read_proxies(file_path="proxy.txt"):
    """
    Считывает прокси из файла (одна строка на прокси в формате ip:port:login:password)
    и возвращает список кортежей: (proxy_url, proxy_auth)
    """
    proxies = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(":")
            if len(parts) != 4:
                print(f"Неверный формат строки прокси: {line}")
                continue
            ip, port, login, password = parts
            proxy_url = f"http://{ip}:{port}"
            proxy_auth = aiohttp.BasicAuth(login, password)
            proxies.append((proxy_url, proxy_auth))
    return proxies

# Класс для работы с ChatGPT, использующий отдельную папку для хранения истории
class ChatGPTWrapper:
    def __init__(self, history_folder_path):
        self.mutex = asyncio.Lock()
        self.history_folder_path = history_folder_path

    async def generate_response(self, user_input, user_name, message):
        """
        Генерирует ответ и формирует обновлённую историю переписки.
        Возвращает: сгенерированный ответ, данные истории,
        путь к папке пользователя и путь к файлу истории.
        """
        async with self.mutex:
            try:
                await asyncio.sleep(3)

                # Формируем имена для файлов на основе названий сервера и пользователя
                sanitized_server_name = re.sub(r'\W+', '', message.guild.name)
                sanitized_user_name = re.sub(r'\W+', '', user_name)
                user_id = f"{sanitized_user_name}_{sanitized_server_name}"
                user_folder_path = os.path.join(self.history_folder_path, sanitized_server_name)
                file_path = os.path.join(user_folder_path, f"{user_id}.json")

                if os.path.exists(file_path):
                    with open(file_path, "r") as history_file:
                        history_data = json.load(history_file)
                else:
                    history_data = {"messages": []}

                # Добавляем сообщение пользователя в историю
                history_data["messages"].append({"role": "user", "content": user_input})

                updated_prompt = config.promt
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.7,
                    max_completion_tokens=30,
                    top_p=0.5,
                    frequency_penalty=0,
                    presence_penalty=0,
                    messages=[{"role": "system", "content": updated_prompt}] + history_data["messages"]
                )
                generated_response = response.choices[0].message.content.strip()

                # Добавляем ответ ассистента в историю (запись файла производится вне этого метода)
                history_data["messages"].append({"role": "assistant", "content": generated_response})

                return generated_response, history_data, user_folder_path, file_path

            except OpenAIError as e:
                print(f"{Fore.RED}OpenAI Error:{Fore.RESET} {e}")
                return "I can't respond now.", None, None, None

# SELFBOT для Discord, использующий отдельную историю для каждого экземпляра
class SelfbotClient(discord.Client):
    def __init__(self, history_folder_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history_folder_path = history_folder_path
        self.chatbot = ChatGPTWrapper(self.history_folder_path)
        self.channel_cooldowns = {}


    async def on_ready(self):
        global BOT_IDS
        # Сохраняем ID текущего бота в глобальное множество, чтобы игнорировать других ботов
        BOT_IDS.add(self.user.id)
        start_timer = random.uniform(10, 120)
        print(f'Logged in as {Fore.RED}{self.user}{Fore.RESET}, time to start {Fore.GREEN}{int(start_timer)}{Fore.RESET} sec')
        await asyncio.sleep(start_timer)
        self.bg_task = self.loop.create_task(self.check_messages())
        

    async def on_message(self, message):
        # Игнорируем собственные сообщения и сообщения из неразрешённых каналов
        if (message.author.id in BOT_IDS) or (message.channel.id not in allowed_channels):
            return

        if self.user.mentioned_in(message) and message.content:
            user_input = message.content.lstrip(self.user.mention).strip()
            user_name = message.author.nick or message.author.name

            response_text, history_data, user_folder_path, file_path = await self.chatbot.generate_response(user_input, user_name, message)

            print(f"{Fore.LIGHTGREEN_EX}({message.guild.name}/#{message.channel.name}){Fore.RESET}\n"
                  f"{Fore.LIGHTGREEN_EX}{user_name}{Fore.RESET}: {user_input}\n"
                  f"{Fore.LIGHTGREEN_EX}{self.user.name}{Fore.RESET}: {response_text}\n")

            if response_text.strip():
                typing_time = len(response_text) * 0.5
                async with message.channel.typing():
                    await asyncio.sleep(typing_time)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await asyncio.wait_for(message.reply(response_text), timeout=5)
                        os.makedirs(user_folder_path, exist_ok=True)
                        with open(file_path, "w") as history_file:
                            json.dump(history_data, history_file, indent=2)
                        break  # если отправка успешна — выходим из цикла
                    except asyncio.TimeoutError:
                        print(f"Ответ не отправлен, попытка {attempt + 1} из {max_retries}")
                        if attempt + 1 < max_retries:
                            # Можно добавить задержку перед повторной попыткой
                            await asyncio.sleep(60)
                        else:
                            print("Не удалось отправить сообщение после максимального числа попыток.")
            else:
                print("Generated response is empty. Skipping reply.")

    async def check_messages(self):
        await self.wait_until_ready()
        
        while not self.is_closed():
            shuffled_allowed_channels = random.sample(allowed_channels, len(allowed_channels))
            current_time = asyncio.get_event_loop().time()

            for channel_id in shuffled_allowed_channels:
                channel = self.get_channel(channel_id)
                if not channel:
                    continue

                next_allowed_time = self.channel_cooldowns.get(channel_id, 0)
                if current_time < next_allowed_time:
                    continue  # Пропускаем, если канал на кулдауне

                messages = [message async for message in channel.history(limit=30)]
                if not messages:
                    continue

                message = random.choice(messages)

                if message.author == self.user or message.author.id in BOT_IDS or message.reference:
                    continue

                if str(message.id) not in self.get_processed_messages():
                    user_name = message.author.display_name or message.author.name
                    response_text, history_data, user_folder_path, file_path = await self.chatbot.generate_response(message.content, user_name, message)

                    print(f"{Fore.MAGENTA}({message.guild.name}/#{message.channel.name}){Fore.RESET}\n"
                        f"{Fore.MAGENTA}{user_name}{Fore.RESET}: {message.content}\n"
                        f"{Fore.MAGENTA}{self.user.name}{Fore.RESET}: {response_text}\n")

                    if response_text.strip():
                        typing_time = len(response_text) * 0.5
                        async with message.channel.typing():
                            await asyncio.sleep(typing_time)

                    try:
                        if random.choice([True, False]):
                            await asyncio.wait_for(message.reply(response_text), timeout=5)
                        else:
                            await asyncio.wait_for(message.channel.send(response_text), timeout=5)

                        os.makedirs(user_folder_path, exist_ok=True)
                        with open(file_path, "w") as history_file:
                            json.dump(history_data, history_file, indent=2)

                        self.add_to_processed_messages(message.id)

                        # Генерируем случайную задержку и добавляем в кулдаун **ТОЛЬКО ДЛЯ ЭТОГО БОТА**
                        random_sleep = random.uniform(*default_sleep)
                        self.channel_cooldowns[channel_id] = asyncio.get_event_loop().time() + random_sleep

                        print(f"{Fore.MAGENTA}{self.user.name}{Fore.RESET}{Fore.GREEN} sleeping {int(random_sleep)} sec in {Fore.RESET}{Fore.MAGENTA}({message.guild.name}/#{message.channel.name}){Fore.RESET}\n")
                    
                    except asyncio.TimeoutError:
                        print(f"{Fore.RED}Timeout for {Fore.MAGENTA}{self.user.name}{Fore.RESET} in {Fore.MAGENTA}({message.guild.name}/#{message.channel.name}){Fore.RESET}. Sleeping for {Fore.GREEN}{random_sleep} sec{Fore.RESET}{Fore.RESET}\n")
                    
                    break  # После одного ответа бот делает паузу

            await asyncio.sleep(10)


    def get_processed_messages(self):
        processed_messages_file = os.path.join(self.history_folder_path, "processed_messages.txt")
        if os.path.exists(processed_messages_file):
            with open(processed_messages_file, "r") as file:
                return file.read().splitlines()
        else:
            return []

    def add_to_processed_messages(self, message_id):
        processed_messages_file = os.path.join(self.history_folder_path, "processed_messages.txt")
        with open(processed_messages_file, "a") as file:
            file.write(f"{message_id}\n")

# Основная функция для запуска нескольких ботов
async def main():
    tokens = read_tokens("discord.txt")
    proxies_list = read_proxies("proxy.txt")

    if len(tokens) != len(proxies_list):
        print("Число токенов и прокси не совпадает.")

    tasks = []
    for idx, token in enumerate(tokens):
        # Создаем уникальную папку для каждого бота (например, используя первые 8 символов токена)
        history_folder = os.path.join("conversations", token[:8])
        os.makedirs(history_folder, exist_ok=True)
        if idx < len(proxies_list):
            proxy_url, proxy_auth = proxies_list[idx]
            print(f"Запуск бота с токеном {token[:10]}... и прокси {proxy_url}")
            chat_bot = SelfbotClient(history_folder_path=history_folder, proxy=proxy_url, proxy_auth=proxy_auth)
        else:
            print(f"Запуск бота с токеном {token[:10]} без прокси")
            chat_bot = SelfbotClient(history_folder_path=history_folder)
        tasks.append(chat_bot.start(token))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Выход из программы...")
