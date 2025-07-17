
import discord
import json
import os
import random
import time
from discord.ext import commands, tasks
from tinydb import TinyDB, Query

# Load token from environment
TOKEN = os.getenv('DISCORD_BOT_TOKEN') or os.getenv('TOKEN') or 'YOUR_BOT_TOKEN_HERE'

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.members = True

# Set up bot
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Database
db = TinyDB("tower_data.json")
user_table = db.table("users")
user_data = {}

# Load/save functions
def load_data():
    global user_data
    user_data = {}
    for item in user_table.all():
        user_data[str(item.doc_id)] = item

def save_data():
    user_table.truncate()
    for uid, data in user_data.items():
        user_table.insert(data)

# XP logic
BASE_XP = 50
MAX_XP_PER_LEVEL = 500

def calculate_level(xp):
    total_xp = 0
    level = 1
    while True:
        required = min(BASE_XP + (level - 1) * 50, MAX_XP_PER_LEVEL)
        if xp < total_xp + required:
            break
        total_xp += required
        level += 1
    return level

def xp_needed_for_next_level(xp):
    level = calculate_level(xp)
    total_xp = 0
    for i in range(1, level):
        total_xp += min(BASE_XP + (i - 1) * 50, MAX_XP_PER_LEVEL)
    next_level_xp = min(BASE_XP + (level - 1) * 50, MAX_XP_PER_LEVEL)
    return (total_xp + next_level_xp) - xp

def calculate_height(uid):
    user = user_data.get(uid, {})
    level = calculate_level(user.get("xp", 0))
    return 5 + (level - 1) * 3 + user.get("bonus_height", 0)

def get_title(level):
    titles = ["Bricklayer", "Seeker", "Architect", "Foreman", "Erectomancer", "Sky Grazer", "Cloud Splitter", "Spire Slinger", "Wand Waver", "Wizard of Girth"]
    return titles[level - 1] if level <= len(titles) else f"Ascendant Lv.{level}"

def get_flavor(height):
    if height < 15:
        return "Just a stump in the dirt."
    elif height < 50:
        return "Casting a respectable shadow."
    elif height < 100:
        return "Locals whisper of your structure."
    elif height < 200:
        return "Your tower pierces the skies."
    else:
        return "Your tower now speaks to the gods."

def init_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "xp": 0,
            "bonus_height": 0,
            "wins": 0,
            "losses": 0,
            "timestamp": time.time()
        }

# Auto-save
@tasks.loop(minutes=5)
async def autosave():
    save_data()

# XP gain
async def add_xp(user, amount, channel):
    uid = str(user.id)
    init_user(uid)
    before_level = calculate_level(user_data[uid]["xp"])
    user_data[uid]["xp"] += amount
    after_level = calculate_level(user_data[uid]["xp"])
    if after_level > before_level:
        target_channel = discord.utils.get(channel.guild.text_channels, name="tower-of-power")
        if target_channel:
            embed = discord.Embed(title="🏗️ Level Up!", color=0x8e44ad)
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="New Level", value=str(after_level), inline=True)
            embed.add_field(name="New Height", value=f"{calculate_height(uid)}ft", inline=False)
            await target_channel.send(embed=embed)
    save_data()

