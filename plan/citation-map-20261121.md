# Citation map: claim -> evidence (2026-11-21, for camera-ready and reviewer discussion)

Status codes: V = metadata verified on Crossref/DOI, ACL Anthology, OpenReview or arXiv
abstract page, and the finding read on the abstract or full text; P = preprint (verified
page, not peer reviewed); U = unverified (search snippet only; do not cite until opened).
"in bib" = already in `paper/AAMAS/refs.bib`. Verified new entries are in
`paper/AAMAS/refs_rebuttal_candidates.bib`. Earlier note: `plan/related-work-check-20261121.md`.

## C1. An equal split acts as a focal default
| Source | Status | Finding used |
|---|---|---|
| Schelling 1960, The Strategy of Conflict | U (book) | Tacit bargainers converge on conspicuous divisions such as an even split |
| Mehta, Starmer, Sugden 1994, AER 84(3):658-673 "The Nature of Salience" | V (JSTOR, no DOI) | Coordination improves on salient labels (Schelling salience); general coordination, not splits |
| Li, Shirado 2025, EMNLP, doi 10.18653/v1/2025.emnlp-main.267 | V | GPT-4o splits equally in 99% of dictator trials; reasoning variants give less |
| Dodivers, Rafai 2025 | in bib | Equal split in ChatGPT dictator decisions read as focal point |
| Fan et al. 2024, AAAI | in bib | Dictator-game preference patterns of LLMs (equality reading U) |
Phrase: the near-fixed equal split matches a focal default seen in human coordination and in LLM dictator games, not a response to incentives.

## C2. Knowing the answer, acting otherwise
| Source | Status | Finding used |
|---|---|---|
| Xu et al. 2025, "Large Language Models Often Say One Thing and Do Another", ICLR 2025 poster, arXiv 2503.07003 | V (venue); number U | Inconsistency between stated answers and actions (the >30% figure unverified) |
| Shen, Clark, Mitra 2025, "Mind the Value-Action Gap", EMNLP, doi 10.18653/v1/2025.emnlp-main.154 | V | Stated values and value-informed actions align poorly (14k+ actions) |
| Sobotka, Karabag, Topcu 2026, arXiv 2605.00226 | P | Acting on decoded beliefs would raise payoffs in about 95% of games (counterfactual estimate) |
| Schmied et al. 2025, "LLMs are Greedy Agents", arXiv 2504.16078 | P | Defines the knowing-doing gap in decision making |
Phrase: correct value answers with unchanged play are an instance of the documented say-do and belief-action gaps.

## C3. Insensitivity to stakes: SCOPE IT, counter-evidence exists
| Source | Status | Finding |
|---|---|---|
| Pal et al. 2026, arXiv 2601.09849 | in bib, P | Claude and Llama unaffected by stopping probability; Gemini and GPT-5 respond: model-dependent |
| Schmidt, Bonati, Kobis, Soraperra 2024, Sci. Rep. 14:22274, doi 10.1038/s41598-024-73306-x | V | GPT-3.5 advice sensitive to reciprocity but not to strategic risk |
| Huynh et al. 2026, payoff scaling (arXiv 2601.19082, Interface Focus) | in bib | COUNTER: payoff scale alone substantially changes cooperation (our own group) |
Phrase: risk insensitivity holds for these models in this game; other work finds payoff-scale effects, so we do not claim general stake insensitivity.

## C4. Recognition and framing
| Source | Status | Finding |
|---|---|---|
| Barrie, Tornberg 2025, arXiv 2505.23796 | P | Naming-game "emergence" indistinguishable from recall; no controlled test of recognition on behaviour |
| Lore, Heydari 2024, Sci. Rep. 14:18490, doi 10.1038/s41598-024-69032-z | V | GPT-3.5 driven by framing; GPT-4 and LLaMa-2 weigh structure and context |
| Robinson, Burden 2025, arXiv 2503.04840 | P | Decisions vary across contexts with the same game structure |
Phrase: models recognise canonical games and respond to framing, yet in our data recognition is universal while play differs, so recognition alone cannot explain it.

## C5. Conditioning on partners' moves
| Source | Status | Finding |
|---|---|---|
| Akata et al. 2025, Nat. Hum. Behav. 9:1380-1390, doi 10.1038/s41562-025-02172-y | in bib, V | Repeated-game play depends on partner behaviour |
| Fontana, Pierri, Aiello 2024, arXiv 2406.13605 | in bib (fontana2024nicer), P | Cooperate only when opponent defection is low; forgiving below 30% |
| Pal et al. 2026 | in bib | History-dependent strategies (Forgiver, WSLS, GRIM, TFT) by model and cost |
Phrase: partner-contingent responses are expected from repeated-game studies; our counterfactual shows they coexist with stake insensitivity.

## C6. State-tracking errors over long histories
| Source | Status | Finding |
|---|---|---|
| Sinha et al. 2026, "The Illusion of Diminishing Returns", ICLR 2026, arXiv 2509.09677 | P (venue U) | Per-step accuracy falls with horizon; earlier own errors in context raise later errors |
| Dai, Fan 2026, arXiv 2605.02028 | P (check title version) | All 205 models lose count abruptly; median capacity 50 items |
Phrase: printing the pool is the right control because LLMs lose track of counts over long contexts; it removes part of the waste, not the default.

## C7. Drift across versions
| Source | Status | Finding |
|---|---|---|
| Chen, Zaharia, Zou 2024, HDSR 6(2), doi 10.1162/99608f92.5317da47 | V | GPT-4 prime identification 84% -> 51% between March and June 2023 |
| Affonso 2026, arXiv 2604.18596 | P | Cooperation generationally unstable: OpenAI 50.3% -> 1.5%, Google 8.3% -> 56.8% |
| Sakai et al. 2026, arXiv 2601.05302 | P | GPT-5 more selective cooperation than earlier GPT models |
Phrase: defaults are version-specific (our Claude Haiku 5.5 versus 4.5), so audits must be rerun per model version.

## C8. Post-training and prosociality: only "consistent with"
| Source | Status | Finding |
|---|---|---|
| Mei et al. 2024, PNAS | in bib | Chatbots more cooperative/altruistic than humans |
| Shapira, Tennenholtz, Reichart 2026, arXiv 2603.17218 | P | Aligned models normative, base models predict human multi-round play better (~10:1) |
No confirmed base-versus-chat test in a prosocial game: never state post-training as the cause.

## C11. Stated reasons are not mechanism
| Source | Status | Finding |
|---|---|---|
| Turpin, Michael, Perez, Bowman 2023, NeurIPS, arXiv 2305.04388 | V (arXiv; NeurIPS listing) | Biasing features steer answers without appearing in explanations; accuracy drop up to 36% |
| Lanham et al. 2023, arXiv 2307.13702 | P | Reliance on stated reasoning varies; larger models often less faithful |
Phrase: Haiku's fairness-citing reasons are stated justification, not evidence about internal computation.

## Do not use until opened
Fan et al. equality reading; Xu et al. ">30%" figure; Chen et al. NBER PDF; Hua et al. jackpot claim;
arXiv 2601.07972, 2610.23860, 2611.03094, 2609.00012, 2502.09053, 2412.12362 (numbers); BFI 2026-29.
