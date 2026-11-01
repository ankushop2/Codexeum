import { useEffect, useState } from "react";
import { Button, HealthBar, Panel, PetAvatar, SkillCard } from "./components";

type Skill = { id: string; name: string; symbol: string };

export default function App() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selected, setSelected] = useState("debugging");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/skills", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json();
      })
      .then((data) => setSkills(data.skills))
      .catch((error) => {
        if (error.name !== "AbortError")
          setError(
            "Cannot reach the API. Start both services with pnpm dev, then reload.",
          );
      });
    return () => controller.abort();
  }, []);

  return (
    <main>
      <header>
        <a className="brand" href="/">
          ✳ CODEX <span>ARENA</span>
        </a>
        <span className="badge">FOUNDATION PREVIEW</span>
      </header>
      <div className="intro">
        <p className="eyebrow">YOUR PET. YOUR SKILLS. YOUR MOVE.</p>
        <h1>
          Small pets.
          <br />
          <em>Big brain energy.</em>
        </h1>
        <p>Pick a specialty. Meet your rival. Help your pet when it matters.</p>
      </div>
      <Panel className="arena">
        <div className="arena-top">
          <span>TRAINING ARENA</span>
          <span>FIVE ROUNDS · ONE WINNER</span>
        </div>
        <div className="fighters">
          <div>
            <HealthBar name="BYTE" value={100} />
            <PetAvatar name="Byte" />
            <span className="player-label">YOUR COMPANION</span>
          </div>
          <span className="versus">VS</span>
          <div>
            <HealthBar name="GLITCH" value={100} />
            <PetAvatar name="Glitch" rival />
            <span className="player-label">YOUR FUTURE RIVAL</span>
          </div>
        </div>
        <div className="dialogue" aria-live="polite">
          <span>⌘</span>
          <div>
            <strong>
              {preview
                ? "Your arena is ready."
                : "A new challenger is loading…"}
            </strong>
            <p>
              {preview
                ? `${skills.find((skill) => skill.id === selected)?.name} selected. Matchmaking and Codex answers are the next build.`
                : "Choose your pet’s specialty below. A shared random skill joins the battle at match time."}
            </p>
          </div>
        </div>
      </Panel>
      <section className="selection">
        <div>
          <p className="eyebrow">01 / CHOOSE YOUR SPECIALTY</p>
          <h2>What’s your superpower?</h2>
        </div>
        <span className="muted">+ 1 shared random category per match</span>
      </section>
      {error ? (
        <p role="alert" className="error">
          {error}
        </p>
      ) : (
        <div className="skills" aria-label="Skill categories">
          {skills.map((skill) => (
            <SkillCard
              key={skill.id}
              {...skill}
              selected={selected === skill.id}
              onClick={() => setSelected(skill.id)}
            />
          ))}
        </div>
      )}
      <div className="footer-action">
        <p>
          Original placeholder pets · Multiplayer and AI are not connected yet.
        </p>
        <Button disabled={!skills.length} onClick={() => setPreview(true)}>
          Preview selection <span>↗</span>
        </Button>
      </div>
    </main>
  );
}
