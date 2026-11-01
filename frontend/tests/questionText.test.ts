import assert from "node:assert/strict";
import test from "node:test";
import { questionBlocks } from "../src/questionText.ts";

test("renders the screenshot's escaped code as indented lines", () => {
  const question =
    "What will the following code output?\\n```python\\ndef f(a):\\n    return a if a > 0 else f(a + 1)\\nprint(f(-3))\\n```";
  assert.deepEqual(questionBlocks(question), [
    { type: "text", content: "What will the following code output?" },
    {
      type: "code",
      language: "python",
      content: "def f(a):\n    return a if a > 0 else f(a + 1)\nprint(f(-3))",
    },
  ]);
});

test("keeps literal escape sequences inside strings intact", () => {
  const result = questionBlocks(
    'Output?\\n```python\\nprint("\\n")\\nprint("done")\\n```',
  );
  assert.equal(result[1].content, 'print("\\n")\nprint("done")');
});

test("preserves properly formatted code and HTML-looking source as text", () => {
  const code = 'const tag = "<script>alert(1)</script>";\nconsole.log("\\n");';
  assert.equal(
    questionBlocks("Output?\n```javascript\n" + code + "\n```")[1].content,
    code,
  );
});

test("handles unfenced prose, inline code, multiple blocks and unclosed fences", () => {
  assert.deepEqual(questionBlocks("What does `\\n` mean?"), [
    { type: "text", content: "What does `\\n` mean?" },
  ]);
  const result = questionBlocks(
    "Compare:\n```python\na = 1\n```\nand\n```python\nb = 2",
  );
  assert.equal(result.length, 4);
  assert.equal(result[3].content, "b = 2");
});

test("normalizes escaped CRLF and handles apostrophes in code comments", () => {
  const result = questionBlocks(
    "Example\\r\\n```python\\r\\n# don't change this\\r\\nprint('hi')\\r\\n```",
  );
  assert.equal(result[1].content, "# don't change this\nprint('hi')");
});
