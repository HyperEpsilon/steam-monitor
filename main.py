from dotenv import load_dotenv
import os
import requests
from requests.exceptions import HTTPError
import sqlite3
from http import HTTPStatus
import time
import json

# Imports for Testing
from pprint import pprint
import random


class SteamMonitor():
    def __init__(self, db_path: str) -> None:
        load_dotenv()
        self.connection = self.db_setup(db_path)

    def __enter__(self) -> SteamMonitor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # TODO: Log exception to DB, if any
        # Close DB connection
        self.connection.close()

    def collect_data(self) -> None:
        """One collection pass of all user data"""
        self.timestamp = self.get_current_timestamp()

        # Get user summary
        response = self.get_users_summary()
        if not response:
            return
        
        # Process user summary
        for user_data in response['response']['players']: # pyright: ignore[reportIndexIssue]
            self.record_user_stats(user_data)
    
    def get_users_summary(self) -> dict | bool:
        summaries_data = {
            'key': os.getenv("STEAM_API_KEY"),
            'steamids': os.getenv("STEAM_IDS") # comma separated list of steamids
        }
        return self.fetch_api_json('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/', summaries_data)

    def record_user_stats(self, data: dict) -> None:
        # Sanitize the data and convert to the expected data types
        formatted_data = self.format_data(data)
        
        # update user_states table
        self.update_user_state(formatted_data)

        # call GetOwnedGames api
        # compare game count. If different, add all missing games
        self.compare_and_update_game_count(formatted_data['steam_id'])

        # call GetRecentlyPlayedGames api
        # compare playtime_forever for each game. Add new record if different
        self.update_recent_played_games(formatted_data['steam_id'])

    def update_user_state(self, data: dict) -> None:
        # get most recent user state
        q1 = '''
        SELECT persona_state, game_id, lastlogoff
        FROM user_states
        WHERE steam_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        '''
        cur = self.connection.cursor()
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
        cur.execute(q2, (self.timestamp, data['steam_id'], data['persona_state'], data['game_id'], data['lastlogoff']))
        self.connection.commit()

    def compare_and_update_game_count(self, steam_id: int) -> None:
        # compare game count. If different, add all missing games
        
        # Call API
        owned_games_data = {
            'key': os.getenv("STEAM_API_KEY"),
            'steamid': steam_id,
            'include_appinfo': 1,
            'include_played_free_games': 1,
        }
        response = self.fetch_api_json('https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/', owned_games_data)
        if not response:
            return
        assert isinstance(response, dict)

        # Compare API response "game_count" to DB query based on steam_id and null last_seen
        cur = self.connection.cursor()
        q1 = '''
        SELECT count(game_id)
        FROM owned_games
        WHERE steam_id = ?
        AND timestamp_removed IS NULL
        '''
        res = cur.execute(q1, (steam_id,))
        db_game_count = res.fetchone()[0]
        if db_game_count == response['response']['game_count']:
            return

        # If different, query DB with all rows and compare to API response
        q2 = '''
        SELECT game_id
        FROM owned_games
        WHERE steam_id = ?
        AND timestamp_removed IS NULL
        '''
        res = cur.execute(q2, (steam_id,))
        db_games = res.fetchall()

        # Dict comprehension to transform API response into {appid: name}
        api_games = {game['appid']:game['name'] for game in response['response']['games']}

        # Loop through all rows from DB, removing from API dict any values in DB
        removed_games = []
        for db_game in db_games:
            val = api_games.pop(db_game[0], None)
            if val == None:
                removed_games.append((db_game[0]))

        # set 'last_seen' for any games in DB but not in API
        if len(removed_games) > 0:
            q3 = '''
            UPDATE owned_games
            SET timestamp_removed = ?
            WHERE steam_id = ?
            AND game_id = ?
            AND timestamp_removed IS NULL
            '''
            cur.execute(q3, [(self.timestamp, steam_id, game_id) for game_id in removed_games])
        
        # Add new row for all remaining games in API dict
        if len(api_games) > 0:
            # Insert or ignore list into 'games' table first
            q4 = '''
            INSERT OR IGNORE
            INTO games (game_id, name)
            VALUES (?, ?)
            '''
            cur.executemany(q4, [(game_id, api_games[game_id]) for game_id in api_games])
            q5 = '''
            INSERT INTO owned_games (game_id, steam_id, timestamp_added)
            values (?, ?, ?)
            '''
            cur.executemany(q5, [(game_id, steam_id, self.timestamp) for game_id in api_games])
        self.connection.commit()
        return
        

    def update_recent_played_games(self, steam_id: int) -> None:
        recent_played_games_data = {
            'key': os.getenv("STEAM_API_KEY"),
            'steamid': steam_id,
        }

        response = self.fetch_api_json('http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/', recent_played_games_data)
        if not response or response['response']['total_count'] == 0: # pyright: ignore[reportIndexIssue]
            return

        cur = self.connection.cursor()
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
        for game in response['response']['games']: # pyright: ignore[reportIndexIssue]
            # query DB, if playtime is different, then insert new record
            res = cur.execute(q2, (steam_id, game['appid']))
            row = res.fetchone()

            if row == (game['playtime_forever'],):
                continue

            try:
                cur.execute(q1, (self.timestamp, steam_id, game['appid'], game['playtime_forever']))
            except sqlite3.IntegrityError as ex:
                cur.execute(q3, (game['appid'], game['name']))
                cur.execute(q1, (self.timestamp, steam_id, game['appid'], game['playtime_forever']))
        self.connection.commit()

    def db_setup(self, path: str) -> sqlite3.Connection:
        connection = sqlite3.connect(path)
        cursor = connection.cursor()
        cursor.execute(' PRAGMA foreign_keys=ON; ')
        connection.commit()
        return connection

    def get_current_timestamp(self) -> int:
            cur = self.connection.cursor()
            res = cur.execute('SELECT unixepoch()').fetchone()
            return res[0]

    def fetch_api_json(self, url: str, params: dict) -> dict | bool:
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
        msg = None
        for n in range(retries):
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()

                return response.json()

            except HTTPError as exc:
                code = exc.response.status_code # pyright: ignore[reportOptionalMemberAccess]
                msg = str(exc)

                # Retry connection if status code is retryable
                if code in retry_codes:
                    time.sleep(n)
                    continue

                # If status code is not retryable, go to logging
                break

        # Log error if max retries or code not retryable
        q1 = '''
        INSERT INTO errors (timestamp, timestamp_program, status_code, message, params, source)
        VALUES (unixepoch(), ?, ?, ?, ?, ?)
        '''
        cur = self.connection.cursor()
        params_without_api_key = {i:params[i] for i in params if i !='key'}
        params_without_api_key['url'] = url
        cur.execute(q1, (self.timestamp, code, msg, json.dumps(params_without_api_key), 'api'))
        self.connection.commit()

        return False

    @staticmethod
    def format_data(data: dict) -> dict:
        return {
                'steam_id': int(data['steamid']),
                'persona_state': data["personastate"],
                'game_id': int(data.get('gameid')) if data.get('gameid') is not None else None, # pyright: ignore[reportArgumentType]
                'lastlogoff': data['lastlogoff']
            }


def main():
    with SteamMonitor('./database/steam_monitor.db') as monitor:
        monitor.collect_data()

if __name__ == "__main__":
    main()
