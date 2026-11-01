Each game has two players and five questions.
Player 1 creates a game and shares a code with player 2.
Each round has a 30-second timeout.
Advance immediately when both players answer (assumed).
Each game has one category per player and one random category.
Question generation supplies two questions from each player category and one from the random category.
Correct trainer answers score 5; correct pet, team or bot answers score 2 (existing main).
Equal scores are a draw.
OpenAI generates questions after both players ready up.
Players choose different categories (assumed).
The first round begins after a player presses Start; later rounds begin when the previous round resolves.
Expired rounds advance on the next game request (assumed).
Games expire after one hour without updates (assumed).
Out of scope: matchmaking and forfeits.
Scores are revealed after each round resolves.
Either player may start after questions are ready (assumed).
Bot answers after two seconds without an AI call.
Bot difficulty bases are easy 2, med 3, hard 4 correct answers out of five.
Bot correct-answer count gets a uniform random offset of -1, 0 or +1 per game (assumed).
Bot difficulty defaults to med (assumed).
