import requests
import json
import telebot
import csv
import os
from datetime import datetime

TELEGRAM_BOT_TOKEN = "<TELEGRAM-BOT-TOKEN>"
CHAT_IDS = {
    "all_fuels": ["<CHAT-ID>", "<CHAT-ID>"],  
    "only_benzina": ["<CHAT-ID>"]
}
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

CSV_ANAGRAFICA_URL = 'https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv'
CSV_PREZZI_URL = 'https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv'
JSON_DATA_FILE = "data.json"

DIESEL_ALIASES = ["diesel", "blue diesel", "hi-q diesel", "supreme diesel", "diesel hvo", 
                  "gasolio", "gasolio oro diesel", "s-diesel", "v-power diesel", 
                  "blu diesel alpino", "Gasolio"]

def is_valid_float(value):
    try:
        return float(value)
    except ValueError:
        return None

def fetch_and_combine_csv_data():
    """Scarica i file CSV e li combina in un file JSON leggibile."""
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
        next(reader)
        for row in reader:
            if len(row) >= 9 and row[0].isdigit():
                station_id = row[0]
                data_dict[station_id] = {
                    'gestore': row[1],
                    'indirizzo': f"{row[5]} {row[6]}",
                    'latitudine': is_valid_float(row[8]),
                    'longitudine': is_valid_float(row[9]),
                    'prezzi': {}
                }

    with open("prezzi.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)
        for row in reader:
            if len(row) >= 5 and row[0] in data_dict:
                station_id = row[0]
                carburante = row[1].lower()
                prezzo = is_valid_float(row[2])
                tipo = row[3]  # 0 = servito, 1 = self

                if prezzo is not None:
                    if carburante not in data_dict[station_id]['prezzi']:
                        data_dict[station_id]['prezzi'][carburante] = {"self": None, "servito": None}

                    if tipo == "1":  
                        data_dict[station_id]['prezzi'][carburante]["self"] = prezzo
                    
                    if tipo == "0":  
                        data_dict[station_id]['prezzi'][carburante]["servito"] = prezzo

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

    for station_id, station in data.items():
        if city.lower() in station['indirizzo'].lower():
            for fuel_type in fuel_types:
                for alias in (DIESEL_ALIASES if fuel_type == "diesel" else [fuel_type]):
                    if alias in station['prezzi']:
                        prezzi = station['prezzi'][alias]
                        if prezzi["self"] is not None:
                            if fuel_type not in cheapest_station or prezzi["self"] < cheapest_station[fuel_type]['prezzo_self']:
                                cheapest_station[fuel_type] = {
                                    'gestore': station['gestore'],
                                    'indirizzo': station['indirizzo'],
                                    'prezzo_self': prezzi["self"],
                                    'prezzo_servito': prezzi["servito"],
                                    'latitudine': station['latitudine'],
                                    'longitudine': station['longitudine']
                                }
    return cheapest_station

def send_telegram_message(city, fuel_types, chat_ids):
    cheapest_stations = get_cheapest_station(city, fuel_types)
    if not cheapest_stations:
        for chat_id in chat_ids:
            try:
                bot.send_message(chat_id, f"❌ Nessuna stazione trovata per i carburanti richiesti a {city}.")
            except telebot.apihelper.ApiTelegramException as e:
                print(f"Errore nell'invio del messaggio a {chat_id}: {e}")
        return

    messages = []

    for fuel_type, station in cheapest_stations.items():
        google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={station['latitudine']},{station['longitudine']}"
        prezzo_self = f"{station['prezzo_self']}€/L" if station['prezzo_self'] is not None else "N/D"
        prezzo_servito = f"{station['prezzo_servito']}€/L" if station['prezzo_servito'] is not None else "N/D"

        message = (
            f"🏆 *Miglior distributore a {city} per {fuel_type}* 🏆\n\n"
            f"🏪 *Gestore:* {station['gestore']}\n"
            f"📍 *Indirizzo:* {station['indirizzo']}\n"
            f"⛽ *Prezzo Self:* {prezzo_self}\n"
            f"🛠️ *Prezzo Servito:* {prezzo_servito}\n\n"
            f"🗺️ [Vedi su Google Maps]({google_maps_url})"
        )
        messages.append(message)

    for chat_id in chat_ids:
        try:
            bot.send_message(chat_id, "\n\n".join(messages), parse_mode='Markdown', disable_web_page_preview=True)
        except telebot.apihelper.ApiTelegramException as e:
            print(f"Errore nell'invio del messaggio a {chat_id}: {e}")

def delete_temp_files():
    try:
        os.remove("anagrafica.csv")
        os.remove("prezzi.csv")
        os.remove(JSON_DATA_FILE)
        #print("File temporanei eliminati con successo.")
    except FileNotFoundError:
        print("File già eliminati o non trovati.")

def main():
    city = "<CITY>"
    fetch_and_combine_csv_data()
    send_telegram_message(city, ["benzina", "diesel"], CHAT_IDS["all_fuels"])
    send_telegram_message(city, ["benzina"], CHAT_IDS["only_benzina"])
    delete_temp_files()

if __name__ == "__main__":
    main()
