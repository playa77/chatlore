# 0002: Credit exhaustion is absorbed and resumable

Status: accepted, 2026-11-13.

Context: during the first real import, the OpenRouter model key ran out of
credits mid-run (HTTP 402). The run stopped with the provider's raw error body
in the dialog notes — including a per-key workspace URL — no topics were
written, and nothing in the interface said how to finish the graph.

Decision: a 402 from the model provider becomes `LLMPaymentError`, and from the
embedding provider a named `EmbeddingError`, each with a message built from the
reply's billing numbers only — never the raw body. A stopped run keeps
everything already imported, embedded, and read; the stage notes say what to do
(add credits, then resume). Resuming is a first-class step: `POST
/library/process` runs the embedding and reading pipeline on the library the
upload already built, `GET /library` reports still-unread passages in
`graph_pending`, and the dialog offers a Resume processing button when work is
left. No automatic retries: a balance error is not transient, and the reading
model's own client keeps its existing retry budget for transient statuses.

Rationale: the user's next action after a balance error is topping up, then
finishing; anything else the interface could show is noise. The answer caches
make a resume cheap — a re-run asks the model only for what it has not read.

Consequences: a payment stop leaves the import marked done with a note, not
failed: conversations and the partial graph stay usable (word search works;
topics stay absent until the run finishes). Key checks in `doctor` stay free;
live confirmation of the models is the opt-in `--probe`, which spends a little
credit by design.
