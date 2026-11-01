import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, CSSProperties } from "react";

import GameRoom from "./GameRoom";

type Skill = { id: string; name: string; symbol: string };

type Pet = { name: string; color: string; image?: string };
const starters: Pet[] = [
  { name: "BYTE", color: "#aaa0e8" },
  { name: "PATCH", color: "#edac79" },
  { name: "GLITCH", color: "#9bc6a1" },
];

function ConnectionIndicator() {
  const [status, setStatus] = useState("checking");
  useEffect(() => {
    let mounted = true;
    let controller: AbortController | undefined;
    async function check() {
      controller?.abort();
      controller = new AbortController();
      const timeout = window.setTimeout(() => controller?.abort(), 4000);
      try {
        const response = await fetch("/api/health", {
          cache: "no-store",
          signal: controller.signal,
        });
        const data = await response.json();
        if (mounted)
          setStatus(response.ok && data.status === "ok" ? "online" : "offline");
      } catch {
        if (mounted) setStatus("offline");
      } finally {
        window.clearTimeout(timeout);
      }
    }
    void check();
    const interval = window.setInterval(() => void check(), 10000);
    return () => {
      mounted = false;
      controller?.abort();
      window.clearInterval(interval);
    };
  }, []);
  return (
    <div className={`connection ${status}`} role="status">
      <span className="connection-light" />
      API{" "}
      {status === "online"
        ? "CONNECTED"
        : status === "offline"
          ? "OFFLINE"
          : "CONNECTING"}
    </div>
  );
}

