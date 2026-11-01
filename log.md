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
Setup chooses player or bot before showing room options or difficulty.
Bot difficulty UI hides correct-answer counts.
Round results play once per round: correct pets cheer, wrong or timed-out pets receive falling arrows.
Round effects last three seconds and do not block answers or change server deadlines.
Reduced-motion users see static round feedback instead of movement.
Battle intro lasts three seconds before the first 30-second question begins.
Imported sprites use six idle-row frames for the intro; single images and starter pets slide in.
All five questions target UK A-level difficulty, including the random category.
Pet help on hard questions uses the OpenAI Decisions API to eliminate exactly two wrong options.
Hard-question help remains optional; player skill cannot be guaranteed by question generation.
