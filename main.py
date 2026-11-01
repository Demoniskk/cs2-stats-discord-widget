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


def get_buff163_value():
    try:
        url = f"https://steamcommunity.com/inventory/{STEAM64_ID}/730/2"
        params = {"l": "english", "count": 2000}

        inventory = []

        while True:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()

            if data.get("success") != 1:
                raise Exception(f"Steam inventory failed: {data}")

            descriptions = {
                (d["classid"], d["instanceid"]): d
                for d in data.get("descriptions", [])
            }

            for asset in data.get("assets", []):
                description = descriptions.get(
                    (asset["classid"], asset["instanceid"])
                )

                if description and description.get("market_hash_name"):
                    inventory.append({
                        "name": description["market_hash_name"],
                        "amount": int(asset.get("amount", 1))
                    })

            if not data.get("more_items"):
                break

            params["start_assetid"] = data["last_assetid"]

        quantities = Counter(item["name"] for item in inventory)
        skin_names = list(quantities.keys())

        total_value = 0.0

        for i in range(0, len(skin_names), 500):
            batch = skin_names[i:i + 500]

            r = requests.post(
                "https://api.openskin.dev/v1/prices/batch",
                json={"items": batch},
                timeout=30
            )
            r.raise_for_status()
            data = r.json()

            for item in data.get("results", []):
                name = item.get("item")
                buff = item.get("buff")

                if name and buff and buff.get("ask") is not None:
                    total_value += float(buff["ask"]) * quantities[name]

        return f"{total_value:.2f}"

    except Exception as e:
        print(f"BUFF163 inventory API error: {e}")
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

    inventory_value = get_buff163_value()
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
