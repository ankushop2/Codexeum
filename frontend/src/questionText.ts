export type QuestionBlock =
  | { type: "text"; content: string }
  | { type: "code"; content: string; language: string };

function codeLineBreaks(value: string): string {
  if (value.includes("\n")) return value.replace(/\r\n/g, "\n");
  let result = "";
  let quote = "";
  let comment = false;
  for (let i = 0; i < value.length; i++) {
    const char = value[i];
    if (
      !quote &&
      char === "\\" &&
      (value[i + 1] === "n" || value.slice(i + 1, i + 4) === "r\\n")
    ) {
      result += "\n";
      i += value[i + 1] === "n" ? 1 : 3;
      comment = false;
    } else if (quote && char === "\\") {
      result += char + (value[++i] || "");
    } else {
      if (!comment) {
        if (quote && char === quote) quote = "";
        else if (!quote && (char === "'" || char === '"' || char === "`"))
          quote = char;
        else if (
          !quote &&
          (char === "#" || (char === "/" && value[i + 1] === "/"))
        )
          comment = true;
      }
      result += char;
    }
  }
  return result;
}

export function questionBlocks(value: string): QuestionBlock[] {
  const blocks: QuestionBlock[] = [];
  const fences = /```([\w+-]*)[ \t]*(?:\r?\n|\\r\\n|\\n)?([\s\S]*?)(?:```|$)/g;
  let last = 0;
  for (const match of value.matchAll(fences)) {
    const text = value
      .slice(last, match.index)
      .replace(/\\r\\n|\\n/g, "\n")
      .trim();
    if (text) blocks.push({ type: "text", content: text });
    blocks.push({
      type: "code",
      language: match[1],
      content: codeLineBreaks(match[2]).replace(/^\n+|\n+$/g, ""),
    });
    last = match.index + match[0].length;
  }
  const tail = (
    last ? value.slice(last).replace(/\\r\\n|\\n/g, "\n") : value
  ).trim();
  if (tail) blocks.push({ type: "text", content: tail });
  return blocks;
}
