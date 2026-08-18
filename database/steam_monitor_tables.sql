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
COMMIT;
