import discord
from discord.ext import commands, tasks
import os
import random
import asyncio
import signal
import sys
from datetime import datetime
from tinydb import TinyDB, Query
import atexit

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Database setup
db = TinyDB('player_data.json')
Player = Query()

BASE_XP = 50
MAX_XP_PER_LEVEL = 500
XP_PER_MESSAGE = 2
XP_PER_REACTION = 3
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
    user = db.get(Player.id == int(user_id))
    if not user:
        user = {
            "id": int(user_id),
            "xp": 0,
            "level": 1,
            "height": 5,
            "wins": 0,
            "losses": 0
        }
        db.insert(user)
    return user

def save_player(user_data):
    """Save player data"""
    db.upsert(user_data, Player.id == int(user_data["id"]))

def get_all_players():
    """Get all players sorted by height (desc) then by insertion order"""
    return sorted(db.all(), key=lambda x: (-x.get("height", 5), x.get("id", 0)))

def calculate_level_and_height(user_data):
    """Calculate correct level from XP but preserve height from duels"""
    xp = user_data["xp"]
    old_level = user_data.get("level", 1)
    level = 1
    
    # Calculate level from XP
    temp_xp = xp
    while temp_xp >= get_level_xp(level):
        temp_xp -= get_level_xp(level)
        level += 1
    
    # Update level and remaining XP
    user_data["level"] = level
    user_data["xp"] = temp_xp
    
    # Only adjust height if level changed (don't override duel height changes)
    if level != old_level:
        height_change = (level - old_level) * HEIGHT_PER_LEVEL
        user_data["height"] = user_data.get("height", 5) + height_change
    
    return user_data

def try_level_up(user_id):
    user = get_player(user_id)
    old_level = user["level"]
    
    # Recalculate level and height
    user = calculate_level_and_height(user)
    
    save_player(user)
    return user["level"] > old_level

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

# Graceful shutdown handling
def cleanup():
    print("💾 Ensuring all data is saved...")
    db.close()
    print("✅ Database closed safely")

atexit.register(cleanup)

def signal_handler(signum, frame):
    print(f"📡 Received signal {signum}")
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@bot.event
async def on_ready():
    print(f"Tower of Power online as {bot.user}")
    print(f"💾 Database has {len(db.all())} players")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Process commands first
    await bot.process_commands(message)
    
    # Skip XP for commands (messages starting with !)
    if message.content.startswith('!'):
        return

    # Award XP for regular messages
    user = get_player(message.author.id)
    user["xp"] += XP_PER_MESSAGE
    save_player(user)

    if try_level_up(message.author.id):
        await send_levelup_message(message.author)

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
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

