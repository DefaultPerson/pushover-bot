<h1 align="center">Pushover Bot</h1>

<p align="center">
  <img src="assets/header.png" alt="Pushover Bot" width="600" />
</p>

<p align="center">
  <a href="https://t.me/PushoverABot"><img src="https://img.shields.io/badge/Telegram-@PushoverABot-26A5E4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram Bot" /></a>
  <img src="https://img.shields.io/badge/python-3.14-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/aiogram-3.x-009688?style=flat-square" alt="aiogram" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License" /></a>
</p>

Telegram bot for emergency notifications via [Pushover](https://pushover.net/). Wakes you up with a siren even when your phone is on silent. Add the bot to a group — any member can send an emergency alert to everyone or a specific person.

> **Note:** Group Privacy Mode must be **disabled** in BotFather. Otherwise the bot won't receive messages in groups (except commands and replies). If it was enabled, remove and re-add the bot to the group.

## Features

- **Emergency alerts** — Pushover Priority 2, bypasses quiet hours, repeats every 30s until acknowledged
- **Group chats** — `/gm` sends a siren to all subscribed members
- **Targeted notifications** — `/pgm` (reply or `@username`), `/gm @username`, `/gm user_id`
- **Custom text** — `/gm hello` or `/pgm @username wake up`
- **Inline mode** — type `@bot name text` in a group; works even where the bot misses commands
- **Cancel repeats** — the sender can stop the siren with a button under the result
- **Quiet hours** — `/quiet`: alerts from others arrive silently, without repeats
- **Blocks** — `/block` a person, or refuse all personal alerts with `/personalgms off`
- **Message archiving** — saves all group messages to DB with media files
- **HTML export** — searchable archive with media thumbnails
- **Broadcast** — mass messaging for admins
- **Rate limiting** and **multi-language** support (EN, RU, UK)

## Quick Start

```bash
git clone https://github.com/DefaultPerson/pushover-bot.git
cd pushover-bot
cp .env.example .env
nano .env  # fill in BOT_TOKEN, PUSHOVER_APP_TOKEN, DB_PASSWORD
docker compose -f docker-compose.full.yml up -d
```

`docker-compose.full.yml` runs PostgreSQL, Redis, and the bot together.

For a fresh VPS, deploy with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/DefaultPerson/pushover-bot/main/scripts/deploy.sh | bash
```

## Commands

### Private chat

| Command | Description |
|---------|-------------|
| `/key` | Set up Pushover User Key |
| `/list` | Groups with active notifications |
| `/test_alarm` | Send a test siren to yourself |
| `/quiet 23:00-07:00 Europe/Kyiv` | Daily quiet hours; also `/quiet once 23:00-07:00`, `/quiet 8h`, `/quiet off` |
| `/block @username` / `/block user_id` | Stop alerts from a person; `/unblock`, `/blocks` |
| `/personalgms on\|off` | Accept or refuse personal alerts |
| `/language` | Change language |
| `/id` | Your Telegram id |

### Group chat

| Command | Description |
|---------|-------------|
| `/gm` | Alert everyone |
| `/gm text` | Alert everyone with custom text |
| `/gm @username` | Alert a specific member |
| `/gm @username text` | Specific member with custom text |
| `/gm user_id` | Alert by user ID |
| `/pgm [text]` (reply) / `/pgm @username [text]` | Personal alert; never wakes the whole group |
| `@bot [name] [text]` | Inline: pick everyone or a person from the list |
| `/enable` / `/disable` | Toggle notifications |
| `/block` (reply) | Stop alerts from this person |
| `/id` | Ids of you, the chat, the topic and the replied person |
| `/only_admin` | Restrict `/gm` to admins only |
| `/confirm_gm` | Ask "Wake N people?" before a group alert (admins) |

### Inline mode

Enable it once in BotFather: `/setinline` → choose the bot → set a placeholder such as `name and text…`. Telegram delivers messages posted through inline mode even to a non-admin bot in privacy mode.

## Configuration

See [`.env.example`](.env.example) for all available environment variables.

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram Bot Token | required |
| `PUSHOVER_APP_TOKEN` | Pushover App Token | required |
| `DB_PASSWORD` | PostgreSQL password | required |
| `ADMIN_IDS` | Admin Telegram IDs (comma-separated) | |
| `DEFAULT_TIMEZONE` | Timezone for `/quiet` when the user gives none | `UTC` |
| `ARCHIVE_ENABLED` | Archive group messages | `false` |

## Development

```bash
uv pip install -e libs/aiogram-broadcast
uv pip install -e .
make run
```

## License

This project is licensed under the [MIT License](LICENSE).
