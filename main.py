from dotenv import load_dotenv
import os
import requests
from pprint import pprint
import sqlite3

def main():
    try:
        connection = db_setup('./database/steam_monitor.db')

        response = get_users_summary()
        timestamp = get_current_timestamp(connection)

        for user_data in response.json()['response']['players']:
            record_user_stats(connection, user_data, timestamp)
    finally:
        connection.close()

def db_setup(path):
    connection = sqlite3.connect(path)
    cursor = connection.cursor()
    cursor.execute(' PRAGMA foreign_keys=ON; ')
    connection.commit()
    return connection

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


def record_user_stats(connection, data, timestamp):
    pass
    # update user_states table

    # call GetOwnedGames api
    # compare game count. If different, add all missing games

    # call GetRecentlyPlayedGames api
    # compare playtime_forever for each game. Add new record if different

def get_current_timestamp(connection):
    cur = connection.cursor()
    res = cur.execute('SELECT unixepoch()').fetchone()
    return res[0]


if __name__ == "__main__":
    main()
