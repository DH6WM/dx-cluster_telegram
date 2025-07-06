# 📡 DX Cluster Monitor Bot

A Python-based async Telegram bot that connects to a telnet-based DX Cluster and monitors real-time amateur radio spot activity. The bot filters incoming DX spots based on user-defined rules and notifies you via Telegram when a match occurs.
By Ham Radio Op. DH6WM

---

## ✨ Features

- 🔍 Realtime DX spot parsing from telnet clusters
- 🧠 Band and mode detection based on frequency and Comment
- 📬 Telegram bot alerts for callsign matches
- 📏 Optional filtering by callsign prefix/suffix/region...
- 📈 Logging to daily CSV files (spots, messages, errors)
- 📂 Logs stored in `/log` folder, structured by type

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13.3+
- A Telegram bot token
- A telnet-based DX cluster (e.g. `dxc.cluster.net`)

### Installation

git clone https://github.com/DH6WM/dx-cluster_telegram.git
cd dx-cluster_telegram

pip install telnetlib3
pip install python-telegram-bot

Edit dx-cluster_telnet.py to configure:
- Telnet Server, Port, Username and Password
- Telegram Bot Token (can be done direct into the in the bot_token variable or via an Environment variable)
- Cluster Radius (in the variable RADIUS_PREFIXES) is currently set to Germany and its immediate neighboring countries

Edit user_config.json to set up your own admin user:
- set up your bot by contacting @BotFather on Telegram
- follow instructions...
- find your own Bot and start a private chat
- open "https://api.telegram.org/bot<BotToken>/getUpdates" on a Browser fill <BotToken> with ten API Key by @BotFather.
- read out chatID under result/message/from/id
- enter the ID in your user_config.json file (replace <your Chat ID>)

