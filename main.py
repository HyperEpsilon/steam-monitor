from dotenv import load_dotenv
import os
import requests
from pprint import pprint

def main():
    response = get_users_summary()

    for user_data in response.json()['response']['players']:
        record_user_stats(user_data)

def get_users_summary():
    load_dotenv()

    api_key = os.getenv("STEAM_API_KEY")
    steam_ids = os.getenv("STEAM_IDS") # comma separated list of steamids

    summaries_data = {
        'key': api_key,
        'steamids': steam_ids
    }

    request = requests.get('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/', params=summaries_data)

    # TODO: Add response code checking and error handling
    return request


def record_user_stats(data):
    pass
    # update user_states table

    # call GetOwnedGames api
    # compare game count. If different, add all missing games

    # call GetRecentlyPlayedGames api
    # compare playtime_forever for each game. Add new record if different


if __name__ == "__main__":
    main()
