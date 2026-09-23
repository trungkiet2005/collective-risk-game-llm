# E8 completed: evidence and remaining submission work

## Accepted execution, not a proposed experiment

All four final replacement tasks completed on 18 September 2026 under the single
existing authorized profile `tnkiet`, without quota-driven profile switching or
new credit purchases. The final fail-closed audit returned exit code 0 with:

- 350/350 registered games, 21,000/21,000 turn records, 300/300 numeric probes.
- All 35 model/arm/risk cells contain ten games with reps 0 through 9.
- 26 complete non-overlapping source runs selected; 18 other original-panel runs
  excluded as incomplete, invalid, overlapping, or not needed by the fixed cover.
- No missing cell. Incorrect parsed probe answers were retained, not filtered.

The native wide-CSV conversion was independently checked with `verify_wide.py`:
350 games in 35 files passed all existing invariants and five-model balance.
This is a separate follow-up to the original 3,950-game panel, not a replacement
or a change to the data behind Figures 3 and 5.

## Reproducible products

`paper/AAMAS/analysis/e8_controls.py` produced 350 game rows, 100 game/question
probe rows, 35 contribution contrasts, and ten probe summaries. Contribution
means use six model seats in self-play and only the focal model seat in scripted
partner controls. Confidence intervals use 5,000 independent game-level bootstrap
resamples. Matching API seed labels do not justify paired inference. Intervals
are pointwise, not multiplicity-corrected simultaneous intervals. Zero-width
bootstrap intervals from constant observations do not establish population certainty.

The accepted wide/probe/provenance archive currently resides on the authorized
pod at `/tmp/crg-e8-release-20260918.zip`; it has not been copied into this GitHub
branch or into the anonymous submission package. Raw downloaded notebooks, prompts,
turns, run metadata and the complete acceptance manifest remain under
`plan/runs/submission_audit/` in the pod working clone. That directory is not a
tracked public data release. The portable manifest includes account-relative
provenance; anonymize it before placing it in a blind-review supplement.

Reproduction, from the repository root with an absolute archive path:

```sh
python plan/scripts/audit_e8_panel.py "$DOWNLOADS" --output "$AUDIT/e8_final_gate.json"
python paper/AAMAS/analysis/e8_controls.py "$AUDIT/e8_final_gate.json" --output "$AUDIT/e8_analysis"
python plan/scripts/package_e8_accepted.py "$AUDIT/e8_final_gate.json" --downloads "$DOWNLOADS" --out /tmp/crg-e8-release-new
python plan/scripts/verify_wide.py --wide /tmp/crg-e8-release-new/results --expect-reps 10
```

Verified SHA-256 digests of pod artifacts (CSV files there use CRLF line endings):

| Artifact | SHA-256 |
|---|---|
| Final raw/source acceptance manifest | `de5ec70bd7d35c6122ae2268ee05d03a5f2b123b69e780130729be20d67dea7b` |
| Native wide/probe/provenance ZIP, 58,819 bytes | `6c8c764d6c1acfe212715f056dfdaa95321046d128e645d21c2c37e5fcc7ea5c` |
| Portable manifest within that archive | `8cbd8592ef2b5e39fbd744a0b6bb5109463b432227c573b775608dc0278954e3` |
| Exact contrast CSV | `3b876611882ff7fc498e4acd5038b1408900790448440333c4be047145fabb06` |
| Exact probe-summary CSV | `02ff257f8bf6c9e6f8afdd431c482a455a0a8a52d51590d4433ad446c725a438` |

## Findings requiring manuscript reconciliation

The following are descriptive follow-up estimates, not claims of causal mediation
or a unique internal reasoning mechanism. Full per-cell values, including
unfavourable results, are in `paper/AAMAS/analysis/followups/e8_contrasts.csv`.

1. Printing the running pool at p=0 reduces Grok's mean contribution from 37.40
   to 20.20 units per seat (difference -17.20; pointwise 95% bootstrap interval
   [-18.43, -15.67]). This substantially changes its magnitude, but does not remove
   positive contribution where zero is individually dominant. Do not claim that
   arithmetic/visibility is irrelevant to behaviour.
2. In the p=0 numeric-probe arm, Flash-Lite and Qwen answer both probe questions
   correctly in all 30 observed answers per question, while contributing 20.03
   and 18.07 units per seat. Luna answers correctly and contributes zero. Haiku
   gets 70% of numerical expected-value answers and 100% of comparisons correct;
   Grok gets 56.67% and 46.67%. Do not generalize complete knowledge to all models.
3. Group-payoff framing produces maximum contribution (40 units per seat) for
   Grok at all three tested risks, leaving zero retained payoff. Qwen rises to
   30.93 at p=0.9 from baseline 18.40. Higher contribution or target success is not
   synonymous with higher welfare or equilibrium play.
4. Visible-pool scripted-partner responses are model-dependent. For example,
   Qwen falls from 19.20 to 13.20 with always-four partners, but rises from 28.80
   to 36.40 with always-zero partners. Do not claim a universal repair effect.

## Readiness state

Figure PR #1 is merged in `main` at `9a3a87f665dfbd029c461db117fb31dbeb729214`.
The pre-result scientific revision passed 466 current tests (two documented
legacy moved-module test files excluded), including an exhaustive check of the
p=1 static-equilibrium boundary over 230,230 unordered contribution profiles.
The E8 analysis and native packaging were then executed successfully on accepted
raw evidence. The public figure-final PDF still describes the original panel:
E8 is NOT YET incorporated into its results, threats-to-validity section, abstract,
or supplementary tables. Code/evidence completion is not full submission readiness.

The scientific PR #2 remains open pending final review and workflow approval.
A bot-generated follow-on workflow entered `action_required`; a maintainer should
approve it through GitHub's ordinary approval mechanism, not bypass it. Preserve
an accurate final-head test/build status rather than citing an earlier green run.

Human authors must also review and complete the AI-assistance disclosure required
by the AAMAS 2027 policy when AI contributed to methodology/experimental design.
This session included code, audit and scientific-analysis assistance. Earlier use
history and the exact backend build are not fully retained; do not invent either
an exact model version, missing prompts, or an assertion of human verification.
No OpenReview submission or author-registration action has been performed.