@bot.command()
async def faq(ctx):
    embed = discord.Embed(title="🧙 Tower of Power — FAQ", color=0x9370DB)
    embed.add_field(name="How to grow?", value="• Chat (+2 XP)\n• React (+3 XP)\n• Level up = +3ft\n• Win duels = steal height", inline=False)
    embed.add_field(name="Commands", value="!towerstats, !leaderboard, !duel @user, !resetme, !faq", inline=False)
    embed.add_field(name="Special Rules", value="• 2nd can duel 1st\n• 3rd can duel 2nd\n• Anyone can duel 3rd\n• Otherwise, duel equal/smaller towers", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def towerstats(ctx, target: discord.Member = None):
    if target:
        user = get_player(target.id)
        username = target.display_name
    else:
        user = get_player(ctx.author.id)
        username = ctx.author.display_name
    
    # Ensure data is current
    user = calculate_level_and_height(user)
    save_player(user)
    
    xp_needed = get_level_xp(user["level"])
    embed = discord.Embed(title=f"🏗️ {username}'s Tower", color=0x00BFFF)
    embed.add_field(name="Title", value=f"**{get_title(user['level'])}**", inline=True)
    embed.add_field(name="Tower Stats", value=f"**Tower Height:** {user['height']}ft\n*{get_flavor(user['height'])}*", inline=False)
    embed.add_field(name="Level Info", value=f"Level {user['level']} — {user['xp']}/{xp_needed} XP", inline=True)
    embed.add_field(name="Duels", value=f"Wins: {user['wins']} | Losses: {user['losses']}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    # Refresh all player data first
    all_players = []
    for player in db.all():
        player = calculate_level_and_height(player)
        save_player(player)
        all_players.append(player)
    
    all_players = sorted(all_players, key=lambda x: (-x.get("height", 5), x.get("id", 0)))
    
    if not all_players:
        await ctx.send("📊 No towers have been built yet! Start chatting to gain XP.")
        return
    
    top_10 = all_players[:10]
    
    embed = discord.Embed(
        title="🏆 Tower Leaderboard",
        description="Top 10 Tallest Towers",
        color=0xFFD700
    )
    
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    
    for i, player in enumerate(top_10):
        try:
            user = bot.get_user(int(player["id"]))
            username = user.display_name if user else f"User {player['id']}"
        except:
            username = f"User {player['id']}"
        
        height = player.get("height", 5)
        level = player.get("level", 1)
        title = get_title(level)
        
        embed.add_field(
            name=f"{medals[i]} #{i+1}",
            value=f"**{username}**\n{height}ft tall\nLevel {level} *{title}*",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def duel(ctx, opponent: discord.Member):
    attacker_id = ctx.author.id
    defender_id = opponent.id

    if attacker_id == defender_id:
        await ctx.send("❌ You can't challenge yourself!")
        return

    attacker = get_player(attacker_id)
    defender = get_player(defender_id)

    # Ensure current data
    attacker = calculate_level_and_height(attacker)
    defender = calculate_level_and_height(defender)

    attacker_height = attacker.get("height", 5)
    defender_height = defender.get("height", 5)

    # Get leaderboard for ranking rules
    all_players = get_all_players()
    
    # Find ranks
    attacker_rank = None
    defender_rank = None
    
    for i, player in enumerate(all_players, 1):
        if int(player["id"]) == attacker_id:
            attacker_rank = i
        if int(player["id"]) == defender_id:
            defender_rank = i
    
    # Check duel eligibility
    can_challenge = False
    
    # Special rule: 2nd place can challenge 1st place
    if attacker_rank == 2 and defender_rank == 1:
        can_challenge = True
    # Special rule: 3rd place can challenge 2nd place
    elif attacker_rank == 3 and defender_rank == 2:
        can_challenge = True
    # Special rule: anyone can challenge 3rd place
    elif defender_rank == 3:
        can_challenge = True
    # Regular rule: can only challenge equal or smaller towers
    elif attacker_height >= defender_height:
        can_challenge = True
    
    if not can_challenge:
        if defender_rank == 1:
            await ctx.send("❌ Only the 2nd place player can challenge the tower king!")
        elif defender_rank == 2:
            await ctx.send("❌ Only the 3rd place player can challenge the 2nd place holder!")
        else:
            await ctx.send("❌ You can only challenge someone with equal or smaller tower height.")
        return

    # Duel outcomes - 50% attacker, 30% defender, 20% tower
    rand = random.random()
    if rand < 0.5:
        outcome = "attacker"
    elif rand < 0.8:
        outcome = "defender"
    else:
        outcome = "tower"

    if outcome == "tower":
        # Tower wins - attacker loses height
        loss = round(attacker["height"] * 0.10)
        attacker["height"] = max(5, attacker["height"] - loss)
        attacker["losses"] = attacker.get("losses", 0) + 1
        save_player(attacker)
        
        await ctx.send(f"🗼 The Tower has spoken... {ctx.author.display_name} was struck down and lost {loss}ft!")
        return

    # Player vs Player
    if outcome == "attacker":
        winner = attacker
        loser = defender
        winner_member = ctx.author
        loser_member = opponent
    else:
        winner = defender
        loser = attacker
        winner_member = opponent
        loser_member = ctx.author

    # Calculate height transfer (10% of loser's height)
    transfer = round(loser["height"] * 0.10)
    
    # Transfer height
    winner["height"] += transfer
    loser["height"] = max(5, loser["height"] - transfer)
    
    # Update win/loss records
    winner["wins"] = winner.get("wins", 0) + 1
    loser["losses"] = loser.get("losses", 0) + 1
    
    # Save both players
    save_player(winner)
    save_player(loser)

    # Send result message
    embed = discord.Embed(
        title="⚔️ Tower Duel Results",
        color=0xFF6B6B
    )
    embed.add_field(
        name="Victory!", 
        value=f"**{winner_member.display_name}** has defeated **{loser_member.display_name}**!", 
        inline=False
    )
    embed.add_field(
        name="Spoils of War", 
        value=f"**{winner_member.display_name}** absorbs {transfer}ft and rises even higher.", 
        inline=False
    )
    embed.add_field(
        name="The Fallen", 
        value=f"**{loser_member.display_name}** loses {transfer}ft but will rise again.", 
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def resetme(ctx):
    db.remove(Player.id == int(ctx.author.id))
    await ctx.send("🔁 Your tower has been reset to 5ft. Time to rise again!")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Please set your Discord bot token in the DISCORD_BOT_TOKEN environment variable")
    else:
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            print("❌ Invalid token. Please check your Discord bot token.")
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            cleanup()
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
            cleanup()
