BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "error_access_logs" (
	"timestamp"	INTEGER NOT NULL,
	PRIMARY KEY("timestamp")
);
CREATE TABLE IF NOT EXISTS "errors" (
	"timestamp"	INTEGER NOT NULL,
	"timestamp_program"	INTEGER,
	"status_code"	INTEGER,
	"message"	TEXT,
	"params"	TEXT,
	"source"	TEXT,
	PRIMARY KEY("timestamp")
);
CREATE TABLE IF NOT EXISTS "gameplay_times" (
	"timestamp"	INTEGER NOT NULL,
	"steam_id"	INTEGER NOT NULL,
	"game_id"	INTEGER NOT NULL,
	"playtime_forever"	INTEGER NOT NULL,
	PRIMARY KEY("timestamp","steam_id","game_id"),
	FOREIGN KEY("game_id") REFERENCES "games"("game_id"),
	FOREIGN KEY("steam_id") REFERENCES "users"("steam_id")
);
CREATE TABLE IF NOT EXISTS "games" (
	"game_id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"free"	INTEGER NOT NULL DEFAULT 0,
	"demo"	INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY("game_id")
);
CREATE TABLE IF NOT EXISTS "owned_games" (
	"rowid"	INTEGER NOT NULL,
	"game_id"	INTEGER NOT NULL,
	"steam_id"	INTEGER NOT NULL,
	"timestamp_added"	INTEGER NOT NULL,
	"timestamp_removed"	INTEGER,
	PRIMARY KEY("rowid" AUTOINCREMENT),
	FOREIGN KEY("game_id") REFERENCES "games"("game_id"),
	FOREIGN KEY("steam_id") REFERENCES "users"("steam_id")
);
CREATE TABLE IF NOT EXISTS "user_states" (
	"timestamp"	INTEGER,
	"steam_id"	INTEGER,
	"persona_state"	INTEGER NOT NULL,
	"game_id"	INTEGER,
	"lastlogoff"	INTEGER NOT NULL,
	PRIMARY KEY("timestamp","steam_id"),
	FOREIGN KEY("steam_id") REFERENCES "users"("steam_id")
);
CREATE TABLE IF NOT EXISTS "users" (
	"steam_id"	INTEGER NOT NULL,
	"username"	TEXT NOT NULL,
	"realname"	TEXT,
	PRIMARY KEY("steam_id")
);
CREATE VIEW formatted_gameplay_times

AS
	SELECT datetime(gt.timestamp, 'unixepoch', 'localtime') AS 'Time recorded',
		   u.username,
		   gt.game_id,
		   g.name,
		   concat(floor(gt.playtime_forever / 60), ':', gt.playtime_forever % 60) as 'playtime HH:MM',
		   gt.playtime_forever
	FROM gameplay_times gt
	JOIN games g on gt.game_id = g.game_id
	JOIN users u on gt.steam_id = u.steam_id;
CREATE VIEW formatted_owned_games

AS
	SELECT og.rowid,
	       u.username,
		   og.game_id,
		   g.name,
		   datetime(og.timestamp_added, 'unixepoch', 'localtime') AS 'Date first seen',
		   datetime(og.timestamp_removed, 'unixepoch', 'localtime') AS 'Date removed'
	FROM owned_games og
	JOIN games g on og.game_id = g.game_id
	JOIN users u on og.steam_id = u.steam_id;
CREATE VIEW formatted_user_states

AS
	SELECT datetime(us.timestamp, 'unixepoch', 'localtime') AS 'Time recorded',
	       u.username,
		   CASE us.persona_state WHEN 0 THEN 'Offline' WHEN 1 THEN 'Online' WHEN 2 THEN 'Busy' WHEN 3 THEN 'Away' WHEN 4 THEN 'Snooze' WHEN 5 THEN 'Looking to trade' WHEN 6 THEN 'Looking to play' END as 'Persona State',
		   us.game_id,
		   g.name,
		   datetime(us.lastlogoff, 'unixepoch', 'localtime') AS 'Last Logoff'
	FROM user_states us
	LEFT JOIN games g on us.game_id = g.game_id
	JOIN users u on us.steam_id = u.steam_id;
COMMIT;
