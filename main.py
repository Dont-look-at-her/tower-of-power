
import discord
from discord.ext import commands, tasks
import os
import random
import asyncio
from datetime import datetime
from tinydb import TinyDB, Query

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

db = TinyDB('player_data.json')
Player = Query()

BASE_XP = 50
MAX_XP_PER_LEVEL = 500
XP_PER_MESSAGE = 5
XP_PER_REACTION = 2
HEIGHT_PER_LEVEL = 3

LEVEL_CHANNEL_NAME = "tower-of-power"

titles = [
    "🧱 Bricklayer", "🧙‍♂️ Seeker", "🏗️ Scaffold Scout", "📏 Ruler Whisperer",
    "🔮 Erectomancer", "🏰 Peak Dreamer", "🌆 Girth Lord", "🪜 Ascensionist",
    "💈 Spiral Conqueror", "💜 Wizard of Wood", "🌀 Infinity Riser"
]

def get_level_xp(level):
    return min(BASE_XP * level, MAX_XP_PER_LEVEL)

def get_title(level):
    return titles[level - 1] if level - 1 < len(titles) else f"🔝 Tower Sage Lv.{level}"

def get_flavor(height):
    if height < 10:
        return "Still just a bump in the ground."
    elif height < 20:
        return "People start tripping over your foundation."
    elif height < 30:
        return "Your tower casts a slightly concerning shadow."
    elif height < 50:
        return "Birds are nesting somewhere up there."
    elif height < 75:
        return "Clouds pause to admire your structure."
    elif height < 100:
        return "Even planes give you a respectful fly-around."
    else:
        return "A monument feared by gods and zoning boards alike."

def get_player(user_id):
    user = db.get(Player.id == user_id)
    if not user:
        user = {
            "id": user_id,
            "xp": 0,
            "level": 1,
            "height": 5,
            "last_xp": str(datetime.utcnow()),
            "wins": 0,
            "losses": 0
        }
        db.insert(user)
    return user

def save_player(user):
    db.upsert(user, Player.id == user["id"])

def update_height_timestamp(user_id):
    user = get_player(user_id)
    user["last_xp"] = str(datetime.utcnow())
    save_player(user)

def try_level_up(user_id):
    user = get_player(user_id)
    level_up = False
    while user["xp"] >= get_level_xp(user["level"]):
        user["xp"] -= get_level_xp(user["level"])
        user["level"] += 1
        user["height"] += HEIGHT_PER_LEVEL
        level_up = True
    save_player(user)
    return level_up

async def send_levelup_message(member):
    channel = discord.utils.get(member.guild.text_channels, name=LEVEL_CHANNEL_NAME)
    if channel:
        user = get_player(member.id)
        embed = discord.Embed(
            title=f"🎉 {member.display_name} leveled up!",
            description=f"**Level {user['level']} – {get_title(user['level'])}**\n🏯 Tower Height: {user['height']}ft",
            color=0x9370DB
        )
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Tower of Power online as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user = get_player(message.author.id)
    user["xp"] += XP_PER_MESSAGE
    save_player(user)

    if try_level_up(message.author.id):
        await send_levelup_message(message.author)

    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    member = reaction.message.guild.get_member(user.id)
    if member:
        user_data = get_player(member.id)
        user_data["xp"] += XP_PER_REACTION
        save_player(user_data)
        if try_level_up(member.id):
            await send_levelup_message(member)

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

