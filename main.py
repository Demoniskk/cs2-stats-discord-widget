import requests
import json
import time
import schedule
import os
 
DISCORD_APPLICATION_ID = os.getenv("DISCORD_APPLICATION_ID")
DISCORD_USER_ID = os.getenv("DISCORD_USER_ID")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LEETIFY_KEY = os.getenv("LEETIFY_KEY")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
STEAM64_ID = os.getenv("STEAM64_ID")
WINGMAN_RANKS = {
    1: "Silver 1",
    2: "Silver 2",
    3: "Silver 3",
    4: "Silver 4",
    5: "Silver Elite",
    6: "Silver Elite Master",
    7: "Gold Nova 1",
    8: "Gold Nova 2",
    9: "Gold Nova 3",
    10: "Gold Nova Master",
    11: "Master Guardian 1",
    12: "Master Guardian 2",
    13: "Master Guardian Elite",
    14: "Distinguished Master Guardian",
    15: "Legendary Eagle",
    16: "Legendary Eagle Master",
    17: "Supreme Master First Class",
    18: "The Global Elite"
}
 
last_premier = None
last_wingman = None
last_name = None
last_value = None
last_hours = None
 
def get_leetify_data():
    url = f"https://api-public.cs-prod.leetify.com/v3/profile?steam64_id={STEAM64_ID}"
    headers = {"_leetify_key": LEETIFY_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Leetify API error: {e}")
        return None
 
def get_priceempire_value():
    url = f"https://pricempire.com/api-data/v1/inventory?steam_id={STEAM64_ID}&context=2&app_id=730&force=false"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Get buff163 total value from provider_breakdown
        total_value = data.get("provider_breakdown", {}).get("buff163", {}).get("totalValue", 0)
        # Convert from cents to dollars (divide by 100) and format with 2 decimals
        return f"{total_value / 100:.2f}"
    except Exception as e:
        print(f"PriceEmpire API error: {e}")
        return "0.00"
 
def get_cs2_hours():
    url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?steamid={STEAM64_ID}&key={STEAM_API_KEY}&format=json&appids_filter=730"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        games = data.get("response", {}).get("games", [])
        for game in games:
            if game.get("appid") == 730:
                hours = game.get("playtime_forever", 0) // 60
                return str(hours)
        
        return "0"
    except Exception as e:
        print(f"Steam API error: {e}")
        return "0"
 
def send_discord_update(premier, wingman, player_name, inventory_value, cs2_hours):
    wingman_rank = WINGMAN_RANKS.get(wingman, str(wingman))
    
    profile_data = {
        "data": {
            "dynamic": [
                {"type": 1, "name": "name", "value": player_name},
                {"type": 1, "name": "hours", "value": cs2_hours},
                {"type": 1, "name": "value", "value": inventory_value},
                {"type": 1, "name": "premier", "value": str(premier)},
                {"type": 1, "name": "wingman", "value": wingman_rank}
            ]
        }
    }
    
    url = f"https://discord.com/api/v9/applications/{DISCORD_APPLICATION_ID}/users/{DISCORD_USER_ID}/identities/0/profile"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "User-Agent": "DiscordBot (https://github.com/discord/discord-api-docs, 1.0.0)"
    }
    
    response = requests.patch(url, headers=headers, data=json.dumps(profile_data))
    print(f"Discord update: {response.status_code} - {response.text if response.text else 'Success'}")
 
def check_and_update():
    global last_premier, last_wingman, last_name, last_value, last_hours
    
    print("Fetching Leetify data...")
    data = get_leetify_data()
    if not data:
        print("Failed to get Leetify data")
        return
    
    print("Fetching PriceEmpire value...")
    inventory_value = get_priceempire_value()
    
    print("Fetching CS2 hours...")
    cs2_hours = get_cs2_hours()
    
    premier = data.get("ranks", {}).get("premier")
    wingman = data.get("ranks", {}).get("wingman")
    player_name = data.get("name")
    
    print(f"Current: premier={premier}, wingman={wingman}, name={player_name}, value={inventory_value}, hours={cs2_hours}")
    print(f"Last: premier={last_premier}, wingman={last_wingman}, name={last_name}, value={last_value}, hours={last_hours}")
    
    if premier != last_premier or wingman != last_wingman or player_name != last_name or inventory_value != last_value or cs2_hours != last_hours:
        print("Changes detected, sending Discord update...")
        send_discord_update(premier, wingman, player_name, inventory_value, cs2_hours)
        last_premier = premier
        last_wingman = wingman
        last_name = player_name
        last_value = inventory_value
        last_hours = cs2_hours
    else:
        print("No changes")
 
check_and_update()
schedule.every(5).minutes.do(check_and_update)
 
print("Starting scheduler... (checking every 5 minutes)")
while True:
    schedule.run_pending()
    time.sleep(1)