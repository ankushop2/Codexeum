import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, CSSProperties } from "react";

import GameRoom from "./GameRoom";

type Skill = { id: string; name: string; symbol: string };

type Pet = {
  name: string;
  color: string;
  image?: string;
  columns?: number;
  rows?: number;
};
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
  const folderInput = useRef<HTMLInputElement>(null);
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

  async function importPet(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;
    const folderSelection = files.some((file) => file.webkitRelativePath);
    const rootFiles = folderSelection
      ? files.filter((file) => file.webkitRelativePath.split("/").length === 2)
      : files;
    const images = rootFiles.filter((file) =>
      ["image/png", "image/webp", "image/gif"].includes(file.type),
    );
    const metadata = rootFiles.find(
      (file) => file.name.toLowerCase() === "pet-record.json",
    );
    const sheet = images.find((file) =>
      ["spritesheet.png", "spritesheet.webp"].includes(file.name.toLowerCase()),
    );
    const file = folderSelection
      ? sheet
      : images.length === 1
        ? images[0]
        : undefined;
    if (!file) {
      setError(
        folderSelection
          ? "No spritesheet.png or spritesheet.webp found in this folder. Choose your pet’s output folder."
          : "Select one pet image and optionally pet-record.json together.",
      );
      return;
    }
    let petName = "";
    if (metadata) {
      try {
        if (metadata.size > 65536) throw new Error();
        const record: unknown = JSON.parse(await metadata.text());
        if (
          typeof record !== "object" ||
          record === null ||
          !("name" in record) ||
          typeof record.name !== "string" ||
          !record.name.trim() ||
          record.name.trim().length > 20
        )
          throw new Error();
        petName = record.name.trim().toUpperCase();
      } catch {
        setError(
          "Could not read a valid pet name from pet-record.json (maximum 20 characters).",
        );
        return;
      }
    }
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
      const codexSheet =
        image.naturalWidth === 1536 &&
        (image.naturalHeight === 2288 || image.naturalHeight === 1872);
      const importedColumns = codexSheet ? 8 : 1;
      const importedRows = codexSheet ? image.naturalHeight / 208 : 1;
      setPets((current) => [
        ...current,
        {
          name:
            petName ||
            (file.name.replace(/\.[^.]+$/, "").toLowerCase() === "spritesheet"
              ? ""
              : file.name
                  .replace(/\.[^.]+$/, "")
                  .slice(0, 20)
                  .toUpperCase()),
          color: "#aaa0e8",
          image: url,
          columns: importedColumns,
          rows: importedRows,
        },
      ]);
      setIndex(pets.length);
      setColumns(importedColumns);
      setRows(importedRows);
      setError("");
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      setError("That image could not be opened. Try another file.");
    };
    image.src = url;
  }

  function cycle(direction: number) {
    const nextIndex = (index + direction + pets.length) % pets.length;
    setIndex(nextIndex);
    setColumns(pets[nextIndex].columns ?? 1);
    setRows(pets[nextIndex].rows ?? 1);
  }

  return (
    <main className={`game-shell ${step === 2 ? "battle-mode" : ""}`}>
      <header className="masthead">
        <span className="tiny">HUMAN + PET / PLAYER 01</span>
        <span className="tiny">LONDON • 2026</span>
      </header>
      <div className="title">
        <img
          className="brand-mark"
          src="/favicon.svg"
          alt=""
          width="40"
          height="40"
        />
        <div>
          <p>THE FIVE-ROUND BRAIN BATTLE</p>
          <h1>CODEXEUM</h1>
        </div>
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
                <h2>{pet.name || "NAME YOUR PET"}</h2>
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
                        "--last-frame":
                          columns === 8 && (rows === 9 || rows === 11)
                            ? `${(6 / 7) * 100}%`
                            : columns > 1
                              ? "100%"
                              : "0%",
                        animation:
                          columns > 1
                            ? `sprite-play 1s steps(${columns === 8 && (rows === 9 || rows === 11) ? 6 : columns - 1}) infinite`
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
              pet={pet}
              columns={columns}
              rows={rows}
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
                onClick={() => folderInput.current?.click()}
              >
                ↑ CHOOSE PET FOLDER
              </button>
              <span>CHOOSE THE FOLDER CONTAINING YOUR PET</span>
              <input
                hidden
                ref={(input) => {
                  folderInput.current = input;
                  input?.setAttribute("webkitdirectory", "");
                }}
                type="file"
                multiple
                onChange={importPet}
              />
              <input
                hidden
                ref={fileInput}
                type="file"
                accept="image/png,image/webp,image/gif,.json,application/json"
                multiple
                onChange={importPet}
              />
            </div>
            <button
              className="text-button import-files"
              onClick={() => fileInput.current?.click()}
            >
              Or select image and metadata files
            </button>
            <details className="import-help">
              <summary>Where’s my Codex pet?</summary>
              <p>
                Choose the folder containing <code>spritesheet.png</code> and{" "}
                <code>pet-record.json</code>. The game reads the name and
                animation layout automatically. If your pet is stored elsewhere,
                select the image and metadata files instead. A small portrait
                and name are shared with your opponent when you join a room; the
                original files stay on your device.
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
                <small>
                  {columns === 8 && (rows === 9 || rows === 11)
                    ? "Codex pet sheet detected: playing six idle frames."
                    : "Preview plays the first row. Adjust the grid for sprite sheets."}
                </small>
              </div>
            )}
            {pet.image && (
              <label className="nickname-label" htmlFor="pet-name">
                PET NAME
                <input
                  id="pet-name"
                  placeholder="e.g. Bitwick"
                  maxLength={20}
                  value={pet.name}
                  onChange={(event) => {
                    const name = event.target.value.toUpperCase();
                    setPets((current) =>
                      current.map((item, i) =>
                        i === index ? { ...item, name } : item,
                      ),
                    );
                  }}
                />
              </label>
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
              disabled={!nickname.trim() || !pet.name.trim()}
              onClick={() => {
                setNickname(nickname.trim());
                setPets((current) =>
                  current.map((item, i) =>
                    i === index ? { ...item, name: item.name.trim() } : item,
                  ),
                );
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
