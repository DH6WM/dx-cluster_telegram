import asyncio
import telnetlib3
import re
import os
import json

from datetime import datetime
from telegram import Bot
from telegram.ext import Application, CommandHandler
# ==============================================================================
from log_util import log_dx_spot, log_message, log_error
# ==============================================================================

# Telnet Config
HOST = 'db0erf.de'      # enter Telnet Server 
PORT = 41113            # enter Telnet Port
TELNET_USER = ''        # enter Telnet Username
TELNET_PW = ''          # enter Telnet PW (empty if none)
RECONNECT_INTERVAL = 10 # Sekunden

# Telegram Config
bot_token = ''          # enter API Key
bot = Bot(token=bot_token)

# User Config File
CONFIG_FILE = 'user_config.json'
user_config = {}

RADIUS_PREFIXES = [
    # Deutschland
    "DA", "DB", "DC", "DD", "DE", "DF", "DG", "DH", "DI", "DJ", "DK", "DL", "DM", "DN", "DO", "DQ", "DR",  # alle deutschen Prefixe

    # Österreich
    "OE",  # alle OE-Regionen sind OE1 bis OE9

    # Schweiz & Liechtenstein
    "HB9", "HB3", "HB0",  # HB9 (CH), HB3 (Einsteiger), HB0 (Liechtenstein)

    # Frankreich
    "F", "TM", "TO", "TX",  # F = regulär, TM = Sonderstationen, TO/TX oft Überseegebiete

    # Luxemburg
    "LX",

    # Belgien
    "ON", "OO", "OR", "OT",  # ON regulär, andere für Events/Sonderstationen

    # Niederlande
    "PA", "PB", "PC", "PD", "PE", "PF", "PG", "PH", "PI",  # alle niederländischen Amateurpräfixe

    # Dänemark
    "OZ", "5P",

    # Polen
    "SP", "SN", "SQ", "SO", "HF", "3Z",

    # Tschechien
    "OK", "OL"

    # Slowakei
    # "OM",

    # optional: Erweiterbar um Nachbarländer 2. Ordnung oder entfernte Partnerregionen
    # z.B. "LA" (Norwegen), "SM" (Schweden), "YO" (Rumänien) je nach Projektziel
]

# ==============================================================================

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    log_message(message, level="log")

def load_config():
    global user_config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            log("Konfig erfolgreich geladen.")
    else:
        log("Keine Konfigurationsdatei gefunden – es wird mit leerem Config gestartet.")
        user_config = {}
        
def update_config():
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_config, f, indent=4, ensure_ascii=False)
        log("Konfiguration erfolgreich gespeichert.")
    except Exception as e:
        log(f"Fehler beim Speichern der Konfiguration: {e}")
        log_error(e, context = "Fehler beim speichern der 'user_config.json' .")
        
def ensure_user_exists(chat_id, username=None):
    chat_id = str(chat_id)
    neu = False
    if chat_id not in user_config:
        user_config[chat_id] = {
            "username": username,
            "status": "new",  # Standardwert für neue User
            "role": "",
            "prefix": [],
            "suffix": [],
            "call": [],
            "radius": "off"
        }
        update_config()
        neu = True
        
    elif username and not user_config[chat_id].get("username"):
        # Optional: Nachtragen, falls beim ersten Mal leer
        user_config[chat_id]["username"] = username
        update_config()
        
    return neu
    
# versucht, das Band aus QRG zu lesen
def get_band_from_frequency(freq_khz: float) -> str:
    """
    Gibt das Amateurfunkband als String zurück.
    Gibt 'unknown' zurück, wenn kein Band passt.
    Möglich ist, dass es in anderen Ländern, andere Grenzen gibt. Da wir in DL aber nur auf den u.g. QRGs senden dürfen, erübrigt sich eine genauere Teiung
    """
    bands = {
    "160m": (1800, 2000),
    "80m": (3500, 3800),
    "60m": (5351.5, 5366.5),
    "40m": (7000, 7200),
    "30m": (10100, 10150),
    "20m": (14000, 14350),
    "17m": (18068, 18168),
    "15m": (21000, 21450),
    "12m": (24890, 24990),
    "10m": (28000, 29700),
    "6m": (50000, 54000),
    "4m": (70000, 70500),
    "2m": (144000, 146000),
    "70cm": (430000, 440000)
    }

    if freq_khz < 0:
        return "unknown"

    if freq_khz < 1800:
        return "LW"

    if freq_khz > 440000:
        return "SHF"
    
    for band, (fmin, fmax) in bands.items():
        if fmin <= freq_khz <= fmax:
            return band

    # Kein passendes Band gefunden
    return "unknown"

