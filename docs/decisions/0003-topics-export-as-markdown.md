# 0003: Topics export as Markdown

Status: accepted, 2026-11-13.

Context: the owner expects topics to be exportable as Markdown. The web
interface showed topic cards only, and the Markdown export covered
conversations only.

Decision: topics are exported as one readable `topics.md` — a heading per
topic, largest first, with its summary, findings, and members. It is written by
`chatlore export <folder> --markdown` next to the conversation files, served by
`GET /topics/export` for a direct download, and linked from the Topics view. A
library without topics writes no file, and the endpoint answers 404 with a hint
to run `chatlore extract`.

Rationale: one file keeps the reports readable in any editor and matches the
Markdown export's shape; the direct endpoint serves the "give me the topics"
case without the whole bundle.

Consequences: the Markdown bundle gains a file when topics exist, which
downstream consumers of that zip should expect. The report holds only what the
graph's topic nodes store; per-message provenance inside a topic stays on the
Explore view.
