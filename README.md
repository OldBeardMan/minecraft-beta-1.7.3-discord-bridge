# Minecraft Beta 1.7.3 Discord Bridge

A Discord bot that bridges Minecraft Beta 1.7.3 servers with Discord by reading logs and sending commands through GNU screen.

## Features

- ✅ **MC → Discord**: Chat messages, player join/leave events
- ✅ **Discord → MC**: Discord messages in-game (using `say` command)
- ✅ **Discord Embeds**: Formatted messages with player avatars (minotar.net)
- ✅ **Screen Integration**: Direct command sending to screen session

## Requirements

- Python 3.6+
- Minecraft Beta 1.7.3 server running in GNU screen session
- Discord Bot (token from Discord Developer Portal)

## Installation

### 1. Install dependencies
```bash
cd discord-bridge
pip3 install --user -r requirements.txt
```

### 2. Discord Bot Setup

1. Go to https://discord.com/developers/applications
2. Create an application and add a bot
3. Copy the TOKEN
4. Enable **MESSAGE CONTENT INTENT** in Bot tab
5. Add the bot to your server with permissions: Send Messages, Embed Links, Read Message History

### 3. Configure .env

Edit the `.env` file:
```env
DISCORD_TOKEN=your_token_here
DISCORD_CHANNEL_ID=channel_id_here
SERVER_LOG_PATH=../server/server.log
SCREEN_SESSION_NAME=beta173
MC_PREFIX=[Minecraft]
DISCORD_PREFIX=[Discord]
```

**How to find Channel ID?**
Enable Developer Mode in Discord → Right-click on channel → Copy ID

**How to find screen session name?**
```bash
screen -ls
# Use the name without PID, e.g. "beta173"
```

## Usage

```bash
# MC server must already be running in screen
screen -ls  # Check session name

# Start the bot in a new screen session
screen -S discord-bot
cd discord-bridge
python3 bot.py

# Detach: Ctrl+A, D
```

## Commands

- `!status` - Bot and connection status

## How it works

**MC → Discord:**
- Bot reads `server.log` every second (polling)
- Detects regex patterns: chat, join, leave
- Sends embeds to Discord

**Discord → MC:**
- Bot captures messages from the channel
- Sends `say` command through `screen -X stuff`
- Appears in-game as: `[Discord] Username: message`

## Troubleshooting

**Bot doesn't detect MC messages:**
- Check if the `server.log` path is correct
- Make sure the bot has read permissions for the file

**Discord messages don't reach MC:**
- Verify the screen session name is correct (`screen -ls`)
- Check if the server is running in that session
- Make sure `screen` is installed

**Package installation issues:**
```bash
# For Python 3.6 you might need:
sudo yum install python3-devel gcc -y
pip3 install --user -r requirements.txt
```

## Project Structure

```
discord-bridge/
├── bot.py                  # Main bot
├── screen_integration.py   # GNU screen integration
├── requirements.txt        # Python dependencies
├── .env                    # Configuration (DO NOT commit!)
└── README.md              # This documentation
```

## License

MIT