#  versucht, die Betriebsart aus der Frequenz abzulesen.
def detect_mode(frequency_khz: float, comment: str, band: str) -> str | None:
    known_modes = {
        # Digitale Modi
        "FT8", "FT4", "JT65", "JT9", "PSK31", "PSK63", "PSK125", "RTTY", "OLIVIA",
        "MFSK", "MSK144", "JS8", "ROS", "THOR", "THROB", "CONTESTIA", "DOMINOEX",
        "HELL", "SSTV", "CW", "PACKET", "PACTOR", "WINMOR", "VARA", "ARDOP", "ATV",

        # Sprachmodi
        "SSB", "LSB", "USB", "AM", "FM", "DV", "DSTAR", "FREEDV", "C4FM", "DMR",

        # Satelliten-/Telemetrie-Modi
        "CW", "FM", "SSB", "BPSK", "AFSK", "FSK", "GMSK", "QPSK", "AX.25",

        # Sondermodi / exotisch
        "WSPR", "FSQ", "MT63", "FELDHELL", "Q15X25", "NBEMS", "EASYPAL"
    }
    comment_upper = comment.upper()

    # Prüfe Kommentar auf bekannte Modi
    for mode in known_modes:
        if mode in comment_upper:
            return mode

    # Frequenzbasierte Mode-Erkennung nur auf relevanten Frequenzen des Bandes
    ft8_center_freqs_by_band = {
        "160m": [1840],
        "80m": [3573],
        "60m": [5357],
        "40m": [7074],
        "30m": [10136],
        "20m": [14074],
        "17m": [18100],
        "15m": [21074],
        "12m": [24915],
        "10m": [28074],
        "6m": [50313, 50323],
        "4m": [70154],
        "2m": [144174]
    }

    FREQ_TOLERANCE_LOW = 0.2    # in kHz
    FREQ_TOLERANCE_HIGH = 3.0   # in kHz

    freqs_to_check = ft8_center_freqs_by_band.get(band, [])
    for center in freqs_to_check:
        if (center - FREQ_TOLERANCE_LOW) <= frequency_khz <= (center + FREQ_TOLERANCE_HIGH):
            return "FT8"

    return None

# Asynchrone Parsing-Funktion zum teilen der DX-Meldung in einzelne Variablen
async def parse_dx_spot(line: str):
    # log(f"Verarbeite Zeile: '{line}'")

    if not line.startswith("DX de "):
        log("Fehler: Zeile beginnt nicht mit 'DX de '")
        raise ValueError("Ungültiges Format: Zeile muss mit 'DX de ' beginnen.")

    try:
        rest = line[6:]  # Entferne "DX de "

        # Regex: Sender, Frequenz, Ziel, Kommentar, UTC-Zeit
        match = re.match(
            r"(\w+):\s+([0-9.]+)\s+([A-Z0-9/]+)\s+(.*?)\s*(\d{4}Z)", rest, re.IGNORECASE
        )

        if not match:
            log("Fehler: Regex-Match fehlgeschlagen")
            log_error(f"Fehler: Regex-Match fehlgeschlagen", context=line)
            raise ValueError("Zeile entspricht nicht dem erwarteten Format.")

        sender_call, frequency_str, target_call, comment, time_utc = match.groups()
        frequency = float(frequency_str)
        band = get_band_from_frequency(frequency)
        comment_clean = comment.strip()

        mode = detect_mode(frequency, comment_clean, band)

        if band == "unknown":
            log(f"Warnung: Frequenz {frequency} kHz konnte keinem bekannten Band zugeordnet werden.")

        if not mode:
            log(f"Info: Kein Modus erkannt für Frequenz {frequency} kHz und Kommentar '{comment_clean}'")

        result = {
            "sender_call": sender_call,
            "frequency": frequency,
            "band": band,
            "target_call": target_call,
            "mode": mode,
            "comment": comment_clean,
            "time_utc": time_utc
        }

        # log(f"Erfolgreich geparst: {result}")
        return result

    except Exception as e:
        log(f"Fehler beim Parsen der Zeile: {e}")
        log_error(e, context = "Fehler beim Parsen")
        raise
    
