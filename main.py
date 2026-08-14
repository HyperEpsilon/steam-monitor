from dotenv import load_dotenv
import os
import requests
from requests.exceptions import HTTPError
from pprint import pprint
import sqlite3
from http import HTTPStatus
import time

def main():
    load_dotenv()
    try:
        connection = db_setup('./database/steam_monitor.db')

        response = get_users_summary()
        timestamp = get_current_timestamp(connection)

        for user_data in response.json()['response']['players']:
            record_user_stats(connection, user_data, timestamp)
    finally:
        connection.close() # type: ignore

def db_setup(path):
    connection = sqlite3.connect(path)
    cursor = connection.cursor()
    cursor.execute(' PRAGMA foreign_keys=ON; ')
    connection.commit()
    return connection

def fetch_api_json(connection: sqlite3.Connection, url: str, params: dict):
    # Adapted from: https://stackoverflow.com/a/61463451
    retries = 3
    retry_codes = [
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    ]

    code = None
    for n in range(retries):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()

            return response.json

        except HTTPError as exc:
            code = exc.response.status_code # pyright: ignore[reportOptionalMemberAccess]

            # Retry connection if status code is retryable
            if code in retry_codes:
                time.sleep(n)
                continue

            # If status code is not retryable, go to logging
            break

    # Log error if max retries or code not retryable
    q1 = '''
    INSERT INTO errors (timestamp, timestamp_program, status_code, message, source)
    VALUES (unixepoch(), ?, ?, ?, ?)
    '''
    cur = connection.cursor()
    params_without_api_key = {i:params[i] for i in params if i !='key'}
    cur.execute(q1, (None, code, params_without_api_key, 'api'))
    connection.commit()

    return False
        

def get_users_summary():
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
    # Sanitize the data and convert to the expected data types
    formatted_data = format_data(data)
    
    # update user_states table
    update_user_state(connection, formatted_data, timestamp)

    # call GetOwnedGames api
    # compare game count. If different, add all missing games

    # call GetRecentlyPlayedGames api
    # compare playtime_forever for each game. Add new record if different
    update_recent_played_games(connection, formatted_data['steam_id'], timestamp)

def update_user_state(connection, data, timestamp):
    # get most recent user state
    q1 = '''
    SELECT persona_state, game_id, lastlogoff
    FROM user_states
    WHERE steam_id = ?
    ORDER BY timestamp DESC
    LIMIT 1
    '''
    cur = connection.cursor()
    res = cur.execute(q1, (data['steam_id'],)) # tuple of length one required for sqlite
    row = res.fetchone()

    # compare stored user state to current state, return if identical
    # data.get is used because 'gameid' is not always a part of the response (when a user isn't playing a game)
    if row is not None and row == (data['persona_state'], data['game_id'], data['lastlogoff']):
        return

    # if different, add new row
    q2 = '''
    INSERT INTO user_states (timestamp, steam_id, persona_state, game_id, lastlogoff)
    VALUES (?, ?, ?, ?, ?)
    '''
    cur.execute(q2, (timestamp, data['steam_id'], data['persona_state'], data['game_id'], data['lastlogoff']))
    connection.commit()

def update_recent_played_games(connection, steam_id, timestamp):
    recent_played_games_data = {
        'key': os.getenv("STEAM_API_KEY"),
        'steamid': steam_id,
    }

    response = requests.get('http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/', params=recent_played_games_data)
    # TODO: Add response code checking and error handling

    if response.json()['response']['total_count'] == 0:
        return

    cur = connection.cursor()
    q2 = '''
    SELECT playtime_forever
    FROM gameplay_times
    WHERE steam_id = ?
    AND game_id = ?
    ORDER BY timestamp DESC
    LIMIT 1
    '''
    q1 = '''
    INSERT INTO gameplay_times (timestamp, steam_id, game_id, playtime_forever)
    VALUES (?, ?, ?, ?)
    '''
    q3 = '''
    INSERT INTO games (game_id, name)
    VALUES (?, ?)
    '''

    # Check each game
    for game in response.json()['response']['games']:
        # query DB, if playtime is different, then insert new record
        res = cur.execute(q2, (steam_id, game['appid']))
        row = res.fetchone()

        if row == (game['playtime_forever'],):
            continue

        try:
            cur.execute(q1, (timestamp, steam_id, game['appid'], game['playtime_forever']))
        except sqlite3.IntegrityError as ex:
            cur.execute(q3, (game['appid'], game['name']))
            cur.execute(q1, (timestamp, steam_id, game['appid'], game['playtime_forever']))
    connection.commit()

def get_current_timestamp(connection):
    cur = connection.cursor()
    res = cur.execute('SELECT unixepoch()').fetchone()
    return res[0]

def format_data(data):
    return {
            'steam_id': int(data['steamid']),
            'persona_state': data["personastate"],
            'game_id': int(data.get('gameid')) if data.get('gameid') is not None else None,
            'lastlogoff': data['lastlogoff']
        }

if __name__ == "__main__":
    main()
