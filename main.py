import os, json, threading, time
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "NEXUS MARKET is online!"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()

OWNER_ID = os.getenv('OWNER_ID', '')
OWNER_USERNAME = os.getenv('OWNER_USERNAME', '@starrlightz12')
RECOVERY_KEY = os.getenv('RECOVERY_KEY', 'change-me')
# YOUR servers - comma separated IDs in Render: YOUR_SERVER_IDS=123,456,789
YOUR_SERVERS = [s.strip() for s in os.getenv('YOUR_SERVER_IDS', '').split(',') if s.strip()]

DB_FILE = 'db.json'
db = {"listings": {}, "ratings": {}, "mode": "private", "allowedServers": [], "lockedFuncs": [], "wanted": [], "auctions": {}, "featured": []}
if os.path.exists(DB_FILE):
    try: db.update(json.load(open(DB_FILE)))
    except: pass
def save(): json.dump(db, open(DB_FILE, 'w'), indent=2)

def is_owner(id): return str(id) == str(OWNER_ID)
def owner_msg(): return f"❌ Only the Owner can do this. DM {OWNER_USERNAME}."
def is_locked(func): return func in db.get("lockedFuncs", [])

def can_use_market(guild_id):
    mode = db.get("mode", "private")
    if mode == "public": return True
    if mode == "private": return str(guild_id) in YOUR_SERVERS
    if mode == "allowlist": return str(guild_id) in YOUR_SERVERS or str(guild_id) in db.get("allowedServers", [])
    return False

def market_blocked(interaction, func=None):
    # Returns error string or None if OK
    if not interaction.guild: return "❌ Use MARKET in a server, not DMs."
    if not can_use_market(interaction.guild.id):
        return f"❌ This bot is private. Only {OWNER_USERNAME}'s servers can use it. Mode: {db.get('mode')}"
    if func and is_locked(func):
        return f"🔒 `{func}` is locked by Owner. DM {OWNER_USERNAME}"
    return None

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try: await bot.tree.sync()
    except Exception as e: print("SYNC FAIL:", e)
    print(f"✅ NEXUS MARKET logged in as {bot.user} | Mode: {db.get('mode')}")

# ---------- OWNER: MODE / ALLOW / LOCK ----------

