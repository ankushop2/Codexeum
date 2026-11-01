import { useEffect, useState } from "react";

type Entry = {
  rank: number;
  nickname: string;
  pet: string;
  points: number;
  games: number;
  wins: number;
};

export default function Leaderboard({ nickname }: { nickname: string }) {
  const [players, setPlayers] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    fetch("/api/leaderboard", { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok)
          throw new Error("Leaderboard unavailable. Try refreshing.");
        const data = await response.json();
        setPlayers(data.players);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [refresh]);

  return (
    <section className="leaderboard" aria-label="Leaderboard">
      <div className="round-heading">
        <h3>🏆 PET LEAGUE</h3>
        <button
          className="text-button"
          disabled={loading}
          onClick={() => setRefresh((value) => value + 1)}
        >
          REFRESH
        </button>
      </div>
      <p>Climb the ranks! Total points from completed battles · Top 20</p>
      {loading ? (
        <p role="status">Loading rankings…</p>
      ) : error ? (
        <p role="alert">{error}</p>
      ) : players.length === 0 ? (
        <p>Be the first! Finish a battle to join the league.</p>
      ) : (
        <div className="leaderboard-scroll">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Trainer / Pet</th>
                <th>Points</th>
                <th>Wins</th>
                <th>Games</th>
              </tr>
            </thead>
            <tbody>
              {players.map((player) => (
                <tr
                  key={player.rank}
                  className={
                    player.nickname.trim().toLowerCase() ===
                    nickname.trim().toLowerCase()
                      ? "your-ranking"
                      : ""
                  }
                >
                  <td>#{player.rank}</td>
                  <td>
                    <strong>{player.nickname}</strong>
                    <br />
                    {player.pet}
                  </td>
                  <td>{player.points}</td>
                  <td>{player.wins}</td>
                  <td>{player.games}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p>
        Use the same nickname to keep climbing. Nicknames are public and shared;
        no account is required.
      </p>
    </section>
  );
}
