# Related-work check, 2026-11-21 (for the AAMAS 2027 rebuttal and camera-ready)

Checked on each arXiv abstract page unless marked "snippet". Before any item enters
`paper/AAMAS/refs.bib`, open the page again and take the metadata from it.

## Already cited in the submission
willis2026evaluating (arXiv 2602.16662), guzmanpiedrahita2025corrupted (COLM 2025,
arXiv 2506.23276), pal2026large (arXiv 2601.09849), akata2025playing (Nat. Hum. Behav. 2025).

## Our own preprint
arXiv 2610.22882 (16 Oct 2026) is this paper. AAMAS 2027 allows archival preprints but asks
authors not to publicise during review. Never cite it as outside work.

## Candidates to add
| Item | What it shows | Use |
|---|---|---|
| Barrie, Tornberg, "Emergent LLM behaviors are observationally equivalent to data leakage", arXiv 2505.23796, 2025 | Naming-game conventions are indistinguishable from recall of the game; no controlled test isolating recognition | Cited by a reviewer; position: our zero-risk and stake-invariance tests are not predicted by recognition alone, and recognition is universal across our models while play differs |
| Li, Shirado, "Spontaneous Giving and Calculated Greed in Language Models", EMNLP 2025, arXiv 2502.17720 | Reasoning reduces cooperation; equal splits in dictator games (99% figure from snippet, unverified) | Focal equal split; supports the default reading |
| Sobotka, Karabag, Topcu, "Why Do LLMs Struggle in Strategic Play?", arXiv 2605.00226, 2026 | Belief-to-action gap (Llama 3.1, Qwen3, gpt-oss) | Supports the answers-versus-play gap |
| Affonso, "Large language models converge on competitive rationality but diverge on cooperation across providers and generations", arXiv 2604.18596, 2026 | Cooperation shifts strongly across model generations (OpenAI down, Google up) | Version drift; matches Claude Haiku 5.5 differing from Haiku 4.5 at p = 0 (generalisation wave) |
| Sakai et al., "Effects of personality steering on cooperative behavior in LLM agents", arXiv 2601.05302, 2026 | GPT-5 cooperates more selectively than earlier GPT models | Version drift |

## Snippet only, not opened
arXiv 2604.20658 (41 open-weight LLMs, six games incl. collective risk); arXiv 2606.27951
(persuasive framing in a collective-risk game); arXiv 2610.33651 (three social dilemmas);
arXiv 2504.16078 (knowing-doing gap in bandits); arXiv 2610.01222 (end-game behaviour across
Claude 4.6, Gemini 3, GPT-5.2).

## Gap
No paper found that varies only the opponents' past moves in a risk game, or that uses the
six-player, ten-round design with risk set to zero (search result, not proof of absence).