@bot.tree.command(name="market-mode", description="Set MARKET mode - Owner only")
@app_commands.choices(mode=[app_commands.Choice(name="private", value="private"), app_commands.Choice(name="public", value="public"), app_commands.Choice(name="allowlist", value="allowlist")])
async def market_mode(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    db["mode"] = mode.value; save()
    await interaction.response.send_message(f"✅ MARKET mode set to **{mode.value}** 👑\nPrivate = only your servers\nPublic = anyone\nAllowlist = only approved servers")

@bot.tree.command(name="market-allow", description="Allow a server to use MARKET - Owner only")
async def market_allow(interaction: discord.Interaction, server_id: str):
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    if server_id not in db["allowedServers"]: db["allowedServers"].append(server_id)
    save(); await interaction.response.send_message(f"✅ Server `{server_id}` can now use MARKET")

@bot.tree.command(name="market-deny", description="Remove a server from MARKET - Owner only")
async def market_deny(interaction: discord.Interaction, server_id: str):
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    if server_id in db["allowedServers"]: db["allowedServers"].remove(server_id)
    save(); await interaction.response.send_message(f"✅ Server `{server_id}` denied from MARKET 🔒")

@bot.tree.command(name="market-servers", description="See MARKET servers + mode")
async def market_servers(interaction: discord.Interaction):
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    await interaction.response.send_message(f"**Mode:** {db.get('mode')}\n**Your Servers:** {YOUR_SERVERS}\n**Allowed Servers:** {db.get('allowedServers')}\n**Locked Funcs:** {db.get('lockedFuncs')}", ephemeral=True)

@bot.tree.command(name="market-lock", description="Lock a MARKET function - Owner only")
@app_commands.choices(function=[app_commands.Choice(name="sell", value="sell"), app_commands.Choice(name="buy", value="buy"), app_commands.Choice(name="auction", value="auction"), app_commands.Choice(name="bid", value="bid"), app_commands.Choice(name="wanted", value="wanted"), app_commands.Choice(name="middleman", value="middleman"), app_commands.Choice(name="rate", value="rate")])
async def market_lock(interaction: discord.Interaction, function: app_commands.Choice[str]):
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    if function.value not in db["lockedFuncs"]: db["lockedFuncs"].append(function.value)
    save(); await interaction.response.send_message(f"🔒 `{function.value}` LOCKED everywhere")

@bot.tree.command(name="market-unlock", description="Unlock a MARKET function - Owner only")
@app_commands.choices(function=[app_commands.Choice(name="sell", value="sell"), app_commands.Choice(name="buy", value="buy"), app_commands.Choice(name="auction", value="auction"), app_commands.Choice(name="bid", value="bid"), app_commands.Choice(name="wanted", value="wanted"), app_commands.Choice(name="middleman", value="middleman"), app_commands.Choice(name="rate", value="rate")])
async def market_unlock(interaction: discord.Interaction, function: app_commands.Choice[str]):
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    if function.value in db["lockedFuncs"]: db["lockedFuncs"].remove(function.value)
    save(); await interaction.response.send_message(f"✅ `{function.value}` UNLOCKED")

@bot.tree.command(name="market-locks", description="See what's locked")
async def market_locks(interaction: discord.Interaction):
    await interaction.response.send_message(f"**Mode:** {db.get('mode')}\n**Locked:** {', '.join(db.get('lockedFuncs', [])) or 'Nothing locked ✅'}", ephemeral=True)

# ---------- SELL / BUY ----------

@bot.tree.command(name="market-sell", description="Sell an item")
async def market_sell(interaction: discord.Interaction, item: str, price: str, description: str = ""):
    err = market_blocked(interaction, "sell")
    if err: return await interaction.response.send_message(err, ephemeral=True)
    lid = str(int(time.time()*1000))
    db["listings"][lid] = {"item": item, "price": price, "desc": description, "seller": str(interaction.user.id), "sellerName": str(interaction.user), "guild": str(interaction.guild.id)}
    save()
    embed = discord.Embed(title=f"🛒 NEXUS MARKET - {item}", description=description or "No description", color=0xFFD700)
    embed.add_field(name="Price", value=price, inline=True)
    embed.add_field(name="Seller", value=interaction.user.mention, inline=True)
    embed.add_field(name="ID", value=lid, inline=True)
    embed.set_footer(text=f"Use /market-buy id:{lid} to buy • Seller rating: {db.get('ratings', {}).get(str(interaction.user.id), 'No ratings yet')}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="market-buy", description="Buy an item by ID")
async def market_buy(interaction: discord.Interaction, id: str):
    err = market_blocked(interaction, "buy")
    if err: return await interaction.response.send_message(err, ephemeral=True)
    item = db.get("listings", {}).get(id)
    if not item: return await interaction.response.send_message("❌ Item not found. Use /market-list to see IDs", ephemeral=True)
    seller = await bot.fetch_user(int(item["seller"]))
    await interaction.response.send_message(f"✅ {interaction.user.mention} wants to buy **{item['item']}** for **{item['price']}**\nSeller: {seller.mention} - Check your DMs! Both of you DM each other to finish the deal.", ephemeral=False)
    try: await seller.send(f"🛒 Someone wants your item **{item['item']}** ({item['price']}) in {interaction.guild.name} - Buyer: {interaction.user} - DM them!")
    except: pass

@bot.tree.command(name="market-list", description="See all listings")
async def market_list(interaction: discord.Interaction):
    err = market_blocked(interaction)
    if err: return await interaction.response.send_message(err, ephemeral=True)
    listings = [v for v in db.get("listings", {}).values() if v["guild"] == str(interaction.guild.id)]
    if not listings: return await interaction.response.send_message("No listings yet. Use /market-sell to post one!", ephemeral=True)
    text = "\n".join([f"**{v['item']}** - {v['price']} - <@{v['seller']}> - ID: `{k}`" for k, v in db["listings"].items() if v["guild"] == str(interaction.guild.id)])
    await interaction.response.send_message(f"🛒 **MARKET LISTINGS:**\n{text}")

@bot.tree.command(name="market-search", description="Search for an item")
async def market_search(interaction: discord.Interaction, item: str):
    err = market_blocked(interaction)
    if err: return await interaction.response.send_message(err, ephemeral=True)
    found = [(k, v) for k, v in db.get("listings", {}).items() if item.lower() in v["item"].lower() and v["guild"] == str(interaction.guild.id)]
    if not found: return await interaction.response.send_message(f"No results for `{item}`", ephemeral=True)
    text = "\n".join([f"**{v['item']}** - {v['price']} - <@{v['seller']}> - ID: `{k}`" for k, v in found])
    await interaction.response.send_message(f"🔍 Results:\n{text}")

@bot.tree.command(name="market-sold", description="Mark item sold - Seller + Owner only")
async def market_sold(interaction: discord.Interaction, id: str):
    err = market_blocked(interaction)
    if err: return await interaction.response.send_message(err, ephemeral=True)
    item = db.get("listings", {}).get(id)
    if not item: return await interaction.response.send_message("❌ Not found", ephemeral=True)
    if str(interaction.user.id) != item["seller"] and not is_owner(interaction.user.id): return await interaction.response.send_message("❌ Only seller or Owner", ephemeral=True)
    db["listings"].pop(id); save()
    await interaction.response.send_message(f"✅ SOLD! **{item['item']}** for {item['price']} 🎉")

@bot.tree.command(name="market-remove", description="Remove listing - Seller + Owner only")
async def market_remove(interaction: discord.Interaction, id: str):
    err = market_blocked(interaction)
    if err: return await interaction.response.send_message(err, ephemeral=True)
    item = db.get("listings", {}).get(id)
    if not item: return await interaction.response.send_message("❌ Not found", ephemeral=True)
    if str(interaction.user.id) != item["seller"] and not is_owner(interaction.user.id): return await interaction.response.send_message("❌ Only seller or Owner", ephemeral=True)
    db["listings"].pop(id); save()
    await interaction.response.send_message(f"✅ Removed **{item['item']}**")

@bot.tree.command(name="market-clear", description="Clear ALL listings - Owner only")
async def market_clear(interaction: discord.Interaction):
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    db["listings"] = {}; save()
    await interaction.response.send_message("✅ All listings cleared")

# ---------- WANTED / RATE / MIDDLEMAN / HELP ----------

@bot.tree.command(name="market-wanted", description="Post what you want to buy")
async def market_wanted(interaction: discord.Interaction, item: str, price: str):
    err = market_blocked(interaction, "wanted")
    if err: return await interaction.response.send_message(err, ephemeral=True)
    db["wanted"].append({"item": item, "price": price, "user": str(interaction.user.id), "guild": str(interaction.guild.id)}); save()
    await interaction.response.send_message(f"🔍 **WANTED:** {interaction.user.mention} wants **{item}** for **{price}** - DM them if you have it!")

@bot.tree.command(name="market-rate", description="Rate a user after a deal")
async def market_rate(interaction: discord.Interaction, user: discord.Member, stars: int):
    err = market_blocked(interaction, "rate")
    if err: return await interaction.response.send_message(err, ephemeral=True)
    if stars < 1 or stars > 5: return await interaction.response.send_message("Stars must be 1-5", ephemeral=True)
    db.setdefault("ratings", {}).setdefault(str(user.id), []).append(stars); save()
    avg = sum(db["ratings"][str(user.id)]) / len(db["ratings"][str(user.id)])
    await interaction.response.send_message(f"✅ Rated {user.mention} {stars}⭐ - New average: {avg:.1f}⭐ ({len(db['ratings'][str(user.id)])} ratings)")

@bot.tree.command(name="market-middleman", description="Start middleman deal - Owner only")
async def market_middleman(interaction: discord.Interaction, buyer: discord.Member, seller: discord.Member, item: str, price: str):
    err = market_blocked(interaction, "middleman")
    if err: return await interaction.response.send_message(err, ephemeral=True)
    if not is_owner(interaction.user.id): return await interaction.response.send_message(owner_msg(), ephemeral=True)
    await interaction.response.send_message(f"🛡️ **MIDDLEMAN DEAL**\nBuyer: {buyer.mention}\nSeller: {seller.mention}\nItem: **{item}**\nPrice: **{price}**\nOwner {interaction.user.mention} is holding this deal. Both confirm in DMs, then Owner says deal done. No scam 👑")

@bot.tree.command(name="market-help", description="Show MARKET commands")
async def market_help(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 NEXUS MARKET - Commands", description=f"Mode: {db.get('mode')} | Owner: {OWNER_USERNAME}", color=0xFFD700)
    embed.add_field(name="🛒 Sell / Buy", value="`/market-sell item: Dragon price: 500 description: Rare`\n`/market-buy id: <id>`\n`/market-list`\n`/market-search item: Dragon`\n`/market-sold id: <id>`\n`/market-remove id: <id>`", inline=False)
    embed.add_field(name="🔍 Wanted / Rate", value="`/market-wanted item: Dragon price: 500`\n`/market-rate user: @user stars: 5`", inline=False)
    embed.add_field(name="🛡️ Middleman", value="`/market-middleman buyer: @x seller: @y item: Dragon price: 500` (Owner)", inline=False)
    embed.add_field(name="🔒 Owner Controls", value="`/market-mode mode: private/public/allowlist`\n`/market-allow server-id: 123`\n`/market-deny server-id: 123`\n`/market-lock function: sell`\n`/market-unlock function: sell`\n`/market-locks`\n`/market-clear`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="claim-owner", description="Claim owner with recovery key")
async def claim_owner(interaction: discord.Interaction, key: str):
    global OWNER_ID
    if key == RECOVERY_KEY:
        OWNER_ID = str(interaction.user.id)
        await interaction.response.send_message("✅ You are now the Owner! Update OWNER_ID in Render too.", ephemeral=True)
    else: await interaction.response.send_message("❌ Wrong key", ephemeral=True)

TOKEN = os.getenv('DISCORD_TOKEN')
print('TOKEN CHECK - length:', len(TOKEN) if TOKEN else 'MISSING')
bot.run(TOKEN.strip() if TOKEN else '')
