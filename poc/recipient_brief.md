# Recipient brief — Midpoint model simulation (s01, Daniel's side)

Follow the same rules as `poc/generator_brief.md` (read it for the general rules), but you
are now running the RECIPIENT side of shared scenario s01.

Privacy: you may read ONLY these fields of `poc/runs/v2/outputs/s01.json`: `share_draft` (the
message Leila sent, which Daniel sees) and `perspective_summary` (Leila's neutral summary,
which goes only into the AI context, never to Daniel). Do not read any other field or any
other file in `poc/runs/v2/outputs/`. Daniel's data is `scenarios.json` → s01 → `recipient`.

## Pipeline

1. Daniel receives `share_draft`.
2. Fixed app question: "How do you see this?" Then intake via `next_intake_question`
   (input: Leila's sent message + Daniel's turns so far; max 4 questions). Answers come from
   `recipient.intake_answers` using the same rules as the generator brief. Run
   `safety_check` on each answer. Then "Anything else you'd like to add?" with unused items.
3. `summarize_issue` on Daniel's turns.
4. `perspective_summary` for Daniel.
5. `consult` reply 1 for Daniel. Context: Daniel's summary and turns, Leila's sent message,
   and Leila's `perspective_summary` (use it to inform the reply; never quote it).
6. Daniel tries to send `recipient.harsh_reply_draft`: `safety_check`, then
   `polite_rewrite` (thread context: Leila's sent message).

## Output

Write `poc/runs/v2/outputs/s01_recipient.json`:

```json
{
  "id": "s01",
  "side": "recipient",
  "received_message": "...",
  "safety_checks": [{"on": "...", "text": "...", "result": {}}],
  "intake": [{"question": "...", "chips": ["..."], "answer": "..."}],
  "anything_else": "...",
  "summary": {},
  "perspective_summary": "...",
  "consult": [{"role": "ai", "text": "..."}],
  "harsh_draft": "...",
  "rewrite": {"rewrite": "...", "harsh": true}
}
```

Validate the JSON after writing. Reply with only the path.
