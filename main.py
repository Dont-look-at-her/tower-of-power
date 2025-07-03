import discord
from discord.ext import commands
import os
import random
import asyncio
from datetime import datetime

# Intents setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

# Load token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Create bot instance
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

    user = message.author
    user_id = str(user.id)

    # Register user if not exists
    if user_id not in tower_data:
        tower_data[user_id] = {"level": 1, "xp": 0, "height": 10}

    user_data = tower_data[user_id]
    user_data["xp"] += 5  # 💥 +5 XP per message

    await handle_level_up(user, user_data, message.channel)

    # Save data
    with open("tower_data.json", "w") as f:
        json.dump(tower_data, f, indent=2)

    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    user_id = str(user.id)

    if user_id not in tower_data:
        tower_data[user_id] = {"level": 1, "xp": 0, "height": 10}

    user_data = tower_data[user_id]
    user_data["xp"] += 3  # ✨ +3 XP per reaction

    await handle_level_up(user, user_data, reaction.message.channel)

    with open("tower_data.json", "w") as f:
        json.dump(tower_data, f, indent=2)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    ensure_user(user)
    user_data[user.id]["xp"] += 1
    update_leaderboard()

tower_data = {}
import os
import json

# Load tower_data from file if it exists
if os.path.exists("tower_data.json"):
    with open("tower_data.json", "r") as f:
        tower_data = json.load(f)

@bot.command(name='towerstats')
async def tower_stats(ctx, member: discord.Member = None):
    user = member or ctx.author  # Use mentioned member or default to author
    user_id = str(user.id)

    # Check if the user is registered
    if user_id not in tower_data:
        await ctx.send(f"{user.display_name} hasn't built a tower yet.")
        return

    user_data = tower_data[user_id]
    level = user_data.get("level", 1)
    xp = user_data.get("xp", 0)
    height = user_data.get("height", 5)

    title = get_title_for_level(level)
    flavor = get_flavor_for_level(level)

    embed = discord.Embed(
        title=f"{user.display_name}'s Tower Stats",
        description=f"🧙‍♂️ **{title} [Lv. {level}]** — Tower Height: **{height}ft**\n"
                    f"XP: `{xp}`\n\n*“{flavor}”*",
        color=0x9370DB  # Purple
    )
    embed.set_footer(text="The Tower watches... always.")
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

@bot.command(name="duel")
async def duel(ctx, opponent: discord.Member):
    attacker = ctx.author
    if opponent == attacker:
        await ctx.send("You cannot duel yourself, fool.")
        return

    attacker_id = str(attacker.id)
    opponent_id = str(opponent.id)

    # Register users if needed
    for user_id in [attacker_id, opponent_id]:
        if user_id not in tower_data:
            tower_data[user_id] = {"level": 1, "xp": 0, "height": 10}

    attacker_data = tower_data[attacker_id]
    opponent_data = tower_data[opponent_id]

    if attacker_data["height"] < opponent_data["height"] and opponent_data["height"] > 10:
        await ctx.send(f"{attacker.display_name}, your tower is too small to challenge {opponent.display_name}.")
        return

    # 30/30/40 outcome logic
    outcome = random.choices(
        population=["attacker", "opponent", "tower"],
        weights=[30, 30, 40],
        k=1
    )[0]

    if outcome == "tower":
        embed = discord.Embed(
            title="🌩 The Tower Has Spoken...",
            description=(
                f"Both **{attacker.display_name}** and **{opponent.display_name}** lose.\n"
                "The Tower demands tribute. Their towers crumble... and the mystery deepens. 🗿"
            ),
            color=0xFFD700  # Gold
        )
        attacker_data["height"] = 10
        opponent_data["height"] = 10

    else:
        winner = attacker if outcome == "attacker" else opponent
        loser = opponent if outcome == "attacker" else attacker

        winner_id = str(winner.id)
        loser_id = str(loser.id)
        winner_data = tower_data[winner_id]
        loser_data = tower_data[loser_id]

        stolen = round(loser_data["height"] * 0.10)
        winner_data["height"] += stolen
        loser_data["height"] = 10

        winner_data["xp"] += 5  # 🏆 +5 XP for winning duel
await handle_level_up(winner, winner_data, ctx.channel)

        embed = discord.Embed(
            title=f"⚔️ Duel Result: {winner.display_name} Wins!",
            description=(
                f"🏆 **{winner.display_name}** absorbs **{stolen}ft** of tower energy!\n"
                f"⚠️ **{loser.display_name}**'s tower crumbles down to **10ft**.\n"
                f"🧱 {winner.display_name}'s tower now stands at **{winner_data['height']}ft**!"
            ),
            color=0x00FF00
        )

    # Save changes
    with open("tower_data.json", "w") as f:
        json.dump(tower_data, f, indent=2)

    await ctx.send(embed=embed)

    update_leaderboard()

update_leaderboard()

@bot.command()
async def handle_level_up(user, user_data, channel):
    level = user_data["level"]
    xp_needed = min(50 + (level - 1) * 50, 500)

    if user_data["xp"] >= xp_needed:
        user_data["xp"] -= xp_needed
        user_data["level"] += 1
        user_data["height"] += 3

        title = get_title_for_level(user_data["level"])
        flavor = get_flavor_for_level(user_data["level"])

        embed = discord.Embed(  # ✅ Fixed indent here
        title=f"🧙‍♂️ {user.display_name} Leveled Up!",
            description=f"**{title} [Lv. {user_data['level']}]** — Tower Height: **{user_data['height']}ft**\n"
                        f"XP reset to `{user_data['xp']}`\n\n*“{flavor}”*",
            color=0x9370DB
        )
        await channel.send(embed=embed)

bot.run(DISCORD_TOKEN)
