# ISO 2026 Completion Directive — finish the FILE, not the pass

Mission: produce complete ISO14001 2026 and ISO9001 2026 HWPX packages.
The unit of progress is the DOCUMENT, not the form. A session that perfects one
form while 20 sit untouched is a failed session.

Single source of truth: `iso2026_completion_ledger.csv` (25 items, pre-filled
with current true state). Rules for using it:

## Session protocol (every session, no exceptions)

1. **OPEN THE LEDGER FIRST.** Print the status summary (done/in-progress/blocked/
   not-started counts and % complete) before doing anything else.
2. **PLAN THE WHOLE SESSION AS A BATCH.** Select every item executable this
   session — typically 4-8 forms — not one. Items are executable when:
   fill_class is AUTO_* or the CONFIRM decision is already on file, and
   blocking_reason is empty or resolved.
3. **EXECUTE NARROW PASSES BACK-TO-BACK on the same draft lineage.** One pass
   per form (keeps auditability), but chained in one session: draft N feeds
   pass N+1. Verification per pass stays mandatory; do NOT wait for human
   review between passes.
4. **BATCH THE HUMAN GATES.** Accumulate all forms completed this session into
   ONE consolidated review packet (one dashboard, one pasteback covering all
   forms) instead of one review per form. Human attention is the scarcest
   resource in this pipeline — spend it in batches.
5. **UPDATE THE LEDGER** at session end: statuses, blocking reasons, next
   executable items. Commit the ledger change (code/CSV only).
6. **REPORT AGAINST THE WHOLE FILE**: "ISO14001: 9/15 forms done (60%),
   ISO9001: 0/9, blockers: F06 law check, F08 goals approval" — never just
   "pass X succeeded."

## Anti-tunnel-vision rules

- **Two-strike defer:** if a form fails twice in a session, mark BLOCKED with
  the exact reason in the ledger and MOVE ON to the next item. Do not spend a
  session debugging one form while others are executable.
- **No polishing past the guards.** A form whose pass verifies clean
  (V3 + parity + marker + layout QA) is DONE for now. Cosmetic iteration
  happens once, at final assembly (F25), not per form.
- **No new tools mid-session** unless a guard gap blocks MORE THAN ONE ledger
  item. One blocked form = ledger note, not a tool project.
- **Timebox infrastructure:** F16 (ISO9001 template rebuild) is the only
  infra item; it unblocks 8 forms and should be one session, not a phase.
- **HUMAN_ONLY items are already done from automation's perspective** once the
  [HUMAN_INPUT] placeholder structure is written. Do not revisit them.
- **SOURCE_BLANK items are permanently done.** Never re-audit F15.

## Fill-class rules (from the 2026 drafts + change matrix)

| Class | Automation writes | Human provides |
|---|---|---|
| AUTO_STATIC | 2025/2024 values verbatim, new terminology (제조/생산) | nothing |
| AUTO_DATE_ROLL | 2026 dates from calendar pattern | pasteback confirmation |
| AUTO_CONTENT_EVOLVED | latest terms + DEFECT corrections (식품→제조) | per-row confirm of corrections |
| CONFIRM | prepared candidate values | one decision, recorded as file |
| MIXED | the AUTO portion + [HUMAN_INPUT] markers | the human portion |
| HUMAN_ONLY | [HUMAN_INPUT] structure only | all content |
| SOURCE_BLANK | nothing | nothing |

## Order of execution (dependency-sorted)

Session A (ISO14001 sweep): F03,F04,F05,F10,F11,F13 + placeholders F12,F14
  -> one consolidated review packet -> ledger: ISO14001 ~80%
Session B (decisions batch): present F06/F07 law check, F08/F09 goals as ONE
  decision packet; apply approved values same session.
Session C (ISO9001 unblock): F16 template rebuild + inventory, then immediately
  F17,F20,F21,F22 same session (proven patterns transfer from ISO14001).
Session D (ISO9001 decisions): F18,F19,F23,F24 decision packet + apply.
Session E (F25 final assembly): full-document three-way parity, layout QA with
  render, marker sweep, format parity, ONE final Hancom review per standard.
  Output state: FINAL_SUBMISSION_CANDIDATE. FINAL_ACCEPTED requires the
  explicit human acceptance decision file — never inferred.

## Constraints unchanged

Zone-1 drafts only; no original modified; no fabricated actuals; no row append
without FORM_DUPLICATE declaration; every delta manifest-claimed; no NVIDIA/API;
no staging of documents; decision files not chat approvals (R5).
