import discord
import json
import random
import os
import time
import signal
import sys
import asyncio
from typing import Optional
from discord.ext import commands, tasks
from tinydb import TinyDB, Query

TOKEN = os.getenv('TOKEN') or os.getenv('DISCORD_BOT_TOKEN') or 'YOUR_BOT_TOKEN_HERE'

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

db = TinyDB('tower_storage.json')
user_table = db.table('users')
user_data = {}

def load_data():
    global user_data
    user_data = {}
    for item in user_table.all():
        user_id = str(item.doc_id)
        user_data[user_id] = item
    print(f"✅ Loaded {len(user_data)} users from TinyDB")

def save_data():
    try:
        user_table.truncate()
        for user_id, data in user_data.items():
            user_table.insert(data)
        print("💾 Data saved to TinyDB")
    except Exception as e:
        print(f"❌ Failed to save data: {e}")

def graceful_shutdown():
    print("🛑 Shutting down bot...")
    print("💾 Saving all data before shutdown...")
    save_data()
    print("✅ Data saved. Bot shutdown complete.")
    sys.exit(0)

def signal_handler(signum, frame):
    print(f"📡 Received signal {signum}")
    graceful_shutdown()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@tasks.loop(minutes=5)
async def auto_save():
    save_data()
    print("⏰ Auto-save completed")

BASE_XP = 50
MAX_XP_PER_LEVEL = 500

def calculate_level(xp):
    if xp < 100:
        return 1
    total_xp_needed = 0
    level = 1
    while total_xp_needed <= xp:
        level += 1
        xp_for_next_level = min(50 + (level - 2) * 50, MAX_XP_PER_LEVEL)
        total_xp_needed += xp_for_next_level
        if total_xp_needed > xp:
            level -= 1
            break
    return max(1, level)

def xp_required_for_next_level(current_xp):
    current_level = calculate_level(current_xp)
    total_xp_needed = 0
    level = 1
    while level <= current_level:
        level += 1
        xp_for_level = min(50 + (level - 2) * 50, 500)
        total_xp_needed += xp_for_level
    return total_xp_needed - current_xp

def calculate_height(user_id):
    if user_id not in user_data:
        return 5
    user = user_data[user_id]
    base = user.get("base_height", 5)
    bonus = user.get("bonus_height", 0)
    level = calculate_level(user.get("xp", 0))
    return base + bonus + (level - 1) * 3

def get_title(level):
    titles = [
        "Peasant", "Apprentice", "Builder", "Craftsman", "Architect",
        "Master Builder", "Tower Lord", "Sky Reacher", "Cloud Walker", "Storm Touched",
        "Heaven's Engineer"
    ]
    return titles[level - 1] if level <= len(titles) else f"Celestial Architect Lv.{level}"

def get_tower_flavor(height):
    if height <= 10:
        return "A modest foundation, every tower starts somewhere."
    elif height <= 25:
        return "Your tower begins to cast a shadow."
    elif height <= 50:
        return "Impressive! Your tower dominates the skyline."
    elif height <= 100:
        return "Magnificent! Your tower pierces the clouds."
    elif height <= 200:
        return "Legendary! Your tower reaches toward the heavens."
    else:
        return "DIVINE! Your tower challenges the gods themselves!"

def init_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "xp": 0,
            "base_height": 5,
            "bonus_height": 0,
            "wins": 0,
            "losses": 0,
            "welcomed": False,
            "height_timestamp": time.time(),
            "previous_height": 5
        }

def update_height_timestamp(user_id):
    if user_id in user_data:
        current = calculate_height(user_id)
        if current > user_data[user_id].get("previous_height", 5):
            user_data[user_id]["height_timestamp"] = time.time()
            user_data[user_id]["previous_height"] = current

async def add_xp(user, amount, channel):
    user_id = str(user.id)
    init_user(user_id)
    old_level = calculate_level(user_data[user_id]["xp"])
    user_data[user_id]["xp"] += amount
    new_level = calculate_level(user_data[user_id]["xp"])
    if new_level > old_level:
        height = calculate_height(user_id)
        title = get_title(new_level)
        flavor = get_tower_flavor(height)
        embed = discord.Embed(
            title="🎉 Level Up!",
            description=f"**{user.display_name}** has reached **Level {new_level}**!",
            color=0x00FF7F
        )
        embed.add_field(name="New Title", value=f"*{title}*", inline=True)
        embed.add_field(name="Tower Stats", value=f"**Tower Height:** {height}ft\n*{flavor}*")
        await channel.send(embed=embed)
    update_height_timestamp(user_id)
    save_data()

@bot.event
async def on_ready():
    if not hasattr(bot, 'start_time'):
        bot.start_time = time.time()
    print(f'🏰 Tower of Power Bot is online as {bot.user}')
    print(f'Connected to {len(bot.guilds)} server(s)')
    if not auto_save.is_running():
        auto_save.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await add_xp(message.author, 1, message.channel)
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    await add_xp(user, 2, reaction.message.channel)

@bot.command(name='ping')
async def ping_command(ctx):
    latency = round(bot.latency * 1000)
    uptime = time.time() - bot.start_time if hasattr(bot, 'start_time') else 0
    uptime_str = f"{int(uptime // 60)}m"
    embed = discord.Embed(title="🏓 Ping", description=f"Latency: {latency}ms\nUptime: {uptime_str}", color=0x00FF7F)
    await ctx.send(embed=embed)

@bot.command(name='faq')
async def help_command(ctx):
    embed = discord.Embed(
        title="🏰 Tower of Power - Help",
        description="Build the tallest tower through activity and strategic duels!",
        color=0x7289DA
    )
    embed.add_field(
        name="📈 Gaining XP & Height",
        value="• **Chat messages:** +1 XP\n• **Reactions:** +2 XP\n• **Level up:** +3ft per level",
        inline=False
    )
    embed.add_field(
        name="🎮 Commands",
        value="• `!towerstats`\n• `!leaderboard`\n• `!challenge @user`\n• `!resetme`\n• `!ping`",
        inline=False
    )
    await ctx.send(embed=embed)

# More commands like !towerstats, !leaderboard, !challenge, etc. are assumed to be included here too