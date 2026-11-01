import type { CSSProperties } from "react";

export type BattlePet = { name: string; color: string; image?: string };
export type Fighter = {
  category: string;
  score: number;
  nickname?: string;
  pet?: BattlePet;
};

function Creature({ pet, rear }: { pet: BattlePet; rear?: boolean }) {
  return (
    <div
      className={`battle-creature ${rear ? "rear" : "front"}`}
      role="img"
      aria-label={`${pet.name}, facing the opponent`}
    >
      {pet.image ? (
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

export default function BattleArena({
  mine,
  rival,
  pet,
  nickname,
  message,
  roundResult,
}: {
  mine?: Fighter;
  rival?: Fighter;
  pet: BattlePet;
  nickname: string;
  message: string;
  roundResult?: { round: number; mine: boolean; rival: boolean };
}) {
  const myPet = mine?.pet || pet;
  const enemyPet = rival?.pet || { name: "RIVAL", color: "#edac79" };
  return (
    <div className="battle-display">
      <div className="battle-field">
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
        <div
          key={`enemy-${roundResult?.round}`}
          className={`enemy-position ${roundResult?.rival ? "successful-move" : ""}`}
        >
          {roundResult?.rival && (
            <span className="move-stars" aria-hidden="true">
              ✦ ✧ ✦
            </span>
          )}
          <Creature pet={enemyPet} />
        </div>
        <div className="arena-platform own-platform" />
        <div
          key={`own-${roundResult?.round}`}
          className={`own-position ${roundResult?.mine ? "successful-move" : ""}`}
        >
          {roundResult?.mine && (
            <span className="move-stars" aria-hidden="true">
              ✦ ✧ ✦
            </span>
          )}
          <Creature pet={myPet} rear />
        </div>
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
