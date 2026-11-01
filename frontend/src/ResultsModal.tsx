import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import LearningProgress from "./LearningProgress";

type Review = { category: string; question?: string; correct_answer?: string };

export default function ResultsModal({
  nickname,
  outcome,
  score,
  rivalScore,
  correct,
  review,
}: {
  nickname: string;
  outcome: string;
  score: number;
  rivalScore: number;
  correct: number;
  review: Review[];
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [step, setStep] = useState(0);
  useEffect(() => {
    const previous = document.body.style.overflow;
    dialog.current?.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);
  function close() {
    dialog.current?.close();
    document.body.style.overflow = "";
  }
  return (
    <>
      <button
        className="retro-button primary"
        onClick={() => {
          setStep(0);
          dialog.current?.showModal();
          document.body.style.overflow = "hidden";
        }}
      >
        VIEW YOUR RESULTS →
      </button>
      {createPortal(
        <dialog
          ref={dialog}
          className="results-modal"
          aria-labelledby="results-title"
          onClose={() => {
            document.body.style.overflow = "";
          }}
        >
          <div className="results-modal-header">
            <span>
              {step === 0 ? "01 · YOUR BATTLE" : "02 · YOUR NEXT DISCOVERY"}
            </span>
            <button
              className="text-button"
              aria-label="Close results"
              onClick={close}
            >
              ✕
            </button>
          </div>
          {step === 0 ? (
            <div className="results-reveal">
              <div className="results-stars" aria-hidden="true">
                ✦ ★ ✦
              </div>
              <h2 id="results-title">{outcome}</h2>
              <p>Great exploring, {nickname}!</p>
              <div className="results-score">
                <strong>{score}</strong>
                <span>TO</span>
                <strong>{rivalScore}</strong>
              </div>
              <p>
                {correct} of 5 questions correct. Every round helps you learn!
              </p>
              <button
                className="retro-button primary"
                onClick={() => {
                  setStep(1);
                  dialog.current?.scrollTo(0, 0);
                }}
              >
                SEE WHAT TO LEARN NEXT →
              </button>
            </div>
          ) : (
            <>
              <h2 id="results-title" className="results-learning-title">
                KEEP YOUR ADVENTURE GOING!
              </h2>
              <LearningProgress nickname={nickname} review={review} />
              <div className="results-modal-actions">
                <button
                  className="retro-button secondary"
                  onClick={() => setStep(0)}
                >
                  ← MY SCORE
                </button>
                <button className="retro-button primary" onClick={close}>
                  DONE ✓
                </button>
              </div>
            </>
          )}
        </dialog>,
        document.body,
      )}
    </>
  );
}
