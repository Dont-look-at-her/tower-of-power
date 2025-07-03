
import discord
from discord.ext import commands
import os
import random
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_data = {}
leaderboard = []

LEVEL_XP_BASE = 50
HEIGHT_PER_LEVEL = 3

def get_level_title(lvl):
    return f"Ascender Lv.{lvl}"

def get_base_height(level):
    return 5 + (level - 1) * HEIGHT_PER_LEVEL

def get_required_xp(level):
    return min(500, LEVEL_XP_BASE + (level - 1) * 50)

def update_leaderboard():
    global leaderboard
    leaderboard = sorted(user_data.items(), key=lambda x: (-x[1]['height'], x[1]['timestamp']))

def ensure_user(user):
    if user.id not in user_data:
        user_data[user.id] = {
            "xp": 0,
            "level": 1,
            "height": 5,
            "timestamp": asyncio.get_event_loop().time()
        }

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    update_leaderboard()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    ensure_user(message.author)
    user = user_data[message.author.id]
    user["xp"] += 1
    required_xp = get_required_xp(user["level"] + 1)
    if user["xp"] >= required_xp:
        user["level"] += 1
        user["height"] = get_base_height(user["level"])
        await message.channel.send(f"🧙‍♂️ {message.author.display_name} leveled up to Level {user['level']}! Tower Height: {user['height']}ft — {get_level_title(user['level'])}")
    update_leaderboard()
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    ensure_user(user)
    user_data[user.id]["xp"] += 1
    update_leaderboard()

@bot.command()
async def towerstats(ctx):
    ensure_user(ctx.author)
    user = user_data[ctx.author.id]
    await ctx.send(f"🧙‍♂️ {ctx.author.display_name} — Level: {user['level']}, XP: {user['xp']}, Tower Height: {user['height']}ft")

@bot.command()
async def duel(ctx, target: discord.Member):
    challenger = ctx.author
    if target.bot or challenger == target:
        await ctx.send("You can't duel that target.")
        return

    ensure_user(challenger)
    ensure_user(target)

    c_data = user_data[challenger.id]
    t_data = user_data[target.id]

    outcome = random.choices(["challenger", "target", "tower"], weights=[30, 30, 40])[0]

    if outcome == "challenger":
        gained = max(0, t_data["height"] - get_base_height(t_data["level"]))
        c_data["height"] += gained
        t_data["height"] = get_base_height(t_data["level"])
        await ctx.send(f"⚔️ {challenger.display_name} has defeated {target.display_name} and absorbed {gained}ft of tower!")
    elif outcome == "target":
        gained = max(0, c_data["height"] - get_base_height(c_data["level"]))
        t_data["height"] += gained
        c_data["height"] = get_base_height(c_data["level"])
        await ctx.send(f"⚔️ {target.display_name} has turned the tables and absorbed {gained}ft from {challenger.display_name}!")
    else:
        for member in [challenger, target]:
            data = user_data[member.id]
            loss = int((data["height"] * 0.1) + 0.999)
            data["height"] = max(get_base_height(data["level"]), data["height"] - loss)
        await ctx.send("🗼 The Tower strikes! Both duelers lose 10% of their tower height.")

    update_leaderboard()

@bot.command()
async def faq(ctx):
    await ctx.send("Welcome to Tower of Power! Message or react to grow your tower. Duel others to absorb their height. Levels increase your tower. Anyone can challenge 3rd place, and 2nd place can challenge 1st. Use !duel @user and !towerstats to play.")

bot.run(TOKEN)
