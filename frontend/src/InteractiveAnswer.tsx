import { useState } from "react";

const places: Record<string, [number, number]> = {
  "North America": [19, 30],
  "South America": [31, 69],
  Europe: [51, 25],
  Africa: [51, 58],
  Asia: [73, 32],
  Oceania: [87, 77],
};

export default function InteractiveAnswer({
  kind,
  options,
  disabled,
  eliminated = [],
  onAnswer,
}: {
  kind: "map" | "order";
  options: string[];
  disabled: boolean;
  eliminated?: number[];
  onAnswer: (answer: number | number[]) => void;
}) {
  const [order, setOrder] = useState(options.map((_, index) => index));
  function move(index: number, direction: number) {
    const next = [...order];
    [next[index], next[index + direction]] = [
      next[index + direction],
      next[index],
    ];
    setOrder(next);
  }
  if (kind === "map")
    return (
      <div>
        <p>Tap a labelled continent to lock in your answer.</p>
        <div className="quiz-map" aria-label="World continent map">
          <svg viewBox="0 0 600 300" aria-hidden="true">
            <rect width="600" height="300" fill="#c9dfe1" />
            <g fill="#9bad83" stroke="#43513b" strokeWidth="2">
              <path d="M35 45 90 20 155 35 180 65 140 100 128 125 100 110 70 75Z" />
              <path d="M145 140 185 125 220 165 205 215 175 265 160 210Z" />
              <path d="M270 50 305 30 335 55 320 90 282 85Z" />
              <path d="M270 105 325 95 355 140 330 205 300 225 275 170Z" />
              <path d="M335 30 460 25 555 65 530 110 465 125 425 155 380 110 340 90Z" />
              <path d="M470 220 530 200 570 235 550 265 495 265Z" />
            </g>
          </svg>
          {options.map((option, index) => (
            <button
              key={option}
              className="map-pin"
              disabled={disabled || eliminated.includes(index)}
              style={{
                left: `${places[option][0]}%`,
                top: `${places[option][1]}%`,
              }}
              onClick={() => onAnswer(index)}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    );
  return (
    <div className="timeline-answer">
      <p>Move the cards: earliest at the top, latest at the bottom.</p>
      <ol>
        {order.map((item, index) => (
          <li key={item}>
            <span>
              {index + 1}. {options[item]}
            </span>
            <div>
              <button
                aria-label={`Move ${options[item]} earlier`}
                disabled={disabled || index === 0}
                onClick={() => move(index, -1)}
              >
                ↑
              </button>
              <button
                aria-label={`Move ${options[item]} later`}
                disabled={disabled || index === order.length - 1}
                onClick={() => move(index, 1)}
              >
                ↓
              </button>
            </div>
          </li>
        ))}
      </ol>
      <button
        className="retro-button primary"
        disabled={disabled}
        onClick={() => onAnswer(order)}
      >
        LOCK IN MY TIMELINE →
      </button>
    </div>
  );
}