# Events
@bot.event
async def on_ready():
    load_data()
    autosave.start()
    print(f"Bot online as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await add_xp(message.author, 5, message.channel)
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    await add_xp(user, 2, reaction.message.channel)

# Commands
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def faq(ctx):
    embed = discord.Embed(title="📜 Tower of Power FAQ", color=0x7289da)
    embed.add_field(name="How to grow?", value="• Chat (+5 XP)
• React (+2 XP)
• Level up = +3ft
• Win duels = steal height", inline=False)
    embed.add_field(name="Duels", value="• 40% attacker wins
• 40% defender wins
• 20% Tower wins
• Loser loses 10% height", inline=False)
    embed.add_field(name="Commands", value="!ping, !faq, !towerstats, !leaderboard, !challenge @user, !resetme", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def towerstats(ctx, user: discord.Member = None):
    target = user or ctx.author
    uid = str(target.id)
    init_user(uid)
    stats = user_data[uid]
    level = calculate_level(stats["xp"])
    height = calculate_height(uid)
    title = get_title(level)
    embed = discord.Embed(title=f"🧱 {target.display_name}'s Tower", color=0x3498db)
    embed.add_field(name="Level", value=level)
    embed.add_field(name="XP", value=f'{stats["xp"]} / +{xp_needed_for_next_level(stats["xp"])}')
    embed.add_field(name="Height", value=f"{height} ft")
    embed.add_field(name="Title", value=title)
    embed.add_field(name="Wins", value=stats.get("wins", 0))
    embed.add_field(name="Losses", value=stats.get("losses", 0))
    embed.add_field(name="Essence", value=get_flavor(height), inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    def sort_key(uid):
        height = calculate_height(uid)
        timestamp = user_data[uid].get("timestamp", float('inf'))
        return (-height, timestamp)

    top = sorted(user_data.keys(), key=sort_key)[:10]
    embed = discord.Embed(title="🏆 Tower Leaderboard", color=0xffd700)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    for i, uid in enumerate(top):
        user = await bot.fetch_user(int(uid))
        height = calculate_height(uid)
        level = calculate_level(user_data[uid]["xp"])
        embed.add_field(name=f"{medals[i]} {user.display_name}", value=f"{height}ft — Lv.{level}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def resetme(ctx):
    uid = str(ctx.author.id)
    user_data[uid] = {
        "xp": 0,
        "bonus_height": 0,
        "wins": 0,
        "losses": 0,
        "timestamp": time.time()
    }
    save_data()
    await ctx.send("🔄 Your tower has been humbled and reset to 5ft.")

@bot.command()
async def challenge(ctx, target: discord.Member):
    attacker = ctx.author
    defender = target
    attacker_id = str(attacker.id)
    defender_id = str(defender.id)
    init_user(attacker_id)
    init_user(defender_id)

    if attacker_id == defender_id:
        await ctx.send("❌ You can't duel yourself.")
        return

    attacker_height = calculate_height(attacker_id)
    defender_height = calculate_height(defender_id)

    # Get sorted leaderboard
    def sort_key(uid):
        height = calculate_height(uid)
        timestamp = user_data[uid].get("timestamp", float('inf'))
        return (-height, timestamp)

    sorted_users = sorted(user_data.keys(), key=sort_key)
    first = sorted_users[0] if len(sorted_users) > 0 else None
    second = sorted_users[1] if len(sorted_users) > 1 else None
    third = sorted_users[2] if len(sorted_users) > 2 else None

    # Duel rules
    if (attacker_id == second and defender_id == first) or        (attacker_id == third and defender_id == second) or        (defender_id == third) or        (attacker_height >= defender_height):
        outcome = random.randint(1, 100)
        if outcome <= 40:
            winner, loser = attacker, defender
        elif outcome <= 80:
            winner, loser = defender, attacker
        else:
            winner, loser = None, attacker if random.choice([True, False]) else defender  # Tower wins

        loser_id = str(loser.id)
        stolen = round(calculate_height(loser_id) * 0.1)

        if winner:
            winner_id = str(winner.id)
            init_user(winner_id)
            user_data[winner_id]["bonus_height"] += stolen
            user_data[winner_id]["wins"] += 1
            result = f"**{winner.display_name}** absorbs {stolen}ft from **{loser.display_name}**!"
        else:
            result = f"🏰 The Tower itself strikes! **{loser.display_name}** loses {stolen}ft to the ether!"

        user_data[loser_id]["bonus_height"] = max(0, user_data[loser_id]["bonus_height"] - stolen)
        user_data[loser_id]["losses"] += 1
        save_data()

        embed = discord.Embed(title="⚔️ Tower Duel", color=0xe74c3c)
        embed.add_field(name="Outcome", value=result)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Invalid challenge. You can only challenge equal/lower towers (except 3rd/2nd/1st rule).")

# Start bot
if TOKEN == 'YOUR_BOT_TOKEN_HERE':
    print("❌ Missing Discord token.")
else:
    bot.run(TOKEN)
