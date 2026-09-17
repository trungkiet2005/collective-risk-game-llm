# Paper — LLMs in the collective-risk social dilemma

Manuscript for the study of instruction-tuned LLM agents playing the Milinski (2008)
collective-risk social dilemma, in the **Royal Society Interface** template, **single column**.

**Title:** *Large language model agents in a collective-risk social dilemma: cooperation tracks prompt salience, not catastrophe risk.*

> **Under revision.** Reviewer report received 2026-08-13; the working plan, the item-by-item
> status and the full reviewer text are no longer tracked as a live document.
> Read that before editing `main.tex`.

## Files
| File | What it is |
|---|---|
| `main.tex` | The manuscript (single-column RSIF). |
| `esm.tex` | Electronic supplementary material: Vietnamese back-translation table, decoding parameters, lottery checks, within-game regressions, anchor strength. Builds standalone with `pdflatex esm` twice; needs the T5 (vntex) encoding for the Vietnamese diacritics. |
| `revision/*.py` | The revision analyses. Each recomputes from the raw logs and writes JSON to `revision/out/`. See the table below. |
| `revision/out/tab_effects.tex`, `tab_axes.tex` | Generated tables, `\input` directly by `main.tex` so they cannot drift from the text. **Regenerate with `python revision/r6_summary_tables.py` before building.** |
| `refs.bib` | 28 references, each web-verified (DOI / arXiv id). |
| `rsproca_new.cls` | RSIF class. Locally patched: bibliography switched from the upstream `biblatex`+`phys` (which fails to load in this TeX install because its section-patch clashes with the class's custom `\@sect`) to `natbib`+bibtex, and the standard `thebibliography`/`\refname`/`\newblock` scaffolding added because the class does not inherit `article.cls`. |
| `figures/*.pdf` | The eleven figures (vector). |
| `make_figures.py` | Regenerates figures 2–7 directly from `../results/open_source/` (self-verifying: numbers come from the raw CSVs). |
| `make_pipeline.py` | Regenerates figure 1 (study-design schematic). Includes an automatic text-overflow check: every text element is validated against its container box. |
| `make_figures_expansion.py` | Figures 8–9 (composition engine, cheap frontier model). |
| `make_figures_toptier.py` | Figure 10 (top-tier panel), globbing `../results/frontier/*/exp_baseline/games.csv`. |
| `revision/r3_round_trajectories.py` | Figure 11 (round-by-round trajectories). |
| `TemplateFigs/` | RSIF logos required by the class. |

### Revision analyses (`revision/`)
| Script | Reviewer item | What it establishes |
|---|---|---|
| `r1_decoding_stability.py` | Q6 | What was actually sent to the hosted models (temperature **is** set, to 0.7); six accidentally duplicated games; permutation ANOVA of contribution on execution batch. |
| `r2_lottery_no_learning.py` | Q7 | The shared lottery cannot feed back into behaviour; drift and prior-catastrophe tests; independent-draw resampling of realised payoffs. |
| `r3_round_trajectories.py` | Q5 | Trajectories, pace-tracking regressions, endgame push near the threshold. Emits `figures/fig11_trajectories.*`. |
| `r4_anchor_strength.py` | W1 / Q1 | How strong the equal-split anchor is, and that the risk null is not confined to models that follow it. |
| `r5_translation_qa.py` | Q2 | Template parity, comprehension accuracy by language and question, tokenisation ratio. Companion prose: `revision/out/r5_backtranslation.md`. |
| `r6_summary_tables.py` | W7 / W8 | Recomputes every effect in the paper and emits the two new tables. |

`revision/_data.py` is the shared loader. **It deliberately never reads
`../results/frontier/crsd_all_models.csv`**, which is stale: that merged file predates the
top-tier sweep and still contains only `gemini-3.1-flash-lite`, so anything joined against
it silently drops the two models the central result rests on. Read the per-model
directories instead, as `make_figures_toptier.py` does.

## Data source
The manuscript now covers both arms:
- `../results/open_source/crsd_all_models.csv` — open-weight behaviour and the composition
  and comprehension studies.
- `../results/open_source/crsd_comprehension_all_models.csv` — in-situ probes.
- `../results/frontier/<model>/exp_baseline/{games.csv,turns.jsonl}` — the commercial arm,
  read per model directory.

## Build
```bash
python make_pipeline.py                     # figure 1
python make_figures.py                      # figures 2-7
python make_figures_expansion.py            # figures 8-9
python make_figures_toptier.py              # figure 10
python revision/r3_round_trajectories.py    # figure 11
python revision/r6_summary_tables.py        # tables 2-3 (\input by main.tex)
pdflatex main && bibtex main && pdflatex main && pdflatex main
pdflatex esm && pdflatex esm                # supplementary
```
Produces `main.pdf` (23 pages) and `esm.pdf` (6 pages). Requires a LaTeX install with
`natbib`, `booktabs`, `eurosym`, `cleveref`, `hyperref`, and — for the supplementary only —
the T5 encoding from `vntex`.

## Author / TODO before submission
- Fill in the author affiliation (`\address{...}`) and confirm the corresponding-author details.
- The behavioural 70B model is Llama-3.1-70B; the comprehension 70B model is Llama-3.3-70B
  (kept labelled distinctly throughout).

## Known design limitations (found by hostile review, 2026-07-20)
1. **The decision prompt names the equal-split solution** ("an average of 2 per player per round", plus a worked payoff example). Some models reproduce it exactly (Gemma-2-9B/EN = 120.0 in 30/30 games, SD=0), so cooperative disposition cannot be separated from compliance with a supplied focal point. The necessary follow-up is to strip the hint and re-run. *(2026-08-13: the hint-free templates and configs now exist — `crsd/prompts/crsd_nohint_*.txt`, `crsd/configs/experiment/exp_nohint.json` — but the run has not been executed. `r4_anchor_strength.py` bounds how much of the null the anchor could explain: essentially none.)*
2. **The risk probe is a retrieval task** — the prompt prints the catastrophe probability verbatim. *(2026-08-13: a `value` probe axis that cannot be answered by retrieval now exists in `crsd/engine/comprehension.py`; run via `exp_evprobe.json`.)*
3. **The catastrophe lottery draws only 10 variates**, seeded per repetition and shared across every model, language and risk level; all fall below 0.5. Catastrophe is reported descriptively only, never used for inference. *(2026-08-13: `r2_lottery_no_learning.py` shows the schedule cannot contaminate behaviour and reports schedule-free payoffs.)*
4. **Analyse contributions paired** (the design uses common random numbers across risk levels); an unpaired analysis badly understates the risk response.