@bot.command()
async def faq(ctx):
    embed = discord.Embed(title="🧙 Tower of Power — FAQ", color=0x9370DB)
    embed.add_field(name="How to grow?", value="• Chat (+5 XP)\n• React (+2 XP)\n• Level up = +3ft\n• Win duels = steal height", inline=False)
    embed.add_field(name="Commands", value="!towerstats, !leaderboard, !duel @user, !resetme, !faq", inline=False)
    embed.add_field(name="Special Rules", value="• 2nd can duel 1st\n• 3rd can duel 2nd\n• Anyone can duel 3rd\n• Otherwise, duel equal/smaller towers", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def towerstats(ctx):
    user = get_player(ctx.author.id)
    xp_needed = get_level_xp(user["level"])
    embed = discord.Embed(title=f"🏗️ {ctx.author.display_name}'s Tower", color=0x00BFFF)
    embed.add_field(name="New Title", value=f"**{get_title(user['level'])}**", inline=True)
    embed.add_field(name="Tower Stats", value=f"**Tower Height:** {user['height']}ft\n*{get_flavor(user['height'])}*", inline=False)
    embed.add_field(name="Level Info", value=f"Level {user['level']} — {user['xp']}/{xp_needed} XP", inline=True)
    embed.add_field(name="Duels", value=f"Wins: {user['wins']} | Losses: {user['losses']}", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='duel')
async def duel(ctx, opponent: discord.Member):
    attacker_id = str(ctx.author.id)
    defender_id = str(opponent.id)

    if attacker_id not in player_data or defender_id not in player_data:
        await ctx.send("Both players must have towers to duel.")
        return

    attacker = player_data[attacker_id]
    defender = player_data[defender_id]

    attacker_height = attacker.get("height", 5)
    defender_height = defender.get("height", 5)

    # Duel eligibility check
    leaderboard = sorted(player_data.items(), key=lambda x: (-x[1]["height"], x[1].get("timestamp", "")))
    attacker_rank = next((i for i, (uid, _) in enumerate(leaderboard, 1) if uid == attacker_id), None)
    defender_rank = next((i for i, (uid, _) in enumerate(leaderboard, 1) if uid == defender_id), None)

    if (
        defender_height > attacker_height
        and not (defender_rank == 3 or attacker_rank == 3 and defender_rank == 2)
    ):
        await ctx.send("You can only challenge someone with equal or lower height — unless you're 3rd place or they're 2nd.")
        return

    outcome = random.choices(["attacker", "defender", "tower"], weights=[0.4, 0.4, 0.2])[0]

    loser = winner = None
    if outcome == "attacker":
        winner, loser = attacker, defender
        winner_id, loser_id = attacker_id, defender_id
    elif outcome == "defender":
        winner, loser = defender, attacker
        winner_id, loser_id = defender_id, attacker_id
    else:
        # Tower wins
        winner = {"name": "The Tower"}
        loser = attacker
        loser_id = attacker_id
        loss = round(loser["height"] * 0.10)
        loser["height"] -= loss
        loser["losses"] = loser.get("losses", 0) + 1
        await ctx.send(f"🗼 The Tower has spoken... {ctx.author.display_name} was struck down and lost {loss}ft!")
        save_data()
        return

    transfer = round(loser["height"] * 0.10)
    winner["height"] += transfer
    loser["height"] -= transfer
    winner["wins"] = winner.get("wins", 0) + 1
    loser["losses"] = loser.get("losses", 0) + 1

    await ctx.send(f"{ctx.guild.get_member(int(winner_id)).mention} defeated {ctx.guild.get_member(int(loser_id)).mention} and stole {transfer}ft!")

    save_data()

@bot.command(name='duel')
async def duel(ctx, opponent: discord.Member):
    attacker_id = str(ctx.author.id)
    defender_id = str(opponent.id)

    if attacker_id not in player_data or defender_id not in player_data:
        await ctx.send("Both players must have towers to duel.")
        return

    attacker = player_data[attacker_id]
    defender = player_data[defender_id]

    attacker_height = attacker.get("height", 5)
    defender_height = defender.get("height", 5)

    # Duel eligibility check
    leaderboard = sorted(player_data.items(), key=lambda x: (-x[1]["height"], x[1].get("timestamp", "")))
    attacker_rank = next((i for i, (uid, _) in enumerate(leaderboard, 1) if uid == attacker_id), None)
    defender_rank = next((i for i, (uid, _) in enumerate(leaderboard, 1) if uid == defender_id), None)

    if (
        defender_height > attacker_height
        and not (defender_rank == 3 or attacker_rank == 3 and defender_rank == 2)
    ):
        await ctx.send("You can only challenge someone with equal or lower height — unless you're 3rd place or they're 2nd.")
        return

    outcome = random.choices(["attacker", "defender", "tower"], weights=[0.4, 0.4, 0.2])[0]

    loser = winner = None
    if outcome == "attacker":
        winner, loser = attacker, defender
        winner_id, loser_id = attacker_id, defender_id
    elif outcome == "defender":
        winner, loser = defender, attacker
        winner_id, loser_id = defender_id, attacker_id
    else:
        # Tower wins
        winner = {"name": "The Tower"}
        loser = attacker
        loser_id = attacker_id
        loss = round(loser["height"] * 0.10)
        loser["height"] -= loss
        loser["losses"] = loser.get("losses", 0) + 1
        await ctx.send(f"🗼 The Tower has spoken... {ctx.author.display_name} was struck down and lost {loss}ft!")
        save_data()
        return

    transfer = round(loser["height"] * 0.10)
    winner["height"] += transfer
    loser["height"] -= transfer
    winner["wins"] = winner.get("wins", 0) + 1
    loser["losses"] = loser.get("losses", 0) + 1

    await ctx.send(f"{ctx.guild.get_member(int(winner_id)).mention} defeated {ctx.guild.get_member(int(loser_id)).mention} and stole {transfer}ft!")

    save_data()

@bot.command()
async def resetme(ctx):
    db.remove(Player.id == ctx.author.id)
    await ctx.send("🔁 Your tower has been reset to 5ft. Time to rise again!")

# Additional commands like !duel and !leaderboard can be added here with the same updated structure

bot.run(TOKEN)
