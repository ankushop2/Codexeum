import type { CSSProperties } from "react";

export type BattlePet = {
  name: string;
  color: string;
  image?: string;
  intro?: string;
};
export type Fighter = {
  category: string;
  score: number;
  nickname?: string;
  pet?: BattlePet;
};

function Creature({
  pet,
  rear,
  intro,
}: {
  pet: BattlePet;
  rear?: boolean;
  intro?: boolean;
}) {
  return (
    <div
      className={`battle-creature ${rear ? "rear" : "front"}`}
      role="img"
      aria-label={`${pet.name}, facing the opponent`}
    >
      {intro && pet.intro ? (
        <span
          className="intro-sprites"
          style={{ backgroundImage: `url("${pet.intro}")` }}
        />
      ) : pet.image ? (
        <img src={pet.image} alt="" />
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
            <span className="back-mark" />
          </div>
          <div className="pixel-foot left" />
          <div className="pixel-foot right" />
        </div>
      )}
    </div>
  );
}

type Outcome = boolean | null;

function RoundPet({
  pet,
  rear,
  result,
  opponent,
  intro,
}: {
  pet: BattlePet;
  rear?: boolean;
  result?: Outcome;
  opponent?: Outcome;
  intro?: boolean;
}) {
  const resolved = result !== undefined;
  const reaction = !resolved ? "" : result ? "round-cheer" : "round-miss";
  return (
    <div
      className={`round-pet ${reaction} ${result && !opponent ? "round-attack" : ""}`}
    >
      <div className="pet-motion">
        <Creature pet={pet} rear={rear} intro={intro} />
      </div>
      {resolved && (
        <div className="pet-reaction" aria-hidden="true">
          <span className="reaction-bubble">
            {result ? "YAY!" : result === null ? "TOO SLOW!" : "OH NO!"}
          </span>
          {result ? (
            <>
              <span className="celebration-ring" />
              <span className="reaction-stars">✦ ✧ ✦</span>
              <span className="reaction-spark spark-one">✦</span>
              <span className="reaction-spark spark-two">✦</span>
            </>
          ) : (
            <>
              <div className="falling-arrows">
                <span>▼</span>
                <span>▼</span>
                <span>▼</span>
              </div>
              <span className="miss-cloud">···</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function RoundEffects({
  round,
  mine,
  rival,
}: {
  round: number;
  mine: Outcome;
  rival: Outcome;
}) {
  const outcome =
    mine && rival
      ? "double-hit"
      : mine
        ? "own-hit"
        : rival
          ? "enemy-hit"
          : "double-miss";
  const title =
    mine && rival
      ? "DOUBLE YAY!"
      : mine || rival
        ? "SUPER EFFECTIVE!"
        : "DOUBLE MISS!";
  return (
    <div className={`round-effects ${outcome}`} aria-hidden="true">
      <div className="round-banner">
        <small>ROUND {round} COMPLETE</small>
        <strong>{title}</strong>
      </div>
      {Boolean(mine) !== Boolean(rival) && (
        <svg
          className="battle-strike"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <path
            className="strike-trail"
            d={
              mine
                ? "M25 75 L43 57 L51 63 L75 25"
                : "M75 25 L57 43 L49 37 L25 75"
            }
            pathLength="100"
          />
        </svg>
      )}
    </div>
  );
}

export default function BattleArena({
  mine,
  rival,
  pet,
  nickname,
  message,
  roundResult,
  introRemaining,
}: {
  mine?: Fighter;
  rival?: Fighter;
  pet: BattlePet;
  nickname: string;
  message: string;
  introRemaining?: number;
  roundResult?: { round: number; mine: Outcome; rival: Outcome };
}) {
  const myPet = mine?.pet || pet;
  const enemyPet = rival?.pet || { name: "RIVAL", color: "#edac79" };
  return (
    <div className="battle-display">
      <div
        className={`battle-field ${introRemaining !== undefined ? "battle-entering" : ""}`}
      >
        {introRemaining !== undefined && (
          <div className="battle-intro" role="status">
            <div className="intro-shutter top" />
            <div className="intro-shutter bottom" />
            <div className="intro-title">
              <small>A CHALLENGER APPEARS!</small>
              <strong>
                {myPet.name} <span>VS</span> {enemyPet.name}
              </strong>
              <small>
                {introRemaining > 0
                  ? `GET READY · ${introRemaining}`
                  : "LET’S BATTLE!"}
              </small>
            </div>
          </div>
        )}
        <div className="fighter-card enemy-card">
          <div>
            <strong>{enemyPet.name}</strong>
            <span>LV. 01</span>
          </div>
          <span>
            {rival?.nickname || "RIVAL"} · {rival?.category}
          </span>
          <div className="points-bar">
            <span>POINTS</span>
            <strong>{rival?.score ?? 0}</strong>
          </div>
        </div>
        <div className="arena-platform enemy-platform" />
        <div className="enemy-position">
          <RoundPet
            key={`enemy-${roundResult?.round}`}
            pet={enemyPet}
            intro={introRemaining !== undefined}
            result={roundResult?.rival}
            opponent={roundResult?.mine}
          />
        </div>
        <div className="arena-platform own-platform" />
        <div className="own-position">
          <RoundPet
            key={`own-${roundResult?.round}`}
            pet={myPet}
            intro={introRemaining !== undefined}
            rear
            result={roundResult?.mine}
            opponent={roundResult?.rival}
          />
        </div>
        {roundResult && (
          <RoundEffects key={roundResult.round} {...roundResult} />
        )}
        <div className="fighter-card own-card">
          <div>
            <strong>{myPet.name}</strong>
            <span>LV. 01</span>
          </div>
          <span>
            {mine?.nickname || nickname} · {mine?.category}
          </span>
          <div className="points-bar">
            <span>POINTS</span>
            <strong>{mine?.score ?? 0}</strong>
          </div>
        </div>
      </div>
      <div className="battle-narration" aria-live="polite">
        {roundResult && (
          <span className="sr-only">
            Round {roundResult.round}: {myPet.name}{" "}
            {roundResult.mine
              ? "answered correctly"
              : roundResult.mine === null
                ? "timed out"
                : "answered incorrectly"}
            ; {enemyPet.name}{" "}
            {roundResult.rival
              ? "answered correctly"
              : roundResult.rival === null
                ? "timed out"
                : "answered incorrectly"}
            .
          </span>
        )}
        <strong>
          {myPet.name} VS {enemyPet.name}!
        </strong>
        <p>
          {message}
          <span className="cursor"> ▼</span>
        </p>
      </div>
    </div>
  );
}
