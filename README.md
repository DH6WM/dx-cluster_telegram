# 📡 DX Cluster Monitor Bot

A Python-based async Telegram bot that connects to a Telnet-based DX Cluster and monitors real-time amateur radio spot activity. The bot filters incoming DX spots based on user-defined rules and notifies you via Telegram when a match is found.  
By Ham Radio Operator **DH6WM**

---

## ✨ Features

- 🔍 Realtime DX spot parsing from Telnet clusters  
- 🧠 Band and mode detection based on frequency and comment  
- 📬 Telegram bot alerts for callsign matches  
- 📏 Optional filtering by callsign prefix, suffix, or region  
- 📈 Logging to daily CSV files (spots, messages, errors)  
- 📂 Logs stored in the `/log` folder, organized by type  

---

## 🚀 Quick Start

### Prerequisites

- Python **3.11+**  
- A Telegram bot token  
- Access to a Telnet-based DX Cluster (e.g. `dxc.cluster.net`)  

---

### Installation

```bash
git clone https://github.com/DH6WM/dx-cluster_telegram.git
cd dx-cluster_telegram

pip install telnetlib3
pip install python-telegram-bot
```

---

### Configuration

Edit `dx-cluster_telnet.py` to configure:

- **Telnet server, port, username, and password**

- **Telegram bot token**  
  - Set it directly in the `bot_token` variable  
  - Or load it from an environment variable (recommended for security)

- **Cluster radius**  
  - Configurable via the `RADIUS_PREFIXES` variable  
  - Currently set to Germany and its immediate neighboring countries

### Telegram Bot Setup

Edit `user_config.json` to set up your own admin user:

- Create a new bot by contacting [@BotFather](https://t.me/BotFather) on Telegram
- Follow the instructions and copy your API token
- Start a chat with your bot
- Open the following URL in your browser (replace `<BotToken>` with your token):  
`https://api.telegram.org/bot<BotToken>/getUpdates`
- Find your own chat ID under `result/message/from/id`
- Copy that ID into `user_config.json` by replacing `<your Chat ID>`


### Start Script:
```bash
python ./dx-cluster_telnet.py
```
