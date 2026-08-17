import dotenv
import logging

from services.telegram import send_deal
from services.steam import get_game_details, find_game_id, game_from_details

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def is_deal(game_data):
    """The current application regards any positive Steam discount as a deal."""
    price = game_data.get("price_overview", game_data)
    return price.get("discount_percent", 0) > 0


def run_cli():
    while True:
        game_querry = input("Enter game name: ")

        game_id = find_game_id(game_querry)
        if not game_id:
            print("Game not found")
            continue

        game_data = game_from_details(game_id, get_game_details(game_id)) or {}

        print(game_data.get("name", "Game not found"))
        print(game_data.get("final_formatted", "Price not found"))
        print(game_data.get("short_description", "Description not found"))

        if is_deal(game_data):
            send_deal({"name": game_data["name"], "price_overview": {
                "initial_formatted": game_data["initial_formatted"], "final_formatted": game_data["final_formatted"],
                "discount_percent": game_data["discount_percent"],
            }}, game_id)
            # TODO: persist sent deals here to prevent notifications across repeated searches.


if __name__ == "__main__":
    run_cli()
