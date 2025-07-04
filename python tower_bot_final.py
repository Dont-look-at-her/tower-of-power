S
import discord
from discord.ext import commands
import os
import json
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

# Global data holders
tower_data = {}
leaderboard = []

# Load tower data from file
if os.path.exists("tower_data.json"):
    with open("tower_data.json", "r") as f:
        tower_data = json.load(f)

# Utility functions
def get_title_for_level(level):
    return f"Ascender Lv.{level}"

def get_flavor_for_level(level):
    return f"Your tower hums with strange energy at level {level}..."

def get_required_xp(level):
    return min(500, 50 + (level - 1) * 50)

def update_leaderboard():
    global leaderboard
    leaderboard = sorted(tower_data.items(), key=lambda x: (-x[1]['height'], x[1].get('timestamp', 0)))

async def handle_level_up(user, user_data, channel):
    level = user_data["level"]
    xp_needed = get_required_xp(level)

    if user_data["xp"] >= xp_needed:
        user_data["xp"] -= xp_needed
        user_data["level"] += 1
        user_data["height"] += 3

        title = get_title_for_level(user_data["level"])
        flavor = get_flavor_for_level(user_data["level"])

        embed = discord.Embed(
            title=f"🧙‍♂️ {user.display_name} Leveled Up!",
            description=(
                f"**{title} [Lv. {user_data['level']}]** — Tower Height: **{user_data['height']}ft**\n"
                f"XP reset to `{user_data['xp']}`\n\n*“{flavor}”*"
            ),
            color=0x9370DB
        )
        await channel.send(embed=embed)

# Events
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

    if user_id not in tower_data:
        tower_data[user_id] = {"level": 1, "xp": 0, "height": 10}

    user_data = tower_data[user_id]
    user_data["xp"] += 5

    await handle_level_up(user, user_data, message.channel)

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
    user_data["xp"] += 3

    await handle_level_up(user, user_data, reaction.message.channel)

    with open("tower_data.json", "w") as f:
        json.dump(tower_data, f, indent=2)

# Commands
@bot.command(name='towerstats')
async def tower_stats(ctx, member: discord.Member = None):
    user = member or ctx.author
    user_id = str(user.id)

    if user_id not in tower_data:
        await ctx.send(f"{user.display_name} hasn't built a tower yet.")
        return

    user_data = tower_data[user_id]
    level = user_data.get("level", 1)
    xp = user_data.get("xp", 0)
    height = user_data.get("height", 10)

    title = get_title_for_level(level)
    flavor = get_flavor_for_level(level)

    embed = discord.Embed(
        title=f"{user.display_name}'s Tower Stats",
        description=f"🧙‍♂️ **{title} [Lv. {level}]** — Tower Height: **{height}ft**\nXP: `{xp}/{get_required_xp(level)}`\n\n*“{flavor}”*",
        color=0x9370DB
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
        user = await bot.fetch_user(int(user_id))
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

    for user_id in [attacker_id, opponent_id]:
        if user_id not in tower_data:
            tower_data[user_id] = {"level": 1, "xp": 0, "height": 10}

    attacker_data = tower_data[attacker_id]
    opponent_data = tower_data[opponent_id]

    update_leaderboard()
    leaderboard_ids = [user_id for user_id, _ in leaderboard]

    attacker_rank = leaderboard_ids.index(attacker_id) if attacker_id in leaderboard_ids else None
    opponent_rank = leaderboard_ids.index(opponent_id) if opponent_id in leaderboard_ids else None

    can_duel = (
        attacker_data["height"] >= opponent_data["height"] or
        opponent_rank == 2 or
        (attacker_rank == 2 and opponent_rank == 1) or
        (attacker_rank == 1 and opponent_rank == 0)
    )

    if not can_duel:
        await ctx.send(f"{attacker.display_name}, you cannot challenge {opponent.display_name} due to tower rank or height.")
        return

    outcome = random.choices(["attacker", "opponent", "tower"], weights=[30, 30, 40], k=1)[0]

    if outcome == "tower":
        attacker_data["height"] = 10
        opponent_data["height"] = 10
        embed = discord.Embed(
            title="🌩 The Tower Has Spoken...",
            description=f"Both **{attacker.display_name}** and **{opponent.display_name}** lose.\nThe Tower demands tribute. Their towers crumble... and the mystery deepens. 🗿",
            color=0xFFD700
        )
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

        winner_data["xp"] += 5
        await handle_level_up(winner, winner_data, ctx.channel)

        embed = discord.Embed(
            title=f"⚔️ Duel Result: {winner.display_name} Wins!",
            description=f"🏆 **{winner.display_name}** absorbs **{stolen}ft** of tower energy!\n⚠️ **{loser.display_name}**'s tower crumbles down to **10ft**.\n🧱 {winner.display_name}'s tower now stands at **{winner_data['height']}ft**!",
            color=0x00FF00
        )

    with open("tower_data.json", "w") as f:
        json.dump(tower_data, f, indent=2)

    await ctx.send(embed=embed)
    update_leaderboard()


@bot.command(name="faq")
async def faq(ctx):
    embed = discord.Embed(
        title="📜 Tower of Power – FAQ",
        description=(
            "**Welcome, Ascender. Here's how the Tower works...**\n\n"
            "🧱 **Starting Out**\n"
            "• Everyone begins with a 10ft tower and Lv. 1.\n"
            "• Gain XP by chatting (+5 XP), reacting (+3 XP), or winning duels (+5 XP).\n\n"
            "🧙‍♂️ **Leveling Up**\n"
            "• Every level needs 50 more XP (up to 500 max per level).\n"
            "• Leveling up gives you +3ft of height.\n"
            "• Type `!towerstats` to check your progress.\n\n"
            "⚔️ **Duels**\n"
            "• Use `!duel @someone` to challenge.\n"
            "• You can only duel someone with equal or lesser height unless:\n"
            "   - You're dueling 3rd place\n"
            "   - You're 3rd dueling 2nd\n"
            "   - You're 2nd dueling 1st\n"
            "• Winner steals 10% of the loser's height (rounded).\n"
            "• Loser resets to 10ft.\n\n"
            "🏆 **Leaderboard**\n"
            "• Type `!leaderboard` to view the top towers.\n"
            "• Ties go to whoever reached the height first.\n\n"
            "🌩 **The Tower watches... always.**"
        ),
        color=0x9370DB
    )
    embed.set_footer(text="Level up. Duel boldly. Grow your tower.")
    await ctx.send(embed=embed)

bot.run(DISCORD_TOKEN)