# Befehls Init. wird oft verwendet
async def befehls_init(update, context):
    
    # Prüfen, ob das Update ein message-Objekt enthält (z.B. nicht bei bearbeiteten Nachrichten)
    if not update.message:
        return None, None, False # Kein gültiges message-Objekt -> Abbruch, kein Command ausführen
        
    # Variablen aus Update Objekt ziehen 
    chat_id = str(update.message.chat.id)
    message = str(update.message.text)
    username = update.message.chat.username
    neu = ensure_user_exists(chat_id, username)
    
    # Befehlseingang loggen
    log(f"Start Befehl von {username} empfangen.: {message}")
    
    # Wenn der User neu angelegt wurde, Admins und den User informieren und Command abbrechen
    if neu:
        await send_telegram_message(
                    text=f"📢 Neuer User @{username} wurde hinzugefügt und wartet auf Freischaltung.",
                    target="admin"
                )
        await update.message.reply_text("🚫 Du bist nicht freigeschaltet. @DH6WM wurde über deine Anfrage informiert und wird diese in kürze bearbeiten.")
        return None, None, False
    
     # Prüfen, ob der User freigeschaltet ist (Status != "new")
    if user_config[chat_id]['status'] == 'new':
        return None, None, False # Command abbrechen, da User noch nicht freigeschaltet ist
       
    # Wenn alle Prüfungen erfolgreich, Daten zurückgeben und Command ausführen lassen
    return chat_id, username, True

# /start Befehl - Aktiviert die Cluster-Meldungen für den Benutzer
async def start(update, context):
    
    # Initialisiere Befehl, prüfe User und Berechtigungen
    chat_id, username, allowed = await befehls_init(update, context)
    # Falls User nicht freigeschaltet oder kein gültiges Update (z.B. EditMessage), abbrechen
    if not allowed:
        return
    
    # Cluster-Meldungen Userbezogen aktivieren
    user_config[chat_id]['status'] = 'active'
    update_config()
    
    await update.message.reply_text("✅ Die Cluster-Meldungen wurden aktiviert. Du erhältst jetzt alle relevanten Updates.")

# /stop Befehl - Deaktiviert die Cluster-Meldungen für den Benutzer
async def stop(update, context):
    
    # Initialisiere Befehl, prüfe User und Berechtigungen
    chat_id, username, allowed = await befehls_init(update, context)
    # Falls User nicht freigeschaltet oder kein gültiges Update (z.B. EditMessage), abbrechen
    if not allowed:
        return
   
    # Cluster-Meldungen Userbezogen stoppen
    user_config[chat_id]['status'] = 'inactive'
    update_config()
    
    await update.message.reply_text("⛔ Die Cluster-Meldungen wurden gestoppt. Du erhältst keine Updates mehr.")

# /status Befehl - Zeigt den aktuellen Status der Telnet-Verbindung und aktive Filter an
async def status(update, context):
    
    # Initialisiere Befehl, prüfe User und Berechtigungen
    chat_id, username, allowed = await befehls_init(update, context)
    # Falls User nicht freigeschaltet oder kein gültiges Update (z.B. EditMessage), abbrechen
    if not allowed:
        return
    
    # Daten auslesen
    prefix = user_config[chat_id].get("prefix", [])
    suffix = user_config[chat_id].get("suffix", [])
    call = user_config[chat_id].get("call", [])
    radius = user_config[chat_id].get("radius", [])
    user_status_value = user_config[chat_id].get("status", "inactive")
    
    await update.message.reply_text(
        f"📡 *Dein aktueller Status:*\n"
        f"- Benachrichtigungen: `{user_status_value}`\n"
        f"- Prefix-Filter     : `{', '.join(prefix) or 'Keine'}`\n"
        f"- Suffix-Filter     : `{', '.join(suffix) or 'Keine'}`\n"
        f"- Call-Filter        : `{', '.join(call) or 'Keine'}`\n"
        f"- Radius-Filter     : `{(radius)}`\n\n"
        f"🌐 Verbunden mit: `{HOST}`\n\n"
        f"📝 Nutze /hilfe um alle verfügbaren Befehle zu sehen",
        parse_mode="Markdown"
    )
     
