# Discord bot

## Bot Functionality Description
- A separate bot is created for each token from `discord.txt` (and added to an exclusion list so that bots do not start interacting with each other).
- If a `proxy.txt` file is available, the bot can work through a specified proxy (if no proxy is provided, the bot will indicate which token is running without a proxy).
- It considers the previous conversation history by loading already saved messages and responses from the corresponding JSON file.
- When a new message is received, a request is formed to OpenAI: a system prompt (from `config.promt`) plus the entire conversation history with the specific user on that server.
- The response is appended to the conversation history to maintain context for future interactions.
- Upon startup, the script waits for a random time (10–60 seconds) to avoid activating all bots simultaneously and to prevent suspicious activity.
- It ignores its own messages and channels not included in `allowed_channels`.
- If the bot is mentioned (@bot), it generates a response, simulates typing time (a delay proportional to the length of the response), and sends the message using the `reply` method.
- Periodically, it reviews randomly selected allowed channels, chooses one random message from the last 20 messages, and responds to it either with a reply or as a normal message (random choice).
- After a successful response, it sets a "cooldown" on the channel (variable `default_sleep`) to prevent spamming.
- When sending a response, the bot simulates typing proportional to the length of the text.

## Message Storage and Control
- The conversation history is saved in JSON format: a separate file is created for each user on each server.
- The file `processed_messages.txt` contains the IDs of messages that the bot has already responded to, in order to avoid duplicate reactions.
- Upon a successful response, the reply is added to the conversation history, and the message ID is added to the list of processed messages.

## Logging and Colorful Console Output
- The bot logs all actions in detail: which channel, who wrote the message, what response was generated, how many seconds the bot "rests," etc.
- The `colorama` library is used for clear, color-coded formatting of messages in the terminal.

## Conclusion
Each instance of the bot operates as a selfbot, communicates with GPT considering the entire previous conversation history, responds to mentions and random messages while respecting constraints (cooldowns, timers), and stores the entire conversation and processing status—maintaining independence from other instances.

## For Setup
- **`discord.txt`** – one token per line (without quotes or commas).
- **`proxy.txt`** – one proxy per line (`ip:port:login:password`). Use this: [https://proxyshard.com?ref=44](https://proxyshard.com?ref=44) (thanks @capitanike).
- Run the command: `pip install -r requirements.txt`
- Then start the bot with: `python3 main.py`

## Variables
- **`allowed_channels`** – IDs of the required channels, separated by commas.
- **`default_sleep`** – Timeout for each channel.
- **`gpt_model`** – GPT model (default is “gpt-4o-mini”).
- **`openai_api`** – API key (obtain it from [https://platform.openai.com/settings/organization/api-keys](https://platform.openai.com/settings/organization/api-keys)).
- **`prompt`** – Your prompt for conversation.
