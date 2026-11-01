import { useEffect, useRef, useState } from "react";

type Session = { code: string; token: string };
type Game = {
  code: string;
  phase: "waiting" | "playing" | "finished";
  players: { category: string; score: number }[];
  you: number;
  server_time: number;
  round?: number;
  deadline?: number;
  question?: { category: string; prompt: string; options: string[] };
  answered?: boolean;
  history: { round: number; category: string; answers: (boolean | null)[] }[];
  winner?: number | null;
};

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function api<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const response = await fetch(`/api/games${path}`, {
    ...options,
    cache: "no-store",
    signal: options.signal ?? AbortSignal.timeout(8000),
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  const data = await response.json();
  if (!response.ok)
    throw new ApiError(
      response.status === 503
        ? "Game storage is unavailable. Configure the backend’s Upstash Redis connection, then try again."
        : data.error || "Request failed",
      response.status,
    );
  return data;
}

function restoreSession(): Session | null {
  try {
    const value = JSON.parse(sessionStorage.getItem("arena-room") || "null");
    return typeof value?.code === "string" && typeof value?.token === "string"
      ? value
      : null;
  } catch {
    return null;
  }
}

export default function GameRoom({
  category,
  nickname,
  petName,
  onBack,
}: {
  category: string;
  nickname: string;
  petName: string;
  onBack: () => void;
}) {
  const [session, setSession] = useState<Session | null>(restoreSession);
  const [game, setGame] = useState<Game | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [remaining, setRemaining] = useState(0);
  const [fatal, setFatal] = useState(false);
  const version = useRef(0);
  const submitting = useRef(false);
  const clock = useRef({ deadline: 0, serverTime: 0, receivedAt: 0 });

  function accept(next: Game) {
    clock.current = {
      deadline: next.deadline || 0,
      serverTime: next.server_time,
      receivedAt: performance.now(),
    };
    setRemaining(
      Math.max(0, Math.ceil((next.deadline || 0) - next.server_time)),
    );
    setGame(next);
  }

  useEffect(() => {
    try {
      if (session)
        sessionStorage.setItem("arena-room", JSON.stringify(session));
      else sessionStorage.removeItem("arena-room");
    } catch {}
  }, [session]);

  useEffect(() => {
    if (!session || fatal || game?.phase === "finished") return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController;
    async function poll() {
      if (submitting.current) {
        timer = setTimeout(poll, 1000);
        return;
      }
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);
      const currentVersion = version.current;
      try {
        const next = await api<Game>(
          `/${session!.code}`,
          { signal: controller.signal },
          session!.token,
        );
        if (!stopped && currentVersion === version.current) {
          accept(next);
          setError("");
        }
      } catch (error) {
        if (!stopped && currentVersion === version.current) {
          setError(
            error instanceof Error
              ? error.message
              : "Connection lost. Retrying…",
          );
          if (error instanceof ApiError && [401, 404].includes(error.status))
            setFatal(true);
        }
      } finally {
        clearTimeout(timeout);
        if (!stopped) timer = setTimeout(poll, 1000);
      }
    }
    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller?.abort();
    };
  }, [session, fatal, game?.phase]);

  useEffect(() => {
    const timer = setInterval(() => {
      const current = clock.current;
      setRemaining(
        Math.max(
          0,
          Math.ceil(
            current.deadline -
              current.serverTime -
              (performance.now() - current.receivedAt) / 1000,
          ),
        ),
      );
    }, 200);
    return () => clearInterval(timer);
  }, []);

  async function enter(join: boolean) {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const next = await api<Session>(
        join ? `/${code.trim().toUpperCase()}/join` : "",
        { method: "POST", body: JSON.stringify({ category }) },
      );
      setFatal(false);
      setGame(null);
      setSession(next);
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Unable to enter room.",
      );
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  async function answer(index: number) {
    if (!session || !game?.round || submitting.current) return;
    submitting.current = true;
    version.current += 1;
    setBusy(true);
    setError("");
    try {
      accept(
        await api<Game>(
          `/${session.code}/answers`,
          {
            method: "POST",
            body: JSON.stringify({ round: game.round, answer: index }),
          },
          session.token,
        ),
      );
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Answer could not be sent. Wait for the next update before retrying.",
      );
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  function leave() {
    version.current += 1;
    setSession(null);
    setGame(null);
    setFatal(false);
    setError("");
    setNotice("");
  }

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(session!.code);
      setNotice("Room code copied. Share it with your opponent.");
    } catch {
      setNotice(
        "Copy the room code shown above and share it with your opponent.",
      );
    }
  }

  const mine = game?.players[game.you];
  const rival = game?.players[game.you === 0 ? 1 : 0];
  return (
    <section className="room-panel">
      {!session ? (
        <>
          <div className="room-loadout">
            <strong>
              {nickname} + {petName}
            </strong>
            <span>SPECIALTY: {category.toUpperCase()}</span>
          </div>
          <p>
            Create a room and share its code, or join your rival. Choose
            different specialties.
          </p>
          <button
            className="retro-button primary"
            disabled={busy}
            onClick={() => void enter(false)}
          >
            {busy ? "CONNECTING…" : "CREATE ROOM →"}
          </button>
          <div className="join-room">
            <label htmlFor="room-code">
              ROOM CODE
              <input
                id="room-code"
                value={code}
                maxLength={6}
                placeholder="ABC123"
                autoComplete="off"
                spellCheck={false}
                onChange={(event) =>
                  setCode(
                    event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""),
                  )
                }
              />
            </label>
            <button
              className="retro-button secondary"
              disabled={busy || code.length !== 6}
              onClick={() => void enter(true)}
            >
              JOIN →
            </button>
          </div>
          <button className="text-button" disabled={busy} onClick={onBack}>
            ← Change specialty
          </button>
        </>
      ) : (
        <>
          <div className="room-code">
            <span>
              ROOM <strong>{session.code}</strong>
            </span>
            <button className="text-button" onClick={() => void copyCode()}>
              COPY CODE
            </button>
          </div>
          {notice && <p role="status">{notice}</p>}
          {!game && !fatal && <p role="status">Connecting to your room…</p>}
          {game?.phase === "waiting" && (
            <div className="waiting-room">
              <span className="cursor">✦</span>
              <h2>Waiting for a rival…</h2>
              <p>
                Share the code. The battle starts as soon as player two joins.
              </p>
              <p>
                Your specialty: {mine?.category}. Your rival must pick a
                different one.
              </p>
            </div>
          )}
          {game && game.phase !== "waiting" && (
            <>
              <div className="battle-score">
                <div>
                  <span>YOU · {mine?.category}</span>
                  <strong>{mine?.score} PTS</strong>
                </div>
                <span>VS</span>
                <div>
                  <span>RIVAL · {rival?.category}</span>
                  <strong>{rival?.score} PTS</strong>
                </div>
              </div>
              {game.phase === "playing" && game.question && (
                <>
                  <div className="round-heading">
                    <span>
                      ROUND {game.round} / 5 ·{" "}
                      {game.question.category.toUpperCase()}
                    </span>
                    <strong role="timer" aria-label="Seconds remaining">
                      {remaining}s
                    </strong>
                  </div>
                  <h2 className="question">{game.question.prompt}</h2>
                  <div className="answer-options">
                    {game.question.options.map((option, index) => (
                      <button
                        key={`${game.round}-${index}`}
                        className="retro-button secondary"
                        disabled={
                          busy || game.answered || remaining === 0 || fatal
                        }
                        onClick={() => void answer(index)}
                      >
                        <span>{String.fromCharCode(65 + index)}.</span> {option}
                      </button>
                    ))}
                  </div>
                  <p role="status">
                    {game.answered
                      ? "Answer locked. Waiting for your rival or the timer…"
                      : remaining === 0
                        ? "Time’s up. Resolving the round…"
                        : busy
                          ? "Sending your answer…"
                          : "Choose your answer before time runs out."}
                  </p>
                  <p className="scoring-note">
                    Correct: 2 points in your specialty, 5 in another. Human
                    answers only for now; Codex is not connected.
                  </p>
                </>
              )}
              {game.phase === "finished" && (
                <div className="match-result">
                  <span>✦</span>
                  <h2>
                    {game.winner === null
                      ? "IT’S A DRAW!"
                      : game.winner === game.you
                        ? "YOU WIN!"
                        : "RIVAL WINS!"}
                  </h2>
                  <p>
                    Five rounds complete. Final score: {mine?.score} –{" "}
                    {rival?.score}.
                  </p>
                  <button className="retro-button primary" onClick={leave}>
                    PLAY AGAIN →
                  </button>
                </div>
              )}
              {game.history.length > 0 && (
                <div className="round-history">
                  <h3>ROUND LOG</h3>
                  {game.history.map((round) => (
                    <div key={round.round}>
                      <span>
                        {round.round}. {round.category}
                      </span>
                      <span>
                        YOU:{" "}
                        {round.answers[game.you] === true
                          ? "HIT"
                          : round.answers[game.you] === false
                            ? "MISS"
                            : "TIMEOUT"}
                      </span>
                      <span>
                        RIVAL:{" "}
                        {round.answers[game.you === 0 ? 1 : 0] === true
                          ? "HIT"
                          : round.answers[game.you === 0 ? 1 : 0] === false
                            ? "MISS"
                            : "TIMEOUT"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
          {game?.phase !== "finished" && (
            <button className="text-button" disabled={busy} onClick={leave}>
              ← Leave room locally
            </button>
          )}
          <p className="scoring-note">
            Leaving does not pause or cancel the match. Refresh this tab to
            reconnect with your saved player token.
          </p>
        </>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}