async def filter_command(update, context):
    
    # Initialisiere Befehl, prüfe User und Berechtigungen
    chat_id, username, allowed = await befehls_init(update, context)
    # Falls User nicht freigeschaltet oder kein gültiges Update (z.B. EditMessage), abbrechen
    if not allowed:
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "ℹ️ *Verwendung:* `/filter <prefix|suffix|call|radius> [Wert1 Wert2 ...]`\n\n"
            "📌 Beispiele:\n"
            "• `/filter prefix 3D2 ZS`\n"
            "• `/filter suffix DARC /QRP`\n"
            "• `/filter call T30TTT`\n"
            "• `/filter radius on`\n"
            "• `/filter <prefix|suffix|call>` (leert den Filter)\n\n"
            "Du kannst Filter mit *Leerzeichen* oder *Komma* trennen.",
            parse_mode="Markdown"
        )
        return

    filter_type = context.args[0].lower()
    raw_values  = context.args[1:]  # kann leer sein für leeren Filter

    if filter_type not in ["prefix", "suffix", "call", "radius"]:
        await update.message.reply_text("❌ Unbekannter Filtertyp. Benutze prefix, suffix oder call.")
        return
     
    # RADIUS separat behandeln
    if filter_type == "radius":
        if not raw_values or raw_values[0].lower() not in ["on", "off"]:
            await update.message.reply_text("ℹ️ Radius-Filter muss `on` oder `off` sein. Beispiel: `/filter radius on`", parse_mode="Markdown")
            return
        user_config[chat_id]["radius"] = raw_values[0].lower()
        update_config()
        await update.message.reply_text(f"✅ Radius-Filter wurde auf `{raw_values[0].lower()}` gesetzt.", parse_mode="Markdown")
        return
    
    # Initialisiere den Filter-Array, falls nicht vorhanden
    if f"{filter_type}" not in user_config[chat_id]:
        user_config[chat_id][f"{filter_type}"] = []

    # Werte setzen oder leeren
    if not raw_values:
        # Filter leeren
        user_config[chat_id][filter_type] = []
    else:
        # Alle Argumente zu einem String zusammenfügen
        combined = " ".join(raw_values)
        # Nach Kommas splitten, danach nochmal nach Leerzeichen splitten
        parts = []
        for part in combined.split(","):
            parts.extend(part.strip().split())
        # Filter bereinigen und Großschreibung vereinheitlichen
        filters = [f.upper() for f in parts if f.strip()]
        user_config[chat_id][filter_type] = filters
        
    # Config speichern
    update_config()

    # Antwort an den User
    await update.message.reply_text(
        f"✅ Dein {filter_type}-Filter wurde aktualisiert auf: `{', '.join(user_config[chat_id][f'{filter_type}']) or 'Keine'}`",
        parse_mode="Markdown"
    )

