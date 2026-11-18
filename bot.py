import discord
from discord.ext import commands
import asyncio
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from screen_integration import send_to_screen, sanitize_for_console

# Load configuration from .env
load_dotenv()

# Configuration
TOKEN = os.getenv('DISCORD_TOKEN')
try:
    CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', ''))
except ValueError:
    CHANNEL_ID = None
SERVER_LOG_PATH = Path(__file__).parent / os.getenv('SERVER_LOG_PATH', '../server/server.log')
SCREEN_SESSION = os.getenv('SCREEN_SESSION_NAME', 'minecraft')
MC_PREFIX = os.getenv('MC_PREFIX', '[Minecraft]')
DISCORD_PREFIX = os.getenv('DISCORD_PREFIX', '[Discord]')

# Beta 1.7.3 clients disconnect on chat packets longer than 119 chars.
# The console `say` command adds a "[Server] " prefix, so keep each line well below that.
MAX_SAY_LENGTH = 100

# Compatibility with discord.py 1.7.3
def get_utcnow():
    try:
        return discord.utils.utcnow()
    except AttributeError:
        return datetime.utcnow()

# Regex patterns for chat messages (Beta 1.7.3 format)
CHAT_REGEX = re.compile(r'\[INFO\] <([^>]+)> (.+)')
JOIN_REGEX = re.compile(r'\[INFO\] ([^\s]+) \[\/[\d.:]+\] logged in')
LEAVE_REGEX = re.compile(r'\[INFO\] ([^\s]+) lost connection')

# Patterns to ignore (spam, errors)
IGNORE_PATTERNS = [
    r'java\.io\.IOException',
    r'at \w+\.',
    r'Bad packet id',
    r'^\s*$',  # Empty lines
    r'\/\d+\.\d+\.\d+\.\d+:\d+ lost connection',  # IP lost connection (bot spam)
]
IGNORE_REGEX = re.compile('|'.join(IGNORE_PATTERNS))

# Discord Intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
try:
    intents.message_content = True
except AttributeError:
    pass

bot = commands.Bot(command_prefix='!', intents=intents)

# Global variables
discord_channel = None
last_log_position = 0
polling_started = False


def read_new_log_lines():
    global last_log_position
    if not SERVER_LOG_PATH.exists():
        return []
    try:
        # Log was truncated or replaced - start from the beginning
        if SERVER_LOG_PATH.stat().st_size < last_log_position:
            last_log_position = 0
        with open(SERVER_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_log_position)
            new_lines = f.readlines()
            last_log_position = f.tell()
            return new_lines
    except Exception as e:
        print(f"Error reading log: {e}")
        return []


def process_log_line(line):
    line = line.strip()

    # Ignore spam and errors
    if IGNORE_REGEX.search(line):
        return None

    # Chat message
    chat_match = CHAT_REGEX.search(line)
    if chat_match:
        player, message = chat_match.groups()
        return ('chat', player, message)

    # Join - only real players (with login)
    join_match = JOIN_REGEX.search(line)
    if join_match:
        return ('join', join_match.group(1), None)

    # Leave - only if it has player name (not IP)
    leave_match = LEAVE_REGEX.search(line)
    if leave_match:
        player = leave_match.group(1)
        # Ignore if it's just an IP (starts with /)
        if not player.startswith('/'):
            return ('leave', player, None)

    return None


async def send_to_minecraft(message):
    try:
        success = send_to_screen(message, SCREEN_SESSION)
        if success:
            print(f"Sent to MC: {message}")
        return success
    except Exception as e:
        print(f"Error sending to MC: {e}")
        return False


def on_log_changed():
    lines = read_new_log_lines()
    for line in lines:
        result = process_log_line(line)
        if result:
            event_type, player, data = result
            if event_type == 'chat':
                print(f"[MC] {player}: {data}")
                asyncio.ensure_future(send_chat_to_discord(player, data))
            elif event_type == 'join':
                print(f"[MC] {player} joined")
                asyncio.ensure_future(send_join_to_discord(player))
            elif event_type == 'leave':
                print(f"[MC] {player} left")
                asyncio.ensure_future(send_leave_to_discord(player))


