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
    update_user_state(connection, data, timestamp)

    # call GetOwnedGames api
    # compare game count. If different, add all missing games

    # call GetRecentlyPlayedGames api
    # compare playtime_forever for each game. Add new record if different

def update_user_state(connection, data, timestamp):
    new_data = {
        'steam_id': int(data['steamid']),
        'persona_state': data["personastate"],
        'game_id': int(data.get('gameid')) if data.get('gameid') is not None else None,
        'lastlogoff': data['lastlogoff']
    }


    # get most recent user state
    q1 = '''
    SELECT persona_state, game_id, lastlogoff
    FROM user_states
    WHERE steam_id = ?
    ORDER BY timestamp DESC
    LIMIT 1
    '''
    cur = connection.cursor()
    res = cur.execute(q1, (new_data['steam_id'],)) # tuple of length one required for sqlite
    row = res.fetchone()

    # compare stored user state to current state, return if identical
    # data.get is used because 'gameid' is not always a part of the response (when a user isn't playing a game)
    if row is not None and row == (new_data['persona_state'], new_data['game_id'], new_data['lastlogoff']):
        return

    # if different, add new row
    q2 = '''
    INSERT INTO user_states (timestamp, steam_id, persona_state, game_id, lastlogoff)
    VALUES (?, ?, ?, ?, ?)
    '''
    cur.execute(q2, (timestamp, new_data['steam_id'], new_data['persona_state'], new_data['game_id'], new_data['lastlogoff']))
    connection.commit()

def get_current_timestamp(connection):
    cur = connection.cursor()
    res = cur.execute('SELECT unixepoch()').fetchone()
    return res[0]


if __name__ == "__main__":
    main()