async def hilfe(update, context):
    
    # Initialisiere Befehl, prüfe User und Berechtigungen
    chat_id, username, allowed = await befehls_init(update, context)
    # Falls User nicht freigeschaltet oder kein gültiges Update (z.B. EditMessage), abbrechen
    if not allowed:
        return
        
    help_text = (
        "📚 *Verfügbare Befehle:*\n\n"
        "/start - Cluster Benachrichtigungen aktivieren\n"
        "/stop - Cluster Benachrichtigungen pausieren\n"
        "/status - Zeigt deinen aktuellen Status und Filter\n"
        "/filter prefix <Filter1,Filter2 ...> - Setzt Prefix-Filter (leer = löschen)\n"
        "/filter suffix <Filter1,Filter2,...> - Setzt Suffix-Filter (leer = löschen)\n"
        "/filter call <Call1,Call2,...> - Setzt Filter für komplette Rufzeichen (leer = löschen)\n"
        "/filter radius <on|off> - der Spotter soll aus DL oder Nachbarland sein.\n"
        "/hilfe - Zeigt diese Hilfenachricht"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")
    
# Befehl zur Freigabe neuer Benutzer mit optionaler Rollenvergabe
async def approve(update, context):
    
    # Initialisiere Befehl, prüfe User und Berechtigungen
    chat_id, approver, allowed = await befehls_init(update, context)
    # Falls User nicht freigeschaltet oder kein gültiges Update (z.B. EditMessage), abbrechen
    if not allowed:
        return

    # 🔐 Rolle des Approvers prüfen (nur Admins dürfen)
    approver_data = user_config.get(chat_id, {})
    if approver_data.get("role") != "admin":
        await update.message.reply_text("🚫 Du hast keine Berechtigung für diesen Befehl.")
        return

    # ✅ Syntaxprüfung
    if len(context.args) < 1:
        await update.message.reply_text("ℹ️ Verwendung: /approve <username> [user|admin]")
        return

    target_username = context.args[0].lstrip("@").lower()
    new_role = context.args[1].lower() if len(context.args) > 1 else "user"

    approved = False

    for uid, user_data in user_config.items():
        if user_data.get("username", "").lower() == target_username:
            current_status = user_data.get("status", "new")

            # ⚠️ Benutzer wurde bereits freigeschaltet
            if current_status != "new":
                if user_data["role"] == new_role:
                    await update.message.reply_text(
                        f"ℹ️ @{target_username} wurde bereits freigeschaltet (Status: `{current_status}`).",
                        parse_mode="Markdown"
                    )
                    return
                
                # Nur Rollenupdate
                else:
                    user_data["role"] = new_role
                    update_config()
                    
                    # Befehlssender über Befehlslauf informieren
                    await update.message.reply_text(
                    f"✅ Benutzer @{target_username} wurde eine neue Rolle zugewiesen. (Rolle: *{new_role}*).",
                    parse_mode="Markdown"
                    )
                    
                     # 📬 Zielnutzer über Rollenänderung informieren
                    try:
                        await send_telegram_message(
                            text=f"ℹ️ Hallo @{target_username}, deine Rolle wurde auf *{new_role}* geändert.",
                            target=uid
                        )
                    except Exception as e:
                        log(f"Fehler beim Benachrichtigen von {target_username}: {e}")
                        log_error(e, context = "Approve: Fehler beim benachrichtigen (Rollenupdate).")

                    return
                
            # ✅ Freischalten und Rolle setzen
            user_data["status"] = "inactive"
            user_data["role"] = new_role
            update_config()

            await update.message.reply_text(
                f"✅ Benutzer @{target_username} wurde freigeschaltet (Status: *inactive*, Rolle: *{new_role}*).",
                parse_mode="Markdown"
            )

            # 📬 Zielnutzer benachrichtigen (sofern Chat-ID vorhanden)
            try:
                await send_telegram_message(
                    text=f"👋 Hallo @{target_username}, du wurdest soeben freigeschaltet! Du kannst jetzt /start verwenden um den Bot zu aktivieren.",
                    target=uid
                )
            except Exception as e:
                log(f"Fehler beim Benachrichtigen von {target_username}: {e}")
                log_error(e, context = "Approve: Fehler beim benachrichtigen (Freischaltung).")

            approved = True
            break

    # ❌ Kein passender Benutzer gefunden
    if not approved:
        await update.message.reply_text(f"❌ Kein Benutzer mit dem Namen @{target_username} gefunden.")

# Funktion zum Senden von Nachrichten
async def send_telegram_message(text, target="active"):
    """
    Sende eine Telegram-Nachricht über den Bot.
    
    Parameter:
    - text (str): Der Nachrichtentext
    - target (str|int): Steuert, an wen gesendet wird:
        * "active" → alle Nutzer mit Status "active"
        * "admin"  → alle Nutzer mit Rolle "admin"
        * <chat_id> (str oder int) → genau an diesen Nutzer
    """

    try:
        # 👤 Direkt an eine bestimmte Chat-ID senden
        if isinstance(target, (str, int)) and str(target).isdigit():
            await bot.send_message(chat_id=str(target), text=text)
            return

        # 🔁 Durch alle Nutzer in der Konfigurationsdatei iterieren
        for chat_id, data in user_config.items():
            # Aktuellen Status und Rolle des Nutzers auslesen
            status = data.get("status", "new")  # fallback: 'new'
            role = data.get("role", "user")     # fallback: 'user'

            # 🎯 Ziel: Alle freigeschalteten (aktiven) Nutzer
            if target == "active" and status == "active":
                await bot.send_message(chat_id=chat_id, text=text)

            # 🎯 Ziel: Alle Nutzer mit Admin-Rechten
            elif target == "admin" and role == "admin":
                await bot.send_message(chat_id=chat_id, text=text)

    except Exception as e:
        # 🛑 Fehler beim Senden protokollieren
        log(f"Fehler beim Telegram-Versand an '{target}': {e}")
        log_error(e, context = "Send Telegram Message: Fehler beim Telegram-Versand.")

# Wenn die Filter einen Treffer finden...
async def handle_match(chat_id, username, dx_data):
    """Aktion bei Treffer mit geparsten DX-Daten."""
    try:
        # Daten aus dem Dictionary extrahieren
        sender = dx_data.get("sender_call", "N/A")
        target = dx_data.get("target_call", "N/A")
        freq   = dx_data.get("frequency", 0.0)
        band   = dx_data.get("band", "unknown")
        mode   = dx_data.get("mode", "n/a")
        time   = dx_data.get("time_utc", "")
        comment = dx_data.get("comment", "")

        # Protokollieren
        log(f"Treffer für {username} gefunden: {target} auf {freq} kHz ({band}, {mode})")

        # Nachrichtentext formatieren
        message = (
            f"📡 *DX-Cluster Treffer:*\n"
            f"• *Call:* `{target}`\n"
            f"• *Frequenz:* `{freq:.1f} kHz`\n"
            f"• *Band:* `{band}`\n"
            f"• *Betriebsart:* `{mode}`\n"
            f"• *Kommentar:* `{comment}`\n"
            f"• *Von:* `{sender}` um `{time}`"
        )

        # Senden über Telegram Bot
        status = user_config.get(chat_id, {}).get("status")
        if status == "active":
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown"
            )

    except Exception as e:
        log(f"Fehler beim Senden der Telegram-Nachricht: {e}")
        log_error(e, context = "Handle Match: Fehler beim Telegram-Versand.")