export default function App() {
  const [pets, setPets] = useState(starters);
  const [index, setIndex] = useState(0);
  const [step, setStep] = useState(0);
  const [nickname, setNickname] = useState("");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selected, setSelected] = useState("debugging");
  const [error, setError] = useState("");
  const [skillError, setSkillError] = useState(false);
  const [columns, setColumns] = useState(1);
  const [rows, setRows] = useState(1);
  const fileInput = useRef<HTMLInputElement>(null);
  const urls = useRef<string[]>([]);
  const pet = pets[index];

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController;
    async function loadSkills() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 4000);
      try {
        const response = await fetch("/api/skills", {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("API unavailable");
        const data = await response.json();
        if (!stopped) {
          setSkills(data.skills);
          setSkillError(false);
        }
      } catch {
        if (!stopped) {
          setSkillError(true);
          timer = setTimeout(loadSkills, 3000);
        }
      } finally {
        clearTimeout(timeout);
      }
    }
    void loadSkills();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller?.abort();
    };
  }, []);

  useEffect(
    () => () => {
      urls.current.forEach((url) => URL.revokeObjectURL(url));
    },
    [],
  );

  function importPet(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (
      !["image/png", "image/webp", "image/gif"].includes(file.type) ||
      file.size > 5 * 1024 * 1024
    ) {
      setError("Choose a PNG, WebP or GIF under 5 MB.");
      return;
    }
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      urls.current.push(url);
      setPets((current) => [
        ...current,
        {
          name: file.name
            .replace(/\.[^.]+$/, "")
            .slice(0, 20)
            .toUpperCase(),
          color: "#aaa0e8",
          image: url,
        },
      ]);
      setIndex(pets.length);
      setColumns(1);
      setRows(1);
      setError("");
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      setError("That image could not be opened. Try another file.");
    };
    image.src = url;
  }

  function cycle(direction: number) {
    setIndex((index + direction + pets.length) % pets.length);
    setColumns(1);
    setRows(1);
  }

  return (
    <main className="game-shell">
      <header className="masthead">
        <span className="tiny">HUMAN + PET / PLAYER 01</span>
        <span className="tiny">LONDON • 2026</span>
      </header>
      <div className="title">
        <span className="title-star">✦</span>
        <div>
          <p>THE FIVE-ROUND BRAIN BATTLE</p>
          <h1>
            CODEX<span>ARENA</span>
          </h1>
        </div>
        <span className="title-star">✦</span>
      </div>
      <nav className="steps" aria-label="Setup progress">
        {["YOUR PET", "YOUR SKILL", "READY UP"].map((label, i) => (
          <span
            key={label}
            className={step === i ? "active" : step > i ? "done" : ""}
            aria-current={step === i ? "step" : undefined}
          >
            {step > i ? "✓" : `0${i + 1}`} {label}
          </span>
        ))}
      </nav>
      <section className="console">
        <div className="screen-heading">
          <span>
            ▶{" "}
            {step === 0
              ? "CHOOSE YOUR COMPANION"
              : step === 1
                ? "CHOOSE YOUR SPECIALTY"
                : "LINK BATTLE"}
          </span>
          <span>LV. 01</span>
        </div>
        <div className="screen">
          <div className="screen-grid" />
          {step === 0 ? (
            <>
              <div className="pet-name">
                <button aria-label="Previous pet" onClick={() => cycle(-1)}>
                  ◀
                </button>
                <h2>{pet.name}</h2>
                <button aria-label="Next pet" onClick={() => cycle(1)}>
                  ▶
                </button>
              </div>
              <div className="pet-stage">
                <div className="platform" />
                {pet.image ? (
                  <div
                    className="imported-pet"
                    role="img"
                    aria-label={pet.name}
                    style={
                      {
                        backgroundImage: `url("${pet.image}")`,
                        backgroundSize: `${columns * 100}% ${rows * 100}%`,
                        "--frames": columns,
                        "--last-frame": columns > 1 ? "100%" : "0%",
                        animation:
                          columns > 1
                            ? `sprite-play 1s steps(${columns - 1}) infinite`
                            : "none",
                      } as CSSProperties
                    }
                  />
                ) : (
                  <div
                    className="pixel-pet"
                    style={{ "--pet-color": pet.color } as CSSProperties}
                  >
                    <div className="pixel-ear left" />
                    <div className="pixel-ear right" />
                    <div className="pixel-body">
                      <i />
                      <i />
                      <b />
                    </div>
                    <div className="pixel-foot left" />
                    <div className="pixel-foot right" />
                  </div>
                )}
                <span className="sparkle one">✦</span>
                <span className="sparkle two">+</span>
              </div>
              <div className="pet-meta">
                <span>
                  {pet.image ? "IMPORTED COMPANION" : "ORIGINAL STARTER PET"}
                </span>
                <span>
                  {String(index + 1).padStart(2, "0")} /{" "}
                  {String(pets.length).padStart(2, "0")}
                </span>
              </div>
            </>
          ) : step === 1 ? (
            <div className="skill-screen">
              <h2>Pick your power.</h2>
              <p>Your pet’s specialty for the battle.</p>
              {skillError ? (
                <p role="alert">
                  Waiting for the backend. Retrying automatically… Start both
                  services with pnpm dev.
                </p>
              ) : !skills.length ? (
                <p role="status">Loading skills…</p>
              ) : (
                <div className="skill-grid">
                  {skills.map((skill) => (
                    <button
                      key={skill.id}
                      className={selected === skill.id ? "selected" : ""}
                      aria-pressed={selected === skill.id}
                      onClick={() => {
                        setSelected(skill.id);
                      }}
                    >
                      <span>{skill.symbol}</span>
                      {skill.name}
                    </button>
                  ))}
                </div>
              )}
              <p className="random-skill">
                ? + ONE SHARED RANDOM CATEGORY AT MATCH TIME
              </p>
            </div>
          ) : (
            <GameRoom
              category={selected}
              nickname={nickname}
              petName={pet.name}
              onBack={() => setStep(1)}
            />
          )}
        </div>
        <div className="dialogue">
          <span className="dialogue-icon">✳</span>
          <p>
            {step === 0
              ? "Every great trainer starts with a companion. Pick a starter, or bring your own Codex pet."
              : step === 1
                ? "Five questions. Two pets. Choose answers to power your companion. Codex assistance is coming later."
                : "Share a room code with your rival. Five questions, ten seconds each. The second player joining starts the battle!"}
            <span className="cursor">▼</span>
          </p>
        </div>
      </section>
      <section className="controls">
        {step === 0 ? (
          <>
            <div className="import-row">
              <button
                className="retro-button secondary"
                onClick={() => fileInput.current?.click()}
              >
                ↑ IMPORT PET
              </button>
              <span>PNG / WEBP / GIF · MAX 5 MB</span>
              <input
                hidden
                ref={fileInput}
                type="file"
                accept="image/png,image/webp,image/gif"
                onChange={importPet}
              />
            </div>
            <details className="import-help">
              <summary>Where’s my Codex pet?</summary>
              <p>
                On your Mac, use Finder → Go → Go to Folder and enter{" "}
                <code>~/.codex/pets/</code>. If your custom pet has an image or
                sprite sheet there, import that file. Built-in pets may be
                bundled with the app rather than in this folder. You can also
                use your own pet artwork. The image stays in this browser tab.
              </p>
            </details>
            {pet.image && (
              <div className="sprite-controls">
                <span>SPRITE SHEET?</span>
                <label>
                  Columns{" "}
                  <input
                    type="number"
                    min="1"
                    max="32"
                    value={columns}
                    onChange={(event) =>
                      setColumns(
                        Math.max(
                          1,
                          Math.min(32, Number(event.target.value) || 1),
                        ),
                      )
                    }
                  />
                </label>
                <label>
                  Rows{" "}
                  <input
                    type="number"
                    min="1"
                    max="32"
                    value={rows}
                    onChange={(event) =>
                      setRows(
                        Math.max(
                          1,
                          Math.min(32, Number(event.target.value) || 1),
                        ),
                      )
                    }
                  />
                </label>
                <small>Preview plays the first row.</small>
              </div>
            )}
            <label className="nickname-label" htmlFor="nickname">
              TRAINER NAME
              <input
                id="nickname"
                placeholder="Your nickname…"
                maxLength={20}
                value={nickname}
                onChange={(event) => setNickname(event.target.value)}
                autoComplete="nickname"
              />
            </label>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <button
              className="retro-button primary"
              disabled={!nickname.trim()}
              onClick={() => {
                setNickname(nickname.trim());
                setStep(1);
              }}
            >
              I CHOOSE YOU! <span>→</span>
            </button>
          </>
        ) : step === 1 ? (
          <div className="step-actions">
            <button
              className="retro-button secondary"
              onClick={() => setStep(step - 1)}
            >
              ← BACK
            </button>
            {step === 1 && (
              <button
                className="retro-button primary"
                disabled={!skills.length}
                onClick={() => setStep(2)}
              >
                READY UP →
              </button>
            )}
          </div>
        ) : null}
      </section>
      <footer>
        <span>5 ROUNDS. 2 PETS. 1 WINNER.</span>
        <ConnectionIndicator />
      </footer>
    </main>
  );
}
