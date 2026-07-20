# Paper — LLMs in the collective-risk social dilemma

Manuscript for the study of instruction-tuned LLM agents playing the Milinski (2008)
collective-risk social dilemma, in the **Royal Society Interface** template, **single column**.

**Title:** *Large language model agents in a collective-risk social dilemma: cooperation tracks prompt salience, not catastrophe risk.*

## Files
| File | What it is |
|---|---|
| `main.tex` | The manuscript (single-column RSIF). |
| `refs.bib` | 19 references, each web-verified (DOI / arXiv id). |
| `rsproca_new.cls` | RSIF class. Locally patched: bibliography switched from the upstream `biblatex`+`phys` (which fails to load in this TeX install because its section-patch clashes with the class's custom `\@sect`) to `natbib`+bibtex, and the standard `thebibliography`/`\refname`/`\newblock` scaffolding added because the class does not inherit `article.cls`. |
| `figures/*.pdf` | The seven figures (vector). |
| `make_figures.py` | Regenerates figures 2–7 directly from `../results/open_source/` (self-verifying: numbers come from the raw CSVs). |
| `make_pipeline.py` | Regenerates figure 1 (study-design schematic). Includes an automatic text-overflow check: every text element is validated against its container box. |
| `TemplateFigs/` | RSIF logos required by the class. |

## Data source
All numbers and figures come **only** from `../results/open_source/`:
- `crsd_all_models.csv` (behaviour, `experiment=='exp_baseline'`, 7 models).
- `crsd_comprehension_all_models.csv` (in-situ comprehension probes, 7 models).
The `exp_test` ablations (framing / memory / persona) are deliberately excluded.

## Build
```bash
python make_pipeline.py       # figure 1
python make_figures.py        # figures 2-6
pdflatex main && bibtex main && pdflatex main && pdflatex main
```
Produces `main.pdf` (13 pages). Requires a LaTeX install with `natbib`, `booktabs`,
`eurosym`, `cleveref`, `hyperref` (all standard).

## Author / TODO before submission
- Fill in the author affiliation (`\address{...}`) and confirm the corresponding-author details.
- The behavioural 70B model is Llama-3.1-70B; the comprehension 70B model is Llama-3.3-70B
  (kept labelled distinctly throughout).

## Known design limitations (found by hostile review, 2026-07-20)
1. **The decision prompt names the equal-split solution** ("an average of 2 per player per round", plus a worked payoff example). Some models reproduce it exactly (Gemma-2-9B/EN = 120.0 in 30/30 games, SD=0), so cooperative disposition cannot be separated from compliance with a supplied focal point. The necessary follow-up is to strip the hint and re-run.
2. **The risk probe is a retrieval task** — the prompt prints the catastrophe probability verbatim.
3. **The catastrophe lottery draws only 10 variates**, seeded per repetition and shared across every model, language and risk level; all fall below 0.5. Catastrophe is reported descriptively only, never used for inference.
4. **Analyse contributions paired** (the design uses common random numbers across risk levels); an unpaired analysis badly understates the risk response.
