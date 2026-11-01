import { useEffect, useRef, useState } from "react";
import BattleArena from "./BattleArena";
import type { BattlePet, Fighter } from "./BattleArena";

type Session = { code: string; token: string };
type Game = {
  code: string;
  phase: "waiting" | "generating" | "ready" | "playing" | "finished";
  players: (Fighter & { ready: boolean; bot: boolean })[];
  you: number;
  server_time: number;
  round?: number;
  deadline?: number;
  question?: { category: string; prompt: string; options: string[] };
  answered?: boolean;
  history: {
    round: number;
    category: string;
    answers: (boolean | null)[];
    sources?: (string | null)[];
  }[];
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
    signal:
      options.signal ??
      AbortSignal.timeout(path.endsWith("/ready") ? 90000 : 8000),
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  const data = await response.json();
  if (!response.ok)
    throw new ApiError(
      response.status === 503 && data.error === "Game storage unavailable"
        ? "Game storage is unavailable. Configure the backend’s Upstash Redis connection, then try again."
        : data.error || data.detail || "Request failed",
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
  pet,
  columns,
  rows,
  onBack,
}: {
  category: string;
  nickname: string;
  petName: string;
  pet: BattlePet;
  columns: number;
  rows: number;
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
  const [petPrompt, setPetPrompt] = useState("");
  const [petBusy, setPetBusy] = useState(false);
  const [petReply, setPetReply] = useState<{
    round: number;
    text: string;
    answer: number | null;
    needsHelp: boolean;
    guided: boolean;
  } | null>(null);
  const petAttempt = useRef("");
  const petRequest = useRef(0);
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

  async function portrait(): Promise<BattlePet> {
    if (!pet.image) return { name: pet.name, color: pet.color };
    const image = new Image();
    image.src = pet.image;
    await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 128;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Unable to prepare pet portrait.");
    context.imageSmoothingEnabled = false;
    const width = image.naturalWidth / columns;
    const height = image.naturalHeight / rows;
    const scale = Math.min(128 / width, 128 / height);
    context.drawImage(
      image,
      0,
      0,
      width,
      height,
      (128 - width * scale) / 2,
      (128 - height * scale) / 2,
      width * scale,
      height * scale,
    );
    return {
      name: pet.name,
      color: pet.color,
      image: canvas.toDataURL("image/png"),
    };
  }

  async function enter(join: boolean, mode = "player") {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const next = await api<Session>(
        join ? `/${code.trim().toUpperCase()}/join` : "",
        {
          method: "POST",
          body: JSON.stringify({
            category,
            mode,
            profile: { nickname, pet: await portrait() },
          }),
        },
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

  async function lobbyAction(action: "ready" | "start") {
    if (!session || submitting.current) return;
    submitting.current = true;
    version.current += 1;
    setBusy(true);
    setError("");
    try {
      accept(
        await api<Game>(
          `/${session.code}/${action}`,
          { method: "POST" },
          session.token,
        ),
      );
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Request failed. Try again.",
      );
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  async function answer(
    index: number,
    source: "trainer" | "pet" | "team" = "trainer",
  ) {
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
            body: JSON.stringify({ round: game.round, answer: index, source }),
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

  async function askPet(prompt = "") {
    if (!session || !game?.round) return;
    const round = game.round;
    const request = ++petRequest.current;
    setPetBusy(true);
    setPetReply(null);
    if (prompt.trim()) setPetPrompt("");
    try {
      const result = await api<{
        round: number;
        reply: string;
        answer: number;
        needs_help: boolean;
      }>(
        `/${session.code}/pet`,
        {
          method: "POST",
          body: JSON.stringify({ round, prompt: prompt.trim() }),
        },
        session.token,
      );
      if (request !== petRequest.current) return;
      setPetReply({
        round: result.round,
        text: result.reply,
        answer: result.answer,
        needsHelp: result.needs_help,
        guided: !!prompt.trim(),
      });
    } catch (error) {
      if (request !== petRequest.current) return;
      setPetReply({
        round,
        text:
          error instanceof Error ? error.message : "Your pet couldn't respond.",
        answer: null,
        needsHelp: true,
        guided: false,
      });
    } finally {
      if (request === petRequest.current) setPetBusy(false);
    }
  }

  useEffect(() => {
    if (!session || game?.phase !== "playing" || !game.round || game.answered)
      return;
    const key = `${session.code}:${game.round}`;
    if (petAttempt.current === key) return;
    petAttempt.current = key;
    setPetPrompt("");
    void askPet();
  }, [session, game?.phase, game?.round, game?.answered]);

  useEffect(() => {
    if (
      !game ||
      game.phase !== "playing" ||
      game.answered ||
      !petReply ||
      petReply.round !== game.round ||
      petReply.needsHelp ||
      petReply.answer === null ||
      petBusy ||
      petPrompt.trim() ||
      remaining === 0
    )
      return;
    const timer = setTimeout(
      () => void answer(petReply.answer!, petReply.guided ? "team" : "pet"),
      3000,
    );
    return () => clearTimeout(timer);
  }, [
    game?.phase,
    game?.round,
    game?.answered,
    petReply,
    petBusy,
    petPrompt,
    remaining === 0,
  ]);

  function leave() {
    version.current += 1;
    petRequest.current += 1;
    petAttempt.current = "";
    setPetReply(null);
    setPetBusy(false);
    setPetPrompt("");
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
  const lastRound = game?.history.at(-1);
  const myHit = lastRound?.answers[game?.you ?? 0] === true;
  const rivalHit = lastRound?.answers[game?.you === 0 ? 1 : 0] === true;
  const myPetName = mine?.pet?.name || pet.name;
  const rivalPetName = rival?.pet?.name || "RIVAL";
  const roundMessage = lastRound
    ? myHit && rivalHit
      ? `${myPetName} and ${rivalPetName} both landed a hit! It's super effective!`
      : myHit
        ? `${myPetName} landed a hit! It's super effective!`
        : rivalHit
          ? `${rivalPetName} landed a hit! The rival's move was super effective!`
          : "Neither move landed!"
    : null;
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
          <p className="portrait-notice">
            Your trainer name and a small pet portrait are shared with your room
            opponent.
          </p>
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
          <button
            className="retro-button secondary"
            disabled={busy}
            onClick={() => void enter(false, "bot")}
          >
            PLAY AGAINST BOT →
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
          {game && ["waiting", "generating", "ready"].includes(game.phase) && (
            <div className="waiting-room">
              <h2>
                {game.phase === "ready"
                  ? "Questions ready!"
                  : game.phase === "generating"
                    ? "Preparing questions…"
                    : game.players.length < 2
                      ? "Waiting for a rival…"
                      : "Ready your team"}
              </h2>
              {game.players.length < 2 && (
                <p>
                  Share the room code. Both players must ready up before
                  questions are generated.
                </p>
              )}
              {game.players.map((player, index) => (
                <p key={index}>
                  {player.nickname}
                  {player.bot ? " (BOT)" : ""}:{" "}
                  {player.ready ? "READY" : "NOT READY"}
                </p>
              ))}
              {game.phase === "waiting" && (
                <button
                  className="retro-button primary"
                  disabled={busy || fatal}
                  onClick={() => void lobbyAction("ready")}
                >
                  {busy
                    ? "PREPARING…"
                    : mine?.ready
                      ? "READY · RETRY PREPARATION"
                      : "READY UP →"}
                </button>
              )}
              {game.phase === "generating" && (
                <p role="status">
                  Generating five questions. The timer has not started.
                </p>
              )}
              <button
                className="retro-button primary"
                disabled={busy || fatal || game.phase !== "ready"}
                onClick={() => void lobbyAction("start")}
              >
                START GAME →
              </button>
              <p>Five rounds · 30 seconds per question.</p>
            </div>
          )}
          {game && (game.phase === "playing" || game.phase === "finished") && (
            <>
              <div className="battle-layout">
                <BattleArena
                  mine={mine}
                  rival={rival}
                  pet={pet}
                  nickname={nickname}
                  message={
                    roundMessage ||
                    (game.phase === "finished"
                      ? "The battle is over. Check your final score!"
                      : game.answered
                        ? "Move locked in. Waiting for the rival…"
                        : remaining === 0
                          ? "Time’s up! Resolving the round…"
                          : "Choose an answer to power your next move!")
                  }
                />
                <div className="battle-question-panel">
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
                            <span>{String.fromCharCode(65 + index)}.</span>{" "}
                            {option}
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
                      <div className="pet-prompt">
                        <label htmlFor="pet-prompt">
                          TALK TO {myPetName.toUpperCase()}
                        </label>
                        <textarea
                          id="pet-prompt"
                          value={petPrompt}
                          maxLength={500}
                          placeholder="Help me solve this!"
                          onChange={(event) => setPetPrompt(event.target.value)}
                          disabled={game.answered || remaining === 0 || fatal}
                        />
                        <button
                          className="retro-button secondary"
                          disabled={
                            petBusy ||
                            !petPrompt.trim() ||
                            game.answered ||
                            remaining === 0 ||
                            fatal
                          }
                          onClick={() => void askPet(petPrompt)}
                        >
                          {petBusy ? "THINKING…" : "ASK PET →"}
                        </button>
                        {petBusy && (
                          <p role="status">{myPetName} is thinking…</p>
                        )}
                        {petReply &&
                          petReply.round === game.round &&
                          !game.answered && (
                            <p role="status">
                              {petReply.answer !== null && (
                                <>
                                  PET CHOOSES{" "}
                                  {String.fromCharCode(65 + petReply.answer)}
                                  .{" "}
                                </>
                              )}
                              {petReply.text}{" "}
                              {petReply.needsHelp
                                ? "Give your pet a hint or choose an answer above!"
                                : petPrompt.trim()
                                  ? "Submit your hint or clear it to let your pet answer."
                                  : "Submitting in 3 seconds. Choose another answer to take over!"}
                            </p>
                          )}
                      </div>
                      <p className="scoring-note">
                        Correct: 2 points in your specialty, 5 in another.
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
                </div>
              </div>
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
                        {round.answers[game.you] === true &&
                          ` · +${round.category === mine?.category ? 2 : 5} PTS · ${(round.sources?.[game.you] || "trainer").toUpperCase()}`}
                      </span>
                      <span>
                        RIVAL:{" "}
                        {round.answers[game.you === 0 ? 1 : 0] === true
                          ? "HIT"
                          : round.answers[game.you === 0 ? 1 : 0] === false
                            ? "MISS"
                            : "TIMEOUT"}
                        {round.answers[game.you === 0 ? 1 : 0] === true &&
                          ` · +${round.category === rival?.category ? 2 : 5} PTS · ${(round.sources?.[game.you === 0 ? 1 : 0] || "trainer").toUpperCase()}`}
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
