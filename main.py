
import discord
from discord.ext import commands
import os
import random
import asyncio
from datetime import datetime

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
        embed = discord.Embed(
            title="📈 Tower Level Up!",
            description=f"**{message.author.display_name}** has reached **Level {user['level']}**!\n\nTheir tower now stands **{user['height']}ft tall**.\nTitle: *{get_level_title(user['level'])}*",
            color=discord.Color.purple()
        )
        await message.channel.send(embed=embed)
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
    embed = discord.Embed(
        title=f"📊 {ctx.author.display_name}'s Tower Stats",
        description=f"**Level:** {user['level']}\n**XP:** {user['xp']}\n**Height:** {user['height']}ft\n**Title:** {get_level_title(user['level'])}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    update_leaderboard()
    embed = discord.Embed(
        title="🏆 Tower Leaderboard",
        color=discord.Color.gold(),
        description=""
    )
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, data) in enumerate(leaderboard[:10]):
        user = await bot.fetch_user(user_id)
        medal = medals[i] if i < 3 else f"{i+1}️⃣"
        embed.description += f"{medal} {user.display_name} — {data['height']}ft (Lv. {data['level']})\n"
    embed.set_footer(text=f"Updated just now • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    await ctx.send(embed=embed)

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
        embed = discord.Embed(title="⚔️ Tower Duel Results", color=discord.Color.green())
        embed.add_field(name="Victory!", value=f"{challenger.display_name} has defeated {target.display_name}!", inline=False)
        embed.add_field(name="Spoils of War", value=f"{challenger.display_name} absorbs {gained}ft and rises even higher.", inline=False)
        embed.add_field(name="The Fallen", value=f"{target.display_name} returns to a humble {get_base_height(t_data['level'])}ft base but keeps their Level {t_data['level']} experience 😔", inline=False)
        await ctx.send(embed=embed)
    elif outcome == "target":
        gained = max(0, c_data["height"] - get_base_height(c_data["level"]))
        t_data["height"] += gained
        c_data["height"] = get_base_height(c_data["level"])
        embed = discord.Embed(title="⚔️ Tower Duel Results", color=discord.Color.red())
        embed.add_field(name="Reversal!", value=f"{target.display_name} has turned the tables and defeated {challenger.display_name}!", inline=False)
        embed.add_field(name="Spoils of War", value=f"{target.display_name} absorbs {gained}ft and grows even stronger.", inline=False)
        embed.add_field(name="The Fallen", value=f"{challenger.display_name} returns to a humble {get_base_height(c_data['level'])}ft base but keeps their Level {c_data['level']} experience 😔", inline=False)
        await ctx.send(embed=embed)
    else:
        for member in [challenger, target]:
            data = user_data[member.id]
            loss = int((data["height"] * 0.1) + 0.999)
            data["height"] = max(get_base_height(data["level"]), data["height"] - loss)
        flavor_texts = [
            "Your tower trembles in shame...",
            "A mysterious wind rattles your shaft.",
            "The stones weep quietly.",
            "Your wizardhood feels... smaller.",
            "The Tower laughs in ancient tongues."
        ]
        embed = discord.Embed(
            title="🗼 The Tower Strikes!",
            description="Neither fighter proved worthy...\n\nBoth duelers lose 10% of their tower height.\n" + random.choice(flavor_texts),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Wizards beware — the Tower is always watching.")
        await ctx.send(embed=embed)

    update_leaderboard()

@bot.command()
async def faq(ctx):
    await ctx.send("Welcome to Tower of Power! Message or react to grow your tower. Duel others to absorb their height. Levels increase your tower. Anyone can challenge 3rd place, and 2nd place can challenge 1st. Use !duel @user and !towerstats to play.")
bot.run(MTM4ODc0MDU4MDg0NjIwNzAwNg.GYBZgs.5rXoSoS_XuFf_pxI5LsNCQbYzRmGCj9oVaQva0)
