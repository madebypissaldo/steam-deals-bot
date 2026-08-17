import requests
import dotenv
import os
import json

dotenv.load_dotenv()

api_key = os.getenv("STEAM_API_KEY")



with open("data/games_appid.json", "r") as f:
    games_appid = json.load(f)


def get_gameID(game_querry):
    for game in games_appid:
        if game["name"].lower() == game_querry.lower():
            return game["appid"]


def get_details(game_id):

    r = requests.get(f"https://store.steampowered.com/api/appdetails?appids={game_id}&cc=br&l=portuguese&key={api_key}")
    querry= json.loads(r.text)
    return querry
while True:
    game_querry = input("Enter game name: ")

    game_id = get_gameID(game_querry)

    details = get_details(game_id)

    print(details.get(str(game_id), {}).get("data", {}).get("name", "Game not found"))
    print(details.get(str(game_id), {}).get("data", {}).get("price_overview", {}).get("final_formatted", "Price not found"))
    print(str(details.get(str(game_id), {}).get("data", {}).get("price_overview", {}).get("discount_percent", "Discount not found"))+"% OFF")
    print(details.get(str(game_id), {}).get("data", {}).get("short_description", "Description not found"))
