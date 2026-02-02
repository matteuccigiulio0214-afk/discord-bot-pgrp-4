from dotenv import load_dotenv
import os

load_dotenv()  # legge le variabili dal file .env
TOKEN = os.getenv("DISCORD_TOKEN")
import discord
from discord.ext import commands
from discord import app_commands, FFmpegPCMAudio, ui
import json
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

DB_FILE = "sanzioni.json"
CONFIG_FILE = "config.json"

# Inizializza file JSON
for file_name in [DB_FILE, CONFIG_FILE]:
    if not os.path.exists(file_name):
        with open(file_name, "w") as f:
            f.write("{}" if file_name == DB_FILE else '{"staff_channel":"","revoca_channel":"","ssu_role":"","ssu_title":"","ssu_message":"","ssu_image":"","link_message":""}')

def carica_json(file):
    with open(file, "r") as f:
        return json.load(f)

def salva_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# Evento on_ready
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online come {bot.user}")

# =========================
# Pulsante Revoca BAN
# =========================
class RevocaButton(ui.View):
    def __init__(self, nome_roblox):
        super().__init__(timeout=None)
        self.nome_roblox = nome_roblox

    @ui.button(label="⛔ Revoca BAN", style=discord.ButtonStyle.danger)
    async def revoca(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = carica_json(CONFIG_FILE)
        revoca_channel = bot.get_channel(int(config.get("revoca_channel", 0)))
        if not revoca_channel:
            await interaction.response.send_message("Canale revoca non impostato", ephemeral=True)
            return
        await revoca_channel.send(f"Revoca BAN richiesta per {self.nome_roblox} da {interaction.user.mention}")
        await interaction.response.send_message("Richiesta inviata ✅", ephemeral=True)

# =========================
# Comando /setup
# =========================
@bot.tree.command(name="setup", description="Configura canali, ruoli, link")
@app_commands.describe(
    staff_channel="Canale staff",
    revoca_channel="Canale revoca ban",
    ssu_role="Ruolo da pingare con /ssu",
    ssu_title="Titolo embed SSU",
    ssu_message="Messaggio embed SSU",
    ssu_image="URL immagine embed SSU",
    link_message="Messaggio link personalizzato"
)
async def setup(interaction: discord.Interaction,
                staff_channel: discord.TextChannel,
                revoca_channel: discord.TextChannel,
                ssu_role: discord.Role,
                ssu_title: str,
                ssu_message: str,
                ssu_image: str,
                link_message: str):
    config = {
        "staff_channel": str(staff_channel.id),
        "revoca_channel": str(revoca_channel.id),
        "ssu_role": str(ssu_role.id),
        "ssu_title": ssu_title,
        "ssu_message": ssu_message,
        "ssu_image": ssu_image,
        "link_message": link_message
    }
    salva_json(CONFIG_FILE, config)
    await interaction.response.send_message("Setup completato ✅", ephemeral=True)

# =========================
# Comando /say
# =========================
@bot.tree.command(name="say", description="Il bot invia un messaggio a scelta")
@app_commands.describe(messaggio="Il messaggio da far dire al bot")
async def say(interaction: discord.Interaction, messaggio: str):
    await interaction.response.send_message(messaggio)

# =========================
# Comando /registra
# =========================
@bot.tree.command(name="registra", description="Registra Warn/Kick/Ban")
@app_commands.describe(
    tipo="Tipo di sanzione: warn/kick/ban",
    nome_roblox="Nome Roblox dell'utente",
    giorni="Solo ban: 0 per permanente",
    motivazione="Motivazione"
)
async def registra(interaction: discord.Interaction, tipo: str, nome_roblox: str, giorni: int = 0, motivazione: str = ""):
    dati = carica_json(DB_FILE)
    user_id = nome_roblox.lower()
    config = carica_json(CONFIG_FILE)
    
    if user_id not in dati:
        dati[user_id] = {"warn": 0}

    if tipo.lower() == "warn":
        dati[user_id]["warn"] += 1
        if dati[user_id]["warn"] >= 4:
            tipo = "ban"
            giorni = 0
    elif tipo.lower() == "kick":
        pass
    elif tipo.lower() == "ban":
        dati[user_id]["warn"] = 0
    
    salva_json(DB_FILE, dati)

    # Embed
    embed = discord.Embed(title=f"⚠️ {tipo.capitalize()} | {nome_roblox}", color=discord.Color.red())
    embed.add_field(name="⚠️ Utente Sanzionato", value=nome_roblox, inline=True)
    embed.add_field(name="⚙️ Staffer", value=interaction.user.mention, inline=True)
    embed.add_field(name="ℹ️ Motivazione", value=motivazione or "Nessuna motivazione", inline=False)
    provvedimento = "Ban" if tipo.lower() == "ban" else ("Kick" if tipo.lower() == "kick" else f"Warn #{dati[user_id]['warn']}")
    embed.add_field(name="⚠️ Provvedimento", value=provvedimento, inline=False)

    staff_channel = bot.get_channel(int(config.get("staff_channel", 0)))
    if staff_channel:
        await staff_channel.send(embed=embed, view=RevocaButton(nome_roblox))
    await interaction.response.send_message("Sanzione registrata ✅", ephemeral=True)

# =========================
# Comando /ssu
# =========================
@bot.tree.command(name="ssu", description="Manda messaggio SSU pingando un ruolo")
async def ssu(interaction: discord.Interaction):
    config = carica_json(CONFIG_FILE)
    channel = bot.get_channel(int(config.get("staff_channel", 0)))
    role_id = int(config.get("ssu_role", 0))
    role = interaction.guild.get_role(role_id)
    if not channel or not role:
        await interaction.response.send_message("Setup non completato!", ephemeral=True)
        return
    embed = discord.Embed(title=config.get("ssu_title", ""), description=config.get("ssu_message", ""), color=discord.Color.blue())
    if config.get("ssu_image"):
        embed.set_image(url=config["ssu_image"])
    await channel.send(content=role.mention, embed=embed)
    await interaction.response.send_message("Messaggio SSU inviato ✅", ephemeral=True)

# =========================
# Evento vocale
# =========================
@bot.event
async def on_voice_state_update(member, before, after):
    config = carica_json(CONFIG_FILE)
    staff_channel = bot.get_channel(int(config.get("staff_channel", 0)))
    
    if before.channel != after.channel and after.channel is not None:
        try:
            vc = await after.channel.connect()
            vc.play(FFmpegPCMAudio("vocals.mp3"))
            while vc.is_playing():
                await discord.utils.sleep_until(vc.is_playing() == False)
            await vc.disconnect()
        except:
            pass
        if staff_channel:
            await staff_channel.send(f"**{member.display_name}** è entrato nella voce {after.channel.name}")

# =========================
# Avvio
# =========================
bot.run(TOKEN)