async def send_chat_to_discord(player, message):
    if not discord_channel:
        return
    embed = discord.Embed(description=message, color=discord.Color.blue(), timestamp=get_utcnow())
    embed.set_author(name=player, icon_url=f"https://minotar.net/avatar/{player}/64")
    try:
        await discord_channel.send(embed=embed)
    except Exception as e:
        print(f"Error: {e}")


async def send_join_to_discord(player):
    if not discord_channel:
        return
    embed = discord.Embed(description=f"**{player}** joined the game", color=discord.Color.green(), timestamp=get_utcnow())
    try:
        await discord_channel.send(embed=embed)
    except Exception as e:
        print(f"Error: {e}")


async def send_leave_to_discord(player):
    if not discord_channel:
        return
    embed = discord.Embed(description=f"**{player}** left the game", color=discord.Color.red(), timestamp=get_utcnow())
    try:
        await discord_channel.send(embed=embed)
    except Exception as e:
        print(f"Error: {e}")


async def poll_log_file():
    while True:
        try:
            await asyncio.sleep(1)
            if SERVER_LOG_PATH.exists():
                on_log_changed()
        except Exception as e:
            print(f"Polling error: {e}")


@bot.event
async def on_ready():
    global discord_channel, last_log_position, polling_started
    print(f"Bot logged in: {bot.user}")

    # on_ready fires again after every reconnect - only initialize once
    if polling_started:
        return

    discord_channel = bot.get_channel(CHANNEL_ID)
    if not discord_channel:
        print(f"Channel not found: {CHANNEL_ID}")
        await bot.close()
        return

    print(f"Channel: {discord_channel.name}")
    embed = discord.Embed(
        title="Discord Bridge Online",
        description=f"MC Server: `{SCREEN_SESSION}`",
        color=discord.Color.green(),
        timestamp=get_utcnow()
    )
    await discord_channel.send(embed=embed)

    if SERVER_LOG_PATH.exists():
        with open(SERVER_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, 2)
            last_log_position = f.tell()
        print(f"Monitoring: {SERVER_LOG_PATH}")
        polling_started = True
        bot.loop.create_task(poll_log_file())
    else:
        print(f"server.log not found: {SERVER_LOG_PATH}")


@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != CHANNEL_ID:
        return
    if message.content.startswith('!') or message.content.startswith('/'):
        await bot.process_commands(message)
        return

    username = sanitize_for_console(message.author.display_name) or 'Unknown'
    text = sanitize_for_console(message.content)
    if message.attachments:
        text = f"{text} [attachment]".strip()
    if not text:
        return

    print(f"[Discord] {username}: {text}")
    header = f"{sanitize_for_console(DISCORD_PREFIX)} {username}: "
    # Split long messages so no single line exceeds the client chat limit
    chunk_size = max(MAX_SAY_LENGTH - len(header), 20)
    for i in range(0, len(text), chunk_size):
        await send_to_minecraft(f"say {header}{text[i:i + chunk_size]}")


@bot.command(name='status')
async def status_command(ctx):
    if ctx.channel.id != CHANNEL_ID:
        return
    embed = discord.Embed(title="Status", color=discord.Color.blue())
    embed.add_field(name="Bot", value="Online", inline=True)
    embed.add_field(name="Screen", value=f"`{SCREEN_SESSION}`", inline=True)
    embed.add_field(name="Log", value="Yes" if SERVER_LOG_PATH.exists() else "No", inline=True)
    await ctx.send(embed=embed)


if __name__ == "__main__":
    print("Discord Bridge for Minecraft Beta 1.7.3")
    if not TOKEN or not CHANNEL_ID:
        print("Missing or invalid DISCORD_TOKEN / DISCORD_CHANNEL_ID in .env")
        exit(1)
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
