# BenzinaOggi

BenzinaOggi is a Python bot that provides daily updates on the cheapest fuel stations near a specified location. It supports various fuel types (e.g., gasoline, diesel) and uses official data sources.

## Features

- Provides the lowest fuel prices for a specified location and fuel type.
- Sends Telegram messages with station details.
- Supports separate fuel type notifications (e.g., gasoline only).
- Calculates distances between the user and fuel stations.

## Requirements

- Python 3.x
- Libraries: `requests`, `pyTelegramBotAPI`, `csv`, `json`, `math`, `datetime`

Install dependencies:

```bash
pip install requests pyTelegramBotAPI
```

## Setup

1. Create a bot on Telegram using [BotFather](https://core.telegram.org/bots#botfather) and get the API token.
2. Replace the token and chat IDs in the script:

```python
TELEGRAM_BOT_TOKEN = "<TELEGRAM-BOT-TOKEN>"
CHAT_IDS = {
    "all_fuels": "<CHAT-ID>",  
    "only_benzina": "<CHAT-ID>"
}
```

3. The bot fetches station and price data from official CSV files.

## Running the Bot

Execute the bot with:

```bash
python BenzinaOggi.py
```

## Automating (Optional)

Schedule daily execution using cron (Linux) or Task Scheduler (Windows).
