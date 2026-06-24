# 🤖 Telegram Group Manager Bot

A full-featured Telegram group management bot built with **python-telegram-bot v20** and ready for **Railway** deployment.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔨 **Ban / Kick / Mute** | Timed mutes (e.g. `/mute 1h`), permanent bans, kick |
| ⚠️ **Warnings** | Auto-ban after N warnings (configurable), warn/unwarn/list |
| 🚫 **Blocklist** | Auto-delete messages with banned words, auto-warn sender |
| 🌙 **Night Mode** | Scheduled group lock/unlock with custom cron times |
| 👋 **Welcome Message** | Customisable with `{name}` `{username}` `{chat}` variables |
| 📅 **Scheduled Messages** | Cron-based recurring messages per group |
| 📋 **Logs** | All actions sent to a configured log channel |
| 🔒 **Profile Guard** | Auto-mutes users with no name/username; auto-unmutes on profile update |

---

## 🚀 Railway Deployment

### 1. Fork / push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. Create a Railway project

1. Go to [railway.app](https://railway.app) and create a new project
2. Choose **Deploy from GitHub repo** and select your repo
3. Railway will auto-detect the `Procfile`

### 3. Set environment variables

In the Railway dashboard → **Variables**:

| Variable | Value |
|---|---|
| `BOT_TOKEN` | Your token from [@BotFather](https://t.me/BotFather) |
| `DB_PATH` | `/data/groupbot.db` *(optional, see Volume below)* |

### 4. Add a Volume (recommended for persistence)

In Railway → your service → **Volumes**:
- Mount path: `/data`
- Set `DB_PATH=/data/groupbot.db`

This persists the SQLite database across deploys and restarts.

---

## 🛠 Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set token
export BOT_TOKEN="your_token_here"

# Run
python bot.py
```

---

## 📋 Command Reference

### Moderation (admin only)
```
/ban [@user|reply] [reason]      — Permanently ban
/unban [@user|reply]             — Unban
/kick [@user|reply] [reason]     — Kick (can rejoin)
/mute [@user|reply] [time]       — Mute (1m/1h/1d or permanent)
/unmute [@user|reply]            — Unmute
/warn [@user|reply] [reason]     — Issue a warning
/unwarn [@user|reply]            — Clear all warnings
/warnings [@user|reply]          — View warning history
/setwarn <number>                — Set max warnings (default: 3)
```

### Blocklist (admin only)
```
/addblock <word>    — Add word to blocklist
/rmblock <word>     — Remove word from blocklist
/blocklist          — List all blocked words
```

### Night Mode (admin only)
```
/nightmode on                      — Enable night mode
/nightmode off                     — Disable night mode
/nightmode set HH:MM HH:MM         — Set lock and unlock times
/nightmode status                  — View current schedule
```

### Welcome (admin only)
```
/setwelcome <message>   — Set welcome text
                          Variables: {name} {username} {chat}
/welcome on|off          — Toggle welcome messages
```

### Scheduled Messages (admin only)
```
/schedule "cron" <message>   — Add scheduled message
                               Example: /schedule "0 9 * * *" GM!
/schedules                   — List all scheduled messages
/delschedule <id>             — Delete a scheduled message
```

### Logs & Settings (admin only)
```
/setlog <channel_id>   — Set log channel (add bot as admin there first)
/setlog off            — Disable logging
/settings              — View all current settings
```

---

## 🔒 Profile Guard (automatic)

Users who join or message without a Telegram **first name** or **username** are automatically muted with instructions. As soon as they update their profile and send a message, they are unmuted automatically.

---

## 📁 Project Structure

```
tg-group-bot/
├── bot.py                  # Entry point
├── database.py             # SQLite helpers (aiosqlite)
├── utils.py                # Shared helpers
├── requirements.txt
├── Procfile                # Railway process definition
├── railway.json            # Railway config
├── README.md
└── handlers/
    ├── help.py             # /start, /help
    ├── moderation.py       # ban/unban/kick/mute/warn
    ├── blocklist.py        # blocked words
    ├── nightmode.py        # scheduled lock/unlock
    ├── welcome.py          # new member greeting
    ├── scheduler.py        # recurring messages
    ├── settings.py         # /setlog, /settings
    └── profile_guard.py    # auto-mute no-profile users
```

---

## ⚙️ Bot Permissions Required

When adding the bot to a group, grant it these admin permissions:
- ✅ Delete messages
- ✅ Ban users
- ✅ Restrict members
- ✅ Send messages

---

## 📝 License

MIT — free to use and modify.
