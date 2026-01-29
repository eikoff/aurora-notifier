import requests
import os
from datetime import datetime
import pytz # Für deutsche Zeitrechnung

# Konfiguration
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']
KP_THRESHOLD = 6

# URLs
URL_FORECAST = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
URL_LIVE = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"

def send_telegram_message(message):
    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(send_url, data={"chat_id": CHAT_ID, "text": message})

def check_aurora():
    # Deutsche Zeit bestimmen
    tz = pytz.timezone('Europe/Berlin')
    now = datetime.now(tz)
    current_hour = now.hour

    alerts = []

    # 1. LIVE-CHECK (Nur zwischen 22:00 und 03:00 Uhr)
    if current_hour >= 22 or current_hour < 3:
        try:
            live_res = requests.get(URL_LIVE).json()
            # Letzten gemessenen Kp-Wert holen
            latest_live = live_res[-1]
            kp_live = float(latest_live['kp_index'])
            if kp_live >= KP_THRESHOLD:
                alerts.append(f"🔴 LIVE-ALARM: Aktueller Kp ist {kp_live}!")
        except Exception as e:
            print(f"Fehler Live-Daten: {e}")

    # 2. FORECAST-CHECK (Immer)
    try:
        fore_res = requests.get(URL_FORECAST).json()
        for entry in fore_res[1:]: # Header überspringen
            kp_val = float(entry[1])
            if kp_val >= KP_THRESHOLD:
                alerts.append(f"📅 Vorhersage: Kp {kp_val} am {entry[0]} UTC")
    except Exception as e:
        print(f"Fehler Forecast-Daten: {e}")

    # Nachricht senden
    if alerts:
        msg = "🌌 **AURORA UPDATE** 🌌\n\n" + "\n".join(alerts[:5])
        send_telegram_message(msg)

if __name__ == "__main__":
    check_aurora()
