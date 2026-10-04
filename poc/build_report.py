"""Throwaway: bundle POC runs into a single HTML report (round 2 with round 1 for comparison)."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
load = lambda p: json.loads(p.read_text())
CHANGES = [
    "Intake: never reuse the user's loaded words; always ask how the other person might see it; chips must answer the question.",
    "Summary: never add feelings or needs the user did not state; safety issues are not framed as ordinary disagreements.",
    "Consult: name the user's part scaled to its size, and say directly when it is the main cause; no false balance in either direction.",
    "Consult pushback: do not dilute an honest point or add reassurances that cancel it; acknowledge, restate once gently, move on.",
    "Consult: no claims about outside services, rules or laws unless given.",
    "Safety mode: split into harm-from-others vs self-harm, with different wording and resources; use the user's own words.",
    "Share draft: when the user is the main cause, own it first with no excuses or 'but'.",
    "Rewrite: remove threats, ultimatums, labels and motive guesses; keep the real request or decision; add nothing the author did not say.",
    "Perspective summary: only this side's own concerns, plus the key facts this side relies on.",
]
data = {
    "date": "2026-10-04",
    "scenarios": load(ROOT / "scenarios/scenarios.json"),
    "truth": load(ROOT / "scenarios/ground_truth.json"),
    "outputs": {p.stem: load(p) for p in sorted((ROOT / "runs/v2/outputs").glob("*.json"))},
    "judgment": load(ROOT / "runs/v2/judgments/judgment.json"),
    "prev": load(ROOT / "runs/v1/judgments/judgment.json"),
    "changes": CHANGES,
}
blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
html = (ROOT / "report_template.html").read_text().replace("/*DATA*/null", blob)
(ROOT / "report.html").write_text(html)
print(f"wrote {ROOT / 'report.html'} ({len(html) // 1024} KB)")