# Telnet Verbindung aufbauen und halten. Erhaltene Zeilen Parser übergeben und Treffer in Filtern suchen.
async def monitor_connection():
    """Verbindung aufbauen und Daten überwachen."""
    while True:
        try:
            log(f"Verbinde mit {HOST}:{PORT} ...")
            await send_telegram_message(f"Versuche Verbindung zu {HOST}:{PORT}", target = "admin")
            reader, writer = await telnetlib3.open_connection(HOST, PORT)
            log("Verbindung hergestellt.")
            await send_telegram_message("Telnet-Verbindung erfolgreich hergestellt.", target = "admin")

            # Optional: Anmeldung o. Ä.
            writer.write(f"{TELNET_USER}\n")
            writer.write(f"{TELNET_PW}\n")
            await asyncio.sleep(1)
            
            # Name setzen
            # writer.write("set/name Willi\n")
            # QTH setzen
            # writer.write("set/qth Weimar\n")
            # Locator setzen
            # writer.write("set/qra JO50PX\n")

            # Clear Filter und setze Prefix-Filter
            writer.write("CLEAR/SPOTS\n")
            writer.write("CLEAR/ANN\n")
            writer.write("CLEAR/WCY\nn")
            writer.write("CLEAR/WWV\n")
            await asyncio.sleep(1)
            
            # schon via Cluster Server einen Filter auf Prefix setzen
            # writer.write("ACCEPT/SPOTS CALL DL*\n")
            # writer.write("REJECT/ANN all\n")
            # writer.write("REJECT/WCY all\n")
            # writer.write("REJECT/WWV all\n")
            # await asyncio.sleep(1)

            # Filter anzeigen
            writer.write("SHOW/FILTER\n")

            # Endlosschleife zum Lesen der Daten
            while True:
                line = await reader.readline()
                if not line:
                    raise ConnectionError("Verbindung unterbrochen")
                    
                # log(line.strip())  # Optional: Alle Telnet Zeilen anzeigen
                
                line = line.strip()
                if not line.startswith("DX de "):
                    continue  # Nicht relevant
                
                try:
                    dx_data = await parse_dx_spot(line)  # 🎯 parse die Zeile

                except Exception as e:
                    log(f"Parse-Fehler: {e} | Zeile: {line}")
                    log_error(e, context = f"Parse-Fehler: {line}")
                    continue  # Fehlerhafte Zeile überspringen
                
                target = dx_data["target_call"]
                sender = dx_data["sender_call"]
                frequency = dx_data["frequency"]
                band = dx_data["band"]
                mode = dx_data["mode"]
                comment = dx_data["comment"]
                
                # Für alle user in user_config prüfen
                for chat_id, data in user_config.items():
                    if data.get('status') != 'active':
                        continue  # Nur aktive user berücksichtigen

                    prefix = data.get('prefix', [])
                    suffix = data.get('suffix', [])
                    call = data.get('call', [])
                    user = data.get('username', [])
                    radius_active = data.get("radius") == "on"

                    # 🔍 Führe Matching auf dem Zielrufzeichen durch
                    prefix_match = any(target.startswith(p) for p in prefix)
                    suffix_match = any(target.endswith(s) for s in suffix)
                    call_match   = target in call
                    radius_match = any(sender.startswith(r) for r in RADIUS_PREFIXES)  

                    # Logik:
                    # - Wenn Radius aus ist: ganz normal
                    # - Wenn Radius an ist: dann muss ein Radius-Match UND ein Benutzerfilter-Match vorliegen
                    if radius_active:
                        if radius_match and (prefix_match or suffix_match or call_match):
                            await handle_match(chat_id, user, dx_data)
                    else:
                        if prefix_match or suffix_match or call_match:
                            await handle_match(chat_id, user, dx_data)

        except Exception as e:
            await send_telegram_message(f"❌ Telnet-Verbindung verloren: {e}", target = "admin")
            log (f"Fehler: {e}")
            log (f"Neuer Verbindungsversuch in {RECONNECT_INTERVAL} Sekunden ...")
            log_error(e, context = "Telnet-Verbindung verloren!}")
            await asyncio.sleep(RECONNECT_INTERVAL)

# Telegram-Bot starten und mit Befehlen reagieren
async def start_bot_and_monitor():
    application = Application.builder().token(bot_token).build()

    # Befehlshandler hinzufügen
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("filter", filter_command))
    application.add_handler(CommandHandler("hilfe", hilfe))
    application.add_handler(CommandHandler("approve", approve))

    # Initialisiere und starte den Bot manuell
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await send_telegram_message("🔄 DX-Cluster Monitor gestartet", target = "admin")

    # Starte Telnet-Monitoring parallel
    telnet_task = asyncio.create_task(monitor_connection())

    # Warte bis der Bot gestoppt wird (z. B. via Signal)
    await application.updater.wait_until_closed()
    

    # Danach beende sauber alles
    await telnet_task
    await application.stop()
    await application.shutdown()

# Main-Funktion starten
if __name__ == '__main__':
    # JSON in Variable laden
    load_config()
    # Starte den Bot und das Telnet-Monitoring innerhalb einer Event-Schleife
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(start_bot_and_monitor())
        loop.run_forever()
    except KeyboardInterrupt as e:
        log("Beendet durch Benutzer.")
        log_error(e, context = "Script beendet!")
