BEGIN TRANSACTION;
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
