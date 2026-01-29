import requests
import os
from datetime import datetime
import pytz

# --- KONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
KP_THRESHOLD = 6
# Prüfen, ob der Workflow manuell gestartet wurde (für Test-Nachricht)
GITHUB_EVENT_NAME = os.environ.get('GITHUB_EVENT_NAME', '')

# --- QUELLEN ---
URL_KP_FORECAST = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
URL_ALERTS = "https://services.swpc.noaa.gov/products/alerts.json"
URL_OVATION_MAP = "https://services.swpc.noaa.gov/images/animations/ovation/north/latest.jpg"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def utc_to_local(utc_dt_string):
    """Konvertiert NOAA UTC Zeitstrings in deutsche Zeit."""
    try:
        # NOAA Format oft: '2023-12-01 12:00:00'
        utc_dt = datetime.strptime(utc_dt_string, '%Y-%m-%d %H:%M:%S')
        utc_dt = pytz.utc.localize(utc_dt)
        german_tz = pytz.timezone('Europe/Berlin')
        return utc_dt.astimezone(german_tz).strftime('%d.%m. %H:%M Uhr')
    except:
        return utc_dt_string

def check_solar_flares():
    """Prüft auf aktuelle Solar Flare Warnungen (Klasse M oder X)."""
    try:
        response = requests.get(URL_ALERTS).json()
        for alert in response:
            # Wir suchen nach Radio Blackout/Flare Alerts (R-Skala)
            if "Space Weather Message Code: ALTTPX" in alert.get('message', ''):
                if "Class M" in alert['message'] or "Class X" in alert['message']:
                    return f"💥 **SOLAR FLARE ALARM!**\nEin starker Flare wurde registriert. Polarlichter in 1-3 Tagen möglich.\n"
    except:
        pass
    return ""

def check_aurora():
    german_tz = pytz.timezone('Europe/Berlin')
    now_germany = datetime.now(german_tz)
    
    # Test-Modus: Wenn manuell gestartet (workflow_dispatch)
    is_test = GITHUB_EVENT_NAME == 'workflow_dispatch'
    
    alert_text = ""
    
    # 1. Solar Flare Check
    flare_info = check_solar_flares()
    alert_text += flare_info

    # 2. Kp-Index Vorhersage
    try:
        fore_res = requests.get(URL_KP_FORECAST).json()
        found_kp = []
        for entry in fore_res[1:]:
            kp_val = float(entry[1])
            if kp_val >= KP_THRESHOLD:
                local_time = utc_to_local(entry[0])
                found_kp.append(f"📈 Kp {kp_val} am {local_time}")
        
        if found_kp:
            alert_text += "\n**Vorhersage hohe Aktivität:**\n" + "\n".join(found_kp[:3]) + "\n"
    except Exception as e:
        print(f"Fehler Forecast: {e}")

    # 3. 30-Minuten-Vorhersage Link
    # (Dieser Link zeigt immer das aktuellste Bild)
    map_link = f"\n🗺️ [Aktuelle 30-Min-Vorhersage]({URL_OVATION_MAP})"

    # Finales Senden
    if alert_text or is_test:
        final_msg = ""
        if is_test:
            final_msg += "🧪 **BOT TESTLAUF**\nVerbindung zur NOAA steht. Zeit in DE: " + now_germany.strftime('%H:%M:%S') + "\n\n"
        
        if alert_text:
            final_msg += "🌌 **AURORA UPDATE** 🌌\n" + alert_text + map_link
        elif is_test:
            final_msg += "Aktuell keine erhöhten Werte (Kp < 6)."
            
        if final_msg:
            send_telegram_message(final_msg)

if __name__ == "__main__":
    check_aurora()
