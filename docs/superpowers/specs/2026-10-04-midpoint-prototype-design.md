# Midpoint Prototype — Design Spec

Date: 2026-10-04
Status: Draft for review

## 1. Purpose

Many personal conflicts and misunderstandings could be resolved with more information and better wording. People often do not know how to describe an issue politely, or do not want to raise it in the moment (for example, a parent who disagrees with their partner's approach to a child but does not want to say so in front of the child).

Midpoint is a personal app where a user:

1. Registers an issue quickly with AI help (one sentence plus a few short questions).
2. Gets private, unbiased AI consultation — including honest feedback when the user is part of the problem, delivered without making them feel undermined.
3. Optionally shares the issue with the other party as a polite message, and continues in an AI-mediated thread.
4. Builds a history of issues the AI can use for better advice over time.

### Goal of this version

A working prototype to test the idea with a small group of real people (friends, family). Success means testers can register issues, find the consultation useful and fair, and (when they choose) share and discuss an issue with the other party in a calmer way than they would have otherwise.

### Out of scope (future sub-projects)

- Human expert consultation
- HR / workplace version
- Native mobile apps
- Languages other than English
- Notifications beyond invite emails

## 2. Key decisions

| Topic | Decision |
|---|---|
| Platform | Mobile-friendly web app |
| Stack | Python FastAPI backend, React (Vite, TypeScript) frontend, PostgreSQL |
| AI | Claude API via official Anthropic Python SDK |
| Language | English only |
| Accounts | Every participant has an account (email magic link, no passwords) |
| Sharing | Optional, per issue. Default is a private, personal issue |
| Two-sided | Recipient signs up, does their own intake, gets their own private consultation |
| Visibility | Each side sees only their own private material plus approved thread messages |
| Thread | Ongoing mediated thread; AI suggests a polite rewrite before each send |
| Resolve | Shared issue resolves when both participants vote; private issue by owner alone |
| Safety | Detect and pause: resources shown, sharing disabled, event logged |
| Architecture | Modular monolith with fixed, separately testable AI steps |

## 3. Architecture

```
frontend/   React (Vite, TS), mobile-first; REST + SSE for streamed AI replies
backend/    FastAPI modular monolith
  accounts/   magic-link login, sessions
  issues/     issue records, history, deletion, export
  intake/     sentence -> follow-up questions -> structured issue
  consult/    private AI consultation chat
  share/      invites, mediated thread, resolve votes
  safety/     risk check on user input and outgoing messages
  ai/         only module that calls Claude; prompt templates; context builder
  admin/      safety events and usage counts (owner only)
evals/      AI scenario files and runner script
```

- PostgreSQL via SQLAlchemy and Alembic migrations.
- Deployment: docker-compose (app + db) on one small VM, HTTPS via reverse proxy.
- All configuration and secrets (Anthropic key, DB URL, SMTP, model names, rate limits, helpline list) come from environment variables.

## 4. Data model

- **User**: id, email (unique), display_name, created_at
- **Issue**: id, owner_id, title, summary (structured JSON: what happened, feelings, needs, desired outcome), status (`private` | `shared` | `resolved`), safety_flag (bool), created_at, updated_at
- **IntakeTurn**: id, issue_id, user_id, role (`ai` | `user`), text, order
- **ConsultSession**: id, issue_id, user_id — one per participant per issue; readable only by that user
- **ConsultMessage**: id, session_id, role (`ai` | `user`), text, prompt_version, created_at
- **Participant**: issue_id, user_id, side (`initiator` | `recipient`), perspective_summary (AI-written neutral summary of this side's view; never shown to the other person, used only as AI context)
- **Invite**: id, issue_id, email, token_hash, expires_at, accepted_at
- **ThreadMessage**: id, issue_id, author_id, original_text (visible only to author), sent_text (visible to both), sent_at
- **ResolveVote**: issue_id, user_id, created_at
- **SafetyEvent**: id, issue_id, user_id, source (`intake` | `consult` | `thread` | `share`), category, excerpt, created_at
- **Feedback**: id, user_id, consult_message_id, rating (up/down), comment, created_at

### Privacy rule

A prompt built for user X may contain only:

- X's own IntakeTurns, issue summary, ConsultMessages, and ThreadMessage original_text
- `sent_text` of all ThreadMessages on the issue
- The other participant's `perspective_summary`
- Summaries of X's own previous issues (history)

It must never contain the other participant's IntakeTurns, ConsultMessages, or ThreadMessage original_text. This rule is implemented in one place: `ai.build_context(user_id, issue_id)`.

## 5. Core flows

### A. Intake (private)

1. User types one sentence describing the issue.
2. Safety check runs. If flagged, go to flow F.
3. AI asks 2–4 short follow-up questions, one at a time (who is involved, what happened, what the user wants). Each question offers quick-reply chips plus free text; questions can be skipped.
4. AI produces a structured summary (title, what happened, feelings and needs, desired outcome). User edits if needed and confirms.
5. Issue is saved with status `private`.

### B. Consultation (private, repeatable)

- Chat inside the issue. The AI opens with a balanced reading of the situation without waiting for a question.
- Tone rules (in the consult prompt):
  1. Acknowledge the user's feelings first.
  2. Describe the other person's likely view.
  3. Name the user's own part plainly but kindly, when there is one.
  4. End with concrete next steps.
  5. Never take sides; never diagnose or label people.
- History: the AI receives short summaries of the user's last N issues (configurable) to spot patterns.
- Private issues stream replies over SSE. Shared issues return the full reply after the leak check (see section 6).

### C. Share (optional)

1. User selects "Share with the other person". Disabled if the issue has a safety flag.
2. AI drafts a polite opening message from the issue summary. User edits and approves it.
3. User enters the recipient's email; an invite with an expiring link is sent.
4. Recipient signs up or logs in via magic link (invite is bound to that email), sees only the approved message, and completes a short intake ("How do you see this?"). This produces their `perspective_summary`.
5. Recipient gets their own private consultation. Issue status becomes `shared`.

### D. Mediated thread

- Either participant writes a message. Safety check runs first.
- AI suggests a polite rewrite, shown next to the original. The author can send the rewrite, edit it, or send the original (with a soft warning if the original is judged harsh).
- After each sent message, both participants' `perspective_summary` values are refreshed.

### E. Resolve

- Either participant selects "I feel this is resolved", creating a ResolveVote.
- A shared issue becomes `resolved` when both participants have voted. A private issue is resolved by its owner alone.

### F. Safety pause

- Triggered when the safety check flags user input (abuse, violence, self-harm, child at risk).
- User sees calm text and helpline resources (Finland plus international; list is configurable).
- Issue `safety_flag` is set: sharing and sending thread messages are disabled for that issue.
- A SafetyEvent is logged.
- Consultation continues in a limited, supportive mode (separate prompt) focused on safety and support resources.

## 6. AI layer

### Models

- Consultation and rewrites: `claude-sonnet-5-5`
- Safety check, summaries, leak judge: `claude-haiku-4-5`
- Model names are configuration, not code.

### Task functions (`backend/ai/`)

| Function | Output |
|---|---|
| `safety_check(text)` | structured `{flagged, category}` |
| `next_intake_question(turns)` | next question with suggested chips, or `done` |
| `summarize_issue(turns)` | structured IssueSummary |
| `consult(context, history)` | streamed text |
| `consult_safety_mode(context)` | streamed text |
| `draft_share(summary)` | text |
| `polite_rewrite(text, thread_context)` | `{rewrite, harsh: bool}` |
| `perspective_summary(side_records)` | text |
| `leak_check(reply, other_side_raw)` | `ok` or `leaked` |

Structured outputs use JSON schemas and are validated with Pydantic.

### Prompts

- Stored as files: `backend/ai/prompts/<task>/v<N>.md`.
- Active version per task is configuration.
- `ConsultMessage.prompt_version` records which version produced each reply, so tester feedback can be compared across versions.

### Leak guard (shared issues only)

1. Generate the consult reply in full (not streamed).
2. `leak_check`: cheap n-gram overlap against the other side's raw text, then a Haiku judge.
3. If leaked: regenerate once. If it leaks again: show a safe fallback reply.

### Cost control

- Per-user daily AI message cap (configurable).
- Prompt caching for long system prompts.

## 7. Error handling

- **User input is saved before any AI call.** No AI failure loses user text.
- **Claude API failure or timeout:** retry once with backoff, then show "AI is unavailable, your text is saved, try again".
- **Invalid structured output:** retry once, then fall back. Intake fallback: skip to summary editing with a blank template.
- **Safety check failure:** fail closed. Sharing and sending stay blocked until a check succeeds; private consultation continues.
- **Leak check failure:** treat as leaked (regenerate, then fallback).
- **Expired or used invite:** clear page explaining the inviter can resend.

## 8. Security and privacy

### Authentication

- Magic link: single-use token, stored hashed, 15-minute expiry.
- Session: httpOnly, secure, SameSite cookie.

### Authorization

- Every issue endpoint checks the user is a participant.
- Consult sessions check ownership; ThreadMessage `original_text` is returned only to its author.

### Invites

- Token stored hashed, 7-day expiry, bound to the invited email.

### Abuse limits

- Rate limits on login requests, invites, and AI endpoints.

### Data handling

- HTTPS only; database on an encrypted disk.
- Owner can delete an issue they own. Account deletion removes the user's data; thread messages they sent remain for the other participant but are shown as from "a former participant".
- Per-user JSON data export.
- Consent screen at signup: data is processed by Anthropic's API; this is a prototype, not therapy, and not for emergencies.
- Admin view (owner only): SafetyEvents and usage counts (issues created, shared, resolved, feedback ratings). No full issue text.

## 9. Testing

### Automated

- Backend: pytest against a real PostgreSQL in Docker. The Claude client is replaced by a stub returning canned outputs, so tests are deterministic and free.
- Required test areas:
  - **Privacy:** `build_context` never includes the other side's raw text; API refuses cross-user access to consult sessions, intake turns, and original thread text.
  - **Flows:** intake to saved issue; share to invite to accept; thread message to rewrite to send; two-vote resolve; private owner resolve.
  - **Safety:** flagged input disables sharing and logs a SafetyEvent; safety check failure fails closed.
  - **Auth:** token expiry, single use, invite bound to email.
  - **Leak guard:** leaked reply triggers regeneration, then fallback.
- Frontend: Vitest and React Testing Library for key components.
- End-to-end: one Playwright smoke test covering the full two-user path.

### AI quality evals (manual, real API)

- `evals/scenarios/`: about 20 scenario files (family, partner, friend, and safety cases).
- `evals/run.py` runs them against the real API and saves outputs for review before each tester round.
- Review checklist per scenario: consultation names the user's own part where relevant; tone is non-judgmental; rewrite preserves meaning; safety cases are flagged.

### Tester feedback

- Thumbs up/down and optional comment on every AI reply, stored with the prompt version.
