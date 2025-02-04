import requests
import json
import time
import telebot
import csv
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

# Configurazione Telegram
TELEGRAM_BOT_TOKEN = "<TELEGRAM-BOT-TOKEN>"
CHAT_IDS = {
    "all_fuels": "<CHAT-ID>",  # Riceve il prezzo più basso per benzina e diesel
    "only_benzina": "<CHAT-ID>>"  # Riceve solo benzina
}
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Configura URL dei dati ministeriali
CSV_ANAGRAFICA_URL = 'https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv'
CSV_PREZZI_URL = 'https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv'
JSON_DATA_FILE = "data.json"

DIESEL_ALIASES = ["diesel", "blue diesel", "hi-q diesel", "supreme diesel", "diesel hvo", "gasolio oro diesel", "s-diesel", "v-power diesel", "blu diesel alpino"]

def deg_to_rad(deg):
    return deg * (3.141592653589793 / 180)

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Raggio della Terra in km
    dlat = deg_to_rad(lat2 - lat1)
    dlon = deg_to_rad(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(deg_to_rad(lat1)) * cos(deg_to_rad(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def is_valid_float(value):
    try:
        return float(value)
    except ValueError:
        return None
def fetch_and_combine_csv_data():
    def fetch_data(url, filename):
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Dati scaricati da {url}")
        else:
            print(f"Errore nel download di {url}")

    fetch_data(CSV_ANAGRAFICA_URL, "anagrafica.csv")
    fetch_data(CSV_PREZZI_URL, "prezzi.csv")

    data_dict = {}
    
    with open("anagrafica.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 9 and row[0].isdigit():
                latitudine = is_valid_float(row[8])
                longitudine = is_valid_float(row[9])
                if latitudine is not None and longitudine is not None:
                    data_dict[row[0]] = {
                        'gestore': row[1],
                        'indirizzo': f"{row[5]} {row[6]}",
                        'latitudine': latitudine,
                        'longitudine': longitudine,
                        'prezzi': {}
                    }
    
    with open("prezzi.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 5 and row[0] in data_dict:
                carburante = row[1].lower()
                prezzo = is_valid_float(row[2])
                if prezzo is not None:
                    if carburante not in data_dict[row[0]]['prezzi'] or prezzo < data_dict[row[0]]['prezzi'][carburante]['prezzo']:
                        data_dict[row[0]]['prezzi'][carburante] = {
                            'prezzo': prezzo,
                            'data': row[4]
                        }
    
    with open(JSON_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_dict, f, indent=2)
    print("Dati aggiornati e salvati in data.json.")

def get_cheapest_station(city, fuel_types):
    try:
        with open(JSON_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("File JSON non trovato. Aggiorno i dati.")
        fetch_and_combine_csv_data()
        return None

    cheapest_station = {}
    
    for station in data.values():
        if city.lower() in station['indirizzo'].lower():
            for fuel_type in fuel_types:
                for alias in (DIESEL_ALIASES if fuel_type == "diesel" else [fuel_type]):
                    if alias in station['prezzi']:
                        prezzo = station['prezzi'][alias]['prezzo']
                        if fuel_type not in cheapest_station or prezzo < cheapest_station[fuel_type]['prezzo']:
                            cheapest_station[fuel_type] = {
                                'gestore': station['gestore'],
                                'indirizzo': station['indirizzo'],
                                'prezzo': prezzo,
                                'latitudine': station['latitudine'],
                                'longitudine': station['longitudine']
                            }
    return cheapest_station

def send_telegram_message(city, fuel_types, chat_id):
    cheapest_stations = get_cheapest_station(city, fuel_types)
    messages = []
    
    for fuel_type, station in cheapest_stations.items():
        google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={station['latitudine']},{station['longitudine']}"
        message = (
            f"🏆 *Miglior distributore a {city} per {fuel_type}* 🏆\n\n"
            f"🏪 *Gestore:* {station['gestore']}\n"
            f"📍 *Indirizzo:* {station['indirizzo']}\n"
            f"⛽ *Prezzo:* {station['prezzo']}€/L\n\n"
            f"🗺️ [Vedi su Google Maps]({google_maps_url})"
        )
        messages.append(message)
    
    if messages:
        bot.send_message(chat_id, "\n\n".join(messages), parse_mode='Markdown', disable_web_page_preview=True)
    else:
        bot.send_message(chat_id, f"❌ Nessuna stazione trovata per i carburanti richiesti a {city}.")


def main():
    city = "<CITY>"
    fetch_and_combine_csv_data()
    
    # Invia il prezzo più basso per benzina e diesel a una chat
    send_telegram_message(city, ["benzina", "diesel"], CHAT_IDS["all_fuels"])
    
    # Invia solo il prezzo della benzina a un'altra chat
    send_telegram_message(city, ["benzina"], CHAT_IDS["only_benzina"])

if __name__ == "__main__":
    main()
