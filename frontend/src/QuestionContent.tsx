import { questionBlocks } from "./questionText";

function inlineCode(text: string) {
  return text
    .split(/(`[^`]+`)/g)
    .map((part, index) =>
      part.startsWith("`") && part.endsWith("`") ? (
        <code key={index}>{part.slice(1, -1)}</code>
      ) : (
        part
      ),
    );
}

export default function QuestionContent({ text }: { text: string }) {
  return (
    <div className="question-content">
      {questionBlocks(text).map((block, index) =>
        block.type === "code" ? (
          <div className="question-code" key={index}>
            {block.language && (
              <span className="code-language">{block.language}</span>
            )}
            <pre aria-label={`${block.language || "Source"} code`}>
              <code>{block.content}</code>
            </pre>
          </div>
        ) : index === 0 ? (
          <h2 className="question" key={index}>
            {inlineCode(block.content)}
          </h2>
        ) : (
          <p className="question" key={index}>
            {inlineCode(block.content)}
          </p>
        ),
      )}
    </div>
  );
}
