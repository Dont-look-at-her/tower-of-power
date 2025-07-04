
import discord
from discord.ext import commands, tasks
import os
import random
import asyncio
from datetime import datetime

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Data store for player stats
player_data = {}

# XP and Level System Constants
BASE_XP = 50
MAX_XP_PER_LEVEL = 500
XP_PER_MESSAGE = 5
XP_PER_REACTION = 2

# Titles per level (some sample levels for flavor)
titles = [
    ("🧱 Bricklayer", "Your tower has a base, but it’s giving patio vibes."),
    ("🧙‍♂️ Seeker", "Your tower casts a slightly concerning shadow."),
    ("🏰 Apprentice Architect", "It’s standing… barely."),
    ("🗼 Tower Tinkerer", "You’ve added your first gargoyle. It farts."),
    ("🔮 Ascending Adept", "Something magical stirs in your foundation."),
    ("⚙️ Erectomancer", "It rises… mysteriously."),
    ("🔥 Spire Forger", "People are starting to notice your spire."),
    ("🌩️ Height Enthusiast", "You dream in altitude."),
    ("🌌 Tower Whisperer", "The tower speaks back sometimes."),
    ("💀 Girth Lord", "Your tower is feared in tavern tales.")
]

def get_title(level):
    if level < len(titles):
        return titles[level]
    return (f"🌟 Sky Seeker Lv.{level}", "The clouds part as you rise ever higher.")

def calculate_xp_needed(level):
    return min(BASE_XP + level * 50, MAX_XP_PER_LEVEL)

def get_leaderboard():
    sorted_players = sorted(player_data.items(), key=lambda x: (-x[1]['height'], x[1]['first_reach_time']))
    leaderboard = []
    for i, (user_id, data) in enumerate(sorted_players[:10], 1):
        leaderboard.append((i, user_id, data))
    return leaderboard

@bot.event
async def on_ready():
    print(f"Bot is ready as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    now = datetime.utcnow()

    if user_id not in player_data:
        player_data[user_id] = {
            'xp': 0,
            'level': 1,
            'height': 5,
            'first_reach_time': now
        }

    data = player_data[user_id]
    data['xp'] += XP_PER_MESSAGE

    leveled_up = False
    while data['xp'] >= min(data['level'] * 50, 500):
        data['xp'] -= min(data['level'] * 50, 500)
        data['level'] += 1
        data['height'] += 3
        data['first_reach_time'] = now
        title, flavor = get_title(data['level'])

        embed = discord.Embed(
            title=f"🔮 {message.author.display_name} has leveled up!",
            description=f"**{title} [Lv. {data['level']}] — Tower Height: {data['height']}ft**\n*{flavor}*",
            color=0x9b59b6
        )
        await message.channel.send(embed=embed)
        leveled_up = True

    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    user_id = str(user.id)
    now = datetime.utcnow()

    if user_id not in player_data:
        player_data[user_id] = {
            'xp': 0,
            'level': 1,
            'height': 5,
            'first_reach_time': now
        }

    data = player_data[user_id]
    data['xp'] += XP_PER_REACTION

@bot.command()
async def towerstats(ctx, member: discord.Member = None):
    user = member or ctx.author
    user_id = str(user.id)

    if user_id not in player_data:
        await ctx.send(f"{user.display_name} hasn't started building their tower yet! Send a message to begin.")
        return

    data = player_data[user_id]
    level = data['level']
    current_xp = data['xp']
    height = data['height']
    xp_needed = min(level * 50, 500)

    embed = discord.Embed(
        title=f"{user.display_name}'s Tower Stats",
        description=f"**Level:** {level}\n**XP:** {current_xp}/{xp_needed}\n**Height:** {height}ft",
        color=0x3498db
    )
    await ctx.send(embed=embed)

@bot.command()
async def duel(ctx, opponent: discord.Member):
    challenger_id = str(ctx.author.id)
    opponent_id = str(opponent.id)

    if challenger_id == opponent_id:
        await ctx.send("You can't duel yourself, tower weirdo.")
        return

    if challenger_id not in player_data or opponent_id not in player_data:
        await ctx.send("Both duelists must have towers. Send some messages first!")
        return

    challenger = player_data[challenger_id]
    challenged = player_data[opponent_id]

    leaderboard = get_leaderboard()
    top_users = [entry[1] for entry in leaderboard]
    challenger_rank = top_users.index(challenger_id) + 1 if challenger_id in top_users else None
    opponent_rank = top_users.index(opponent_id) + 1 if opponent_id in top_users else None

    # Duel eligibility logic
    valid_duel = False

    if challenger['height'] >= challenged['height']:
        valid_duel = True
    elif opponent_rank == 3:
        valid_duel = True
    elif challenger_rank == 3 and opponent_rank == 2:
        valid_duel = True
    elif challenger_rank == 2 and opponent_rank == 1:
        valid_duel = True

    if not valid_duel:
        await ctx.send("You can only duel someone with an equal or smaller tower — unless challenging the top 3 under special rules.")
        return

    # Duel outcome
    winner, loser = (challenger, challenged) if random.random() < 0.5 else (challenged, challenger)
    winner_id, loser_id = (challenger_id, opponent_id) if winner == challenger else (opponent_id, challenger_id)

    stolen_height = max(1, round(loser['height'] * 0.1))
    winner['height'] += stolen_height
    loser['height'] = max(5, loser['height'] - stolen_height)  # Only reduce height, not XP/level

    if winner_id == str(ctx.author.id):
        color = 0x2ecc71
        desc = f"{ctx.author.display_name} has defeated {opponent.display_name} and stolen {stolen_height}ft of tower!"
    else:
        color = 0xe74c3c
        desc = f"{ctx.author.display_name} was defeated by {opponent.display_name}! The Tower has claimed them..."

    embed = discord.Embed(
        title="⚔️ Duel Result",
        description=desc,
        color=color
    )
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    lb = get_leaderboard()
    embed = discord.Embed(title="🏆 Tower of Power Leaderboard", color=0xf1c40f)

    for i, (rank, user_id, data) in enumerate(lb, 1):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(
            name=f"{i}. {user.display_name}",
            value=f"Height: {data['height']}ft — Level {data['level']}",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command()
async def faq(ctx):
    embed = discord.Embed(title="📜 Tower of Power — FAQ & Commands", color=0x95a5a6)
    embed.add_field(name="!towerstats", value="View your current tower level, XP, and height.", inline=False)
    embed.add_field(name="!duel @user", value="Challenge someone with an equal or smaller tower (or 3rd place!).", inline=False)
    embed.add_field(name="!leaderboard", value="See the top 10 tallest towers.", inline=False)
    embed.add_field(name="Leveling", value="Gain XP by chatting or reacting. Level up to grow your tower!", inline=False)
    embed.set_footer(text="Behold the tower… and fear its ascent.")
    await ctx.send(embed=embed)

bot.run(os.getenv("DISCORD_TOKEN"))
