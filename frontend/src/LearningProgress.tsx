import { useEffect, useState } from "react";

const subjects = [
  "geography",
  "art",
  "maths",
  "biology",
  "history",
  "music",
  "science",
];
type Counts = { attempts: number; correct: number };

export default function LearningProgress({ nickname }: { nickname: string }) {
  const [data, setData] = useState<Record<string, Counts>>({});
  const [status, setStatus] = useState("Loading your learning journey…");
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
      <h3>YOUR LEARNING JOURNEY</h3>
      <p>
        Every question helps you grow! Here’s what you’ve learned in completed
        battles.
      </p>
      {status && <p role="status">{status}</p>}
      <div className="subject-progress">
        {subjects.map((subject) => {
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
