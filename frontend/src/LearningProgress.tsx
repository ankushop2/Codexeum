import { useEffect, useRef, useState } from "react";

const subjects = [
  "geography",
  "art",
  "maths",
  "biology",
  "history",
  "music",
  "science",
  "code",
];
type Counts = { attempts: number; correct: number };

export default function LearningProgress({
  nickname,
  review = [],
  completed = false,
}: {
  nickname: string;
  review?: { category: string; question?: string; correct_answer?: string }[];
  completed?: boolean;
}) {
  const [data, setData] = useState<Record<string, Counts>>({});
  const [status, setStatus] = useState("Loading your learning journey…");
  const track = useRef<HTMLDivElement>(null);
  const orderedSubjects = [...subjects].sort((a, b) => {
    const priority = (subject: string) => {
      const count = data[subject];
      return count?.attempts ? count.correct / count.attempts : 0.5;
    };
    return priority(a) - priority(b);
  });
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/progress?nickname=${encodeURIComponent(nickname)}`, {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok)
          throw new Error(
            "Your learning progress is unavailable. Try again after your next battle.",
          );
        setData((await response.json()).subjects);
        setStatus("");
      })
      .catch((error) => {
        if (!controller.signal.aborted) setStatus(error.message);
      });
    return () => controller.abort();
  }, [nickname]);
  return (
    <section className="learning-progress">
      {completed && (
        <div className="learning-celebration">
          <span aria-hidden="true">✦ ★ ✦</span>
          <h3>ADVENTURE COMPLETE!</h3>
          <p>
            {review.length
              ? "Every mistake is a new discovery. Let’s explore what’s next!"
              : "Great exploring! Keep growing with a new subject."}
          </p>
        </div>
      )}
      <div className="learning-heading">
        <div>
          <h3>YOUR NEXT DISCOVERY</h3>
          <p>
            Review missed questions first, then explore subjects to practise.
          </p>
        </div>
        <div className="carousel-controls">
          <button
            className="retro-button secondary"
            aria-label="Previous learning cards"
            onClick={() =>
              track.current?.scrollBy({
                left: -320,
                behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
                  .matches
                  ? "instant"
                  : "smooth",
              })
            }
          >
            ◀
          </button>
          <button
            className="retro-button secondary"
            aria-label="Next learning cards"
            onClick={() =>
              track.current?.scrollBy({
                left: 320,
                behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
                  .matches
                  ? "instant"
                  : "smooth",
              })
            }
          >
            ▶
          </button>
        </div>
      </div>
      <p>
        Every question helps you grow! Here’s what you’ve learned in completed
        battles.
      </p>
      {status && <p role="status">{status}</p>}
      <div
        className="subject-progress learning-carousel"
        ref={track}
        tabIndex={0}
        role="region"
        aria-label="Learning cards, scroll to explore"
      >
        {review.map((round, index) => (
          <article className="review-card" key={`review-${index}`}>
            <span>LET’S TRY AGAIN · {round.category.toUpperCase()}</span>
            <h4>{round.question || `Review round ${index + 1}`}</h4>
            <p>The answer to remember:</p>
            <strong>
              {round.correct_answer || "Try another question in this subject."}
            </strong>
            <p>Say it in your own words, then explain it to your pet!</p>
          </article>
        ))}
        {orderedSubjects.map((subject) => {
          const count = data[subject] || { attempts: 0, correct: 0 };
          const percent = count.attempts
            ? Math.round((100 * count.correct) / count.attempts)
            : 0;
          return (
            <article key={subject}>
              <strong>{subject.toUpperCase()}</strong>
              <p>
                {count.attempts
                  ? `${count.correct} of ${count.attempts} correct · ${percent}%`
                  : "Ready to explore!"}
              </p>
              <progress
                value={count.correct}
                max={count.attempts || 1}
                aria-label={`${subject}: ${count.correct} of ${count.attempts} correct`}
              />
              <p>
                {count.attempts
                  ? percent >= 80
                    ? "Great exploring! Keep it up!"
                    : "Let’s practise this together!"
                  : "Try this subject in your next battle."}
              </p>
            </article>
          );
        })}
      </div>
      <p>Progress belongs to your nickname. Use the same one each time.</p>
    </section>
  );
}
