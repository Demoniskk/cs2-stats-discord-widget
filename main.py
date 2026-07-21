import requests
import json
import os

STATE_FILE = "state.json"

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

# ---------------- STATE HANDLING ---------------- #

def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "premier": None,
            "wingman": None,
            "name": None,
            "value": None,
            "hours": None
        }

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ---------------- API CALLS ---------------- #

def get_leetify_data():
    url = f"https://api-public.cs-prod.leetify.com/v3/profile?steam64_id={STEAM64_ID}"
    headers = {"_leetify_key": LEETIFY_KEY}

    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Leetify API error: {e}")
        return None


def get_priceempire_value():
    url = f"https://pricempire.com/api-data/v1/inventory?steam_id={STEAM64_ID}&context=2&app_id=730&force=false"

    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()

        total_value = data.get("provider_breakdown", {}).get("buff163", {}).get("totalValue", 0)
        return f"{total_value / 100:.2f}"
    except Exception as e:
        print(f"PriceEmpire API error: {e}")
        return "0.00"


def get_cs2_hours():
    url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?steamid={STEAM64_ID}&key={STEAM_API_KEY}&format=json&appids_filter=730"

    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()

        games = data.get("response", {}).get("games", [])
        for game in games:
            if game.get("appid") == 730:
                return str(game.get("playtime_forever", 0) // 60)

        return "0"
    except Exception as e:
        print(f"Steam API error: {e}")
        return "0"

# ---------------- DISCORD UPDATE ---------------- #

def send_discord_update(premier, wingman, player_name, inventory_value, cs2_hours):
    wingman_rank = WINGMAN_RANKS.get(wingman, str(wingman))

    payload = {
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
    }

    r = requests.patch(url, headers=headers, data=json.dumps(payload))
    print(f"Discord update: {r.status_code} - {r.text}")

# ---------------- MAIN LOGIC ---------------- #

def check_and_update():
    print("Running update check...")

    last_state = load_state()

    data = get_leetify_data()
    if not data:
        print("Failed to get Leetify data")
        return

    inventory_value = get_priceempire_value()
    cs2_hours = get_cs2_hours()

    premier = data.get("ranks", {}).get("premier")
    wingman = data.get("ranks", {}).get("wingman")
    player_name = data.get("name")

    print(f"Current: {premier}, {wingman}, {player_name}, {inventory_value}, {cs2_hours}")
    print(f"Last: {last_state}")

    if (
        premier != last_state["premier"]
        or wingman != last_state["wingman"]
        or player_name != last_state["name"]
        or inventory_value != last_state["value"]
        or cs2_hours != last_state["hours"]
    ):
        print("Change detected, updating Discord...")

        send_discord_update(
            premier,
            wingman,
            player_name,
            inventory_value,
            cs2_hours
        )

        new_state = {
            "premier": premier,
            "wingman": wingman,
            "name": player_name,
            "value": inventory_value,
            "hours": cs2_hours
        }

        save_state(new_state)

    else:
        print("No changes")


if __name__ == "__main__":
    check_and_update()
