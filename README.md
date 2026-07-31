# Program Flow
## Monitoring
Run a cron job every minute 

Generate a unix timestamp and use it for all db inserts

Run `GetPlayerSummaries`

Process each entry of response, which will be one friend each (and me)

Pass each user response to a function which will make two calls

1. `GetOwnedGames` (count free games too). Check if `game_count` is different from the count we have stored
2. `GetRecentlyPlayedGames`. Compare `playtime_forever` for each game in list and add new record if different

Use exponential backoff for possible rate-limiting. Should be fine at 100,000 requests per day (I use ~21,000)

If anything errors out in the responses, log it in the DB. If the whole program errors, log that too.

## Error checking
Write a script that fetches the most error access recent record that is further than 10 mins ago (subtract from UNIX timestamp). Then fetch all errors that have occurred during that time period and log a new access.

Alternatively, modify script so I can define a customer range. In the form of `show_errors [min_time] [max_time]`. If `min_time` not provided, fetch records as above. If `max_time` not provided, fetch up until current time.

## Visualizing Data
- [ ] figure out how to connect concurrent blocks of game time (30 mins when game is running)
	- Can I do this in a view?
	- This will be the basis of basically all analysis
	- [sql - Combine consecutive date ranges - Stack Overflow](https://stackoverflow.com/questions/15783315/combine-consecutive-date-ranges) 
	- 
- Check if friends are offline (`persona_state` not 1) while playing games (check via playtime counter)
- Check if friends are playing the same game at the same time. Suspect multiplayer?
- comparing the date of purchase on owned games vs games that are played can be used to figure out if someone is playing games not in their library
	- demos or steam family share probably. Not sure best way to determine (maybe if Demo is in title?)

