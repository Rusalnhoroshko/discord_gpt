import discord
import config
import json
import asyncio
import re
import os
import random
from colorama import Fore
from openai import OpenAI
from openai import OpenAIError

token = config.discord_token
allowed_channels = config.chat_ids  # Подставьте нужные ID
history_folder_path = config.history_folder_path
TRIGGERS = config.TRIGGERS

client = OpenAI(api_key=config.openai_api)

# Класс для работы с ChatGPT
class ChatGPTWrapper:
    def __init__(self):
        self.mutex = asyncio.Lock()

    async def generate_response(self, user_input, user_name, message):
        """
        Генерирует ответ и формирует обновлённую историю переписки,
        но запись в файл производится вне этого метода.
        """
        async with self.mutex:
            try:
                await asyncio.sleep(2)

                sanitized_server_name = re.sub(r'\W+', '', message.guild.name)
                sanitized_user_name = re.sub(r'\W+', '', user_name)
                user_id = f"{sanitized_user_name}_{sanitized_server_name}"
                user_folder_path = os.path.join(history_folder_path, sanitized_server_name)
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
                    temperature=1,
                    max_completion_tokens=30,
                    top_p=0.5,
                    frequency_penalty=0,
                    presence_penalty=0,
                    messages=[{"role": "system", "content": updated_prompt}] + history_data["messages"]
                )
                generated_response = response.choices[0].message.content.strip()

                # Добавляем ответ ассистента в историю (но запись в файл будет выполнена позже)
                history_data["messages"].append({"role": "assistant", "content": generated_response})

                # Возвращаем сгенерированный ответ, а также данные для сохранения истории
                return generated_response, history_data, user_folder_path, file_path

            except OpenAIError as e:
                print(f"{Fore.RED}OpenAI Error:{Fore.RESET} {e}")
                return "I can't respond now.", None, None, None

# SELFBOT для Discord
class SelfbotClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chatbot = ChatGPTWrapper()

    async def on_ready(self):
        self.bg_task = self.loop.create_task(self.check_messages())
        print(f'Logged in as {Fore.RED}{self.user}{Fore.RESET}')

    async def on_message(self, message):
        # Проверка, чтобы бот не отвечал сам себе и чтобы чат был разрешён
        if message.author == self.user or message.channel.id not in allowed_channels:
            return

        if self.user.mentioned_in(message) and message.content:
            user_input = message.content.lstrip(self.user.mention).strip()
            user_name = message.author.nick or message.author.name

            # Получаем ответ и данные для истории переписки
            response_text, history_data, user_folder_path, file_path = await self.chatbot.generate_response(user_input, user_name, message)

            print(f"{Fore.LIGHTGREEN_EX}({message.guild.name}/#{message.channel.name}){Fore.RESET}\n"
                  f"{Fore.LIGHTGREEN_EX}{user_name}{Fore.RESET}: {user_input}\n"
                  f"{Fore.LIGHTGREEN_EX}{self.user.name}{Fore.RESET}: {response_text}\n")

            if response_text.strip():
                typing_time = len(response_text) * 1  # Или подберите нужный коэффициент
                async with message.channel.typing():
                    await asyncio.sleep(typing_time)
                try:
                    await asyncio.wait_for(message.reply(response_text), timeout=5)
                    # Если отправка успешна, записываем обновлённую историю в файл
                    os.makedirs(user_folder_path, exist_ok=True)
                    with open(file_path, "w") as history_file:
                        json.dump(history_data, history_file, indent=2)
                except asyncio.TimeoutError:
                    print('rate limit – запись в историю не произведена')
            else:
                print("Generated response is empty. Skipping reply.")
              

    async def check_messages(self):
        # Ожидание, пока бот не будет готов
        await self.wait_until_ready()
        channel_cooldowns = {}
        while not self.is_closed():
            current_time = asyncio.get_event_loop().time()
            for channel_id in allowed_channels:
                channel = self.get_channel(channel_id)
                if channel:
                    next_allowed_time = channel_cooldowns.get(channel_id, 0)
                    if current_time < next_allowed_time:
                        # Этот канал всё ещё на cooldown – пропускаем его
                        continue
                    async for message in channel.history(limit=10):
                        # Исключаем сообщения от самого бота и ответы на другие сообщения
                        if message.author == self.user or message.author.id == self.user.id:
                            continue
                        if message.reference:
                            continue
                        # Проверяем, что сообщение ещё не было обработано
                        if str(message.id) not in self.get_processed_messages():
                            if not message.reference:
                                mentioned_users = message.mentions
                                if not mentioned_users:
                                    user_name = message.author.display_name or message.author.name
                                    response_text, history_data, user_folder_path, file_path = await self.chatbot.generate_response(message.content, user_name, message)
                                    print(f"{Fore.MAGENTA}({message.guild.name}/#{message.channel.name}){Fore.RESET}\n"
                                            f"{Fore.MAGENTA}{user_name}{Fore.RESET}: {message.content}\n"
                                            f"{Fore.MAGENTA}{self.user.name}{Fore.RESET}: {response_text}\n")
                                    if response_text.strip():
                                        typing_time = len(response_text) * 1
                                        async with message.channel.typing():
                                            await asyncio.sleep(typing_time)
                                    try:
                                        await asyncio.wait_for(message.channel.send(response_text), timeout=5)
                                        os.makedirs(user_folder_path, exist_ok=True)
                                        with open(file_path, "w") as history_file:
                                            json.dump(history_data, history_file, indent=2)
                                        self.add_to_processed_messages(message.id)
                                        sleep_after_reply = random.uniform(240, 360)
                                        channel_cooldowns[channel_id] = asyncio.get_event_loop().time() + sleep_after_reply
                                        print(f"{Fore.GREEN}sleeping {sleep_after_reply} sec in {Fore.RESET}\n")
                                    except asyncio.TimeoutError:
                                        # Если истекло время ожидания, можно задать дефолтный cooldown
                                        default_sleep = 400
                                        channel_cooldowns[channel_id] = asyncio.get_event_loop().time() + default_sleep
                                        print(f"{Fore.RED}Timeout when sending message in channel {channel.name}. Sleeping for {default_sleep} sec{Fore.RESET}\n")
                                    break
            await asyncio.sleep(10)



    def get_processed_messages(self):
        processed_messages_file = os.path.join(history_folder_path, "processed_messages.txt")
        if os.path.exists(processed_messages_file):
            with open(processed_messages_file, "r") as file:
                return file.read().splitlines()
        else:
            return []

    def add_to_processed_messages(self, message_id):
        processed_messages_file = os.path.join(history_folder_path, "processed_messages.txt")
        with open(processed_messages_file, "a") as file:
            file.write(f"{message_id}\n")

# Запуск бота
chat_bot = SelfbotClient()
chat_bot.run(token)
