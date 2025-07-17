import discord
from discord.ext import commands, tasks
import os
import random
import asyncio
import signal
import sys
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

def save_data():
    """Manual save function for compatibility"""
    try:
        db.storage.flush()
        print("💾 Data saved successfully")
    except Exception as e:
        print(f"❌ Failed to save data: {e}")

def graceful_shutdown():
    """Handle graceful shutdown and save data"""
    print("🛑 Shutting down bot...")
    print("💾 Saving all data before shutdown...")
    save_data()
    print("✅ Data saved. Bot shutdown complete.")
    sys.exit(0)

# Set up signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"📡 Received signal {signum}")
    graceful_shutdown()

signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

# Periodic auto-save task
@tasks.loop(minutes=5)
async def auto_save():
    """Automatically save data every 5 minutes"""
    save_data()
    print("⏰ Auto-save completed")

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
    
    # Start auto-save task
    if not auto_save.is_running():
        auto_save.start()
        print("⏰ Auto-save started (every 5 minutes)")

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
    embed.add_field(name="Title", value=f"**{get_title(user['level'])}**", inline=True)
    embed.add_field(name="Tower Stats", value=f"**Tower Height:** {user['height']}ft\n*{get_flavor(user['height'])}*", inline=False)
    embed.add_field(name="Level Info", value=f"Level {user['level']} — {user['xp']}/{xp_needed} XP", inline=True)
    embed.add_field(name="Duels", value=f"Wins: {user['wins']} | Losses: {user['losses']}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    """Display the top 10 tower heights"""
    all_players = db.all()
    
    if not all_players:
        await ctx.send("📊 No towers have been built yet! Start chatting to gain XP.")
        return
    
    # Sort by height (descending), then by timestamp (ascending - who reached it first)
    def sort_key(player):
        height = player.get("height", 5)
        timestamp = player.get("last_xp", "")
        return (-height, timestamp)
    
    sorted_players = sorted(all_players, key=sort_key)
    top_10 = sorted_players[:10]
    
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

@bot.command(name='duel')
async def duel(ctx, opponent: discord.Member):
    attacker_id = ctx.author.id
    defender_id = opponent.id

    # Get player data using TinyDB
    attacker = get_player(attacker_id)
    defender = get_player(defender_id)

    if attacker_id == defender_id:
        await ctx.send("❌ You can't challenge yourself!")
        return

    attacker_height = attacker.get("height", 5)
    defender_height = defender.get("height", 5)

    # Get leaderboard for ranking rules
    all_players = db.all()
    leaderboard = sorted(all_players, key=lambda x: (-x.get("height", 5), x.get("last_xp", "")))
    
    # Find ranks
    attacker_rank = None
    defender_rank = None
    
    for i, player in enumerate(leaderboard, 1):
        if player["id"] == attacker_id:
            attacker_rank = i
        if player["id"] == defender_id:
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

    # Duel outcomes with weights
    outcome = random.choices(["attacker", "defender", "tower"], weights=[0.4, 0.4, 0.2])[0]

    if outcome == "tower":
        # Tower wins - attacker loses height
        loss = round(attacker["height"] * 0.10)
        attacker["height"] = max(5, attacker["height"] - loss)  # Minimum 5ft
        attacker["losses"] = attacker.get("losses", 0) + 1
        save_player(attacker)
        
        await ctx.send(f"🗼 The Tower has spoken... {ctx.author.display_name} was struck down and lost {loss}ft!")
        save_data()
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
    loser["height"] = max(5, loser["height"] - transfer)  # Minimum 5ft
    
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
    save_data()

@bot.command()
async def resetme(ctx):
    db.remove(Player.id == ctx.author.id)
    await ctx.send("🔁 Your tower has been reset to 5ft. Time to rise again!")

# Manual save command for testing
@bot.command()
async def save(ctx):
    """Manually save data"""
    save_data()
    await ctx.send("💾 Data saved manually!")

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
            graceful_shutdown()
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
            graceful_shutdown()