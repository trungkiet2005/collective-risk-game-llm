# Related Work: LLM Agents in Economic / Social-Dilemma / Game-Theory Games

> **Scope.** Multi-agent and single-agent studies (2008 foundational + 2022–2026) in which Large Language Model (LLM) agents play economic, social-dilemma, or game-theoretic games. Focus themes: **cooperation, free-riding, fairness, emergent norms, and human-likeness**. Games covered: public goods, collective-risk social dilemma (CRSD), threshold public goods, iterated prisoner's dilemma (IPD), ultimatum/dictator, common-pool resource (CPR) / tragedy of the commons, trust/donor games.
>
> **How to read this file.** Papers are grouped by theme. Each entry: **Title — Authors (Year, Venue)** · link · 1–3 sentence summary · **Finding:** the key result about LLM cooperation / free-riding / fairness / human-likeness. Items most relevant to *this project* (faithful Milinski-2008 CRSD, cross-language, persona effects) are flagged with markers:
> - 🎯 **CRSD / threshold-PGG with LLMs** — directly adjacent to this project.
> - 🌐 **Language / cross-lingual effects** — relevant to EN vs VN comparison.
> - 🎭 **Persona / personality effects** — relevant to persona manipulation.
> - 🧰 **Benchmark / framework**.
>
> Last updated: 2026-06-20.

---

## 0. Foundational human-subject reference (the game this project faithfully reproduces)

- **The collective-risk social dilemma and the prevention of simulated dangerous climate change — Milinski, Sommerfeld, Krambeck, Reed & Marotzke (2008, *PNAS* 105(7):2291–2294).** https://www.pnas.org/doi/10.1073/pnas.0709546105 · [PubMed](https://pubmed.ncbi.nlm.nih.gov/18287081/)
  The canonical lab CRSD: groups of 6 play ~10 rounds, each starts with an endowment (€40) and per round may invest 0/2/4 into a common climate account; if the group reaches the target sum (€120) the saved money is kept, otherwise with probability *p* (risk) everyone loses all remaining money. A **threshold public good with catastrophic loss under risk**.
  **Finding (human baseline):** Only under **high risk** of loss did about half the groups reach the target; under low/medium risk almost all groups failed. Establishes the risk-dependence, free-riding, and last-minute "edge-of-collapse" dynamics that any faithful LLM reproduction should be benchmarked against.

- *Related human/agent CRSD work for design grounding:* Tavoni et al. (2011, PNAS, CRSD with communication & inequality); **Delegation to autonomous agents promotes cooperation in collective-risk dilemmas** ([arXiv:2103.07710](https://arxiv.org/pdf/2103.07710)); **Learning Collective Action under Risk Diversity** ([arXiv:2201.12891](https://arxiv.org/pdf/2201.12891)) — RL (not LLM) agents in CRSD with heterogeneous risk.

---

## 1. Collective-risk social dilemma & threshold public goods *with LLMs* 🎯

> This is the closest prior art to the present project. As of mid-2026 the literature here is **thin and mostly very recent**, which is a positioning advantage (see §8).

- 🎯🌐 **Evaluating LLMs across behavioral-economics games including threshold collective action (Collective Risk) — multiple 2025–2026 works (arXiv).**
  Several recent papers explicitly fold a **threshold collective-action / collective-risk** game into multi-game LLM test suites. They implement *threshold voting / majority-survival* games where a public good (group survival) is provided only if contributions/choices reach a critical threshold (often 50%), and note the correspondence to CRSDs where individual and collective interests conflict under risk. Representative entries:
  - **More Capable, Less Cooperative? When LLMs Fail At Zero-Cost Collaboration** ([arXiv:2604.07821](https://arxiv.org/pdf/2604.07821)) — finds, counter-intuitively, that more capable models do not reliably cooperate even when cooperation is costless.
  - **Framing Effects in Independent-Agent LLMs: A Cross-Family Behavioral Analysis** ([arXiv:2603.19282](https://arxiv.org/pdf/2603.19282)) — two **logically equivalent** scenarios (individual-survival framing vs collective-survival-conditional-on-majority framing) yield different LLM behavior; demonstrates strong **framing sensitivity** directly relevant to threshold/CRSD wording.
  - **Group size effects and collective misalignment in LLM multi-agent systems** ([arXiv:2510.22422](https://arxiv.org/pdf/2510.22422)) — scaling group size degrades cooperation / induces collective misalignment.
  **Finding:** LLMs are **highly sensitive to framing and group size** in threshold/collective-risk settings, and raw capability does not buy cooperation — but none of these reproduces the *faithful Milinski-2008 mechanism* (per-round binary/ternary investment, explicit risk probability *p*, catastrophic-loss payoff, EN-vs-VN language).

- 🎯 **Coevolutionary dynamics of cooperation, risk, and cost in collective risk games — (2026, arXiv).** [arXiv:2603.20706](https://arxiv.org/pdf/2603.20706)
  Analytical/evolutionary (not LLM) treatment of how risk and cost co-evolve in CRGs. Useful as a **theoretical baseline** for what cooperation rates *should* look like as a function of risk, against which LLM behavior can be compared.

- 🎯 **Cooperative climate action under background risk — (2025, *Scientific Reports*).** https://www.nature.com/articles/s41598-025-12340-9
  Human/modeling CRSD extension adding background risk; useful for designing risk-manipulation conditions.

> **Gap note:** A *faithful* Milinski-2008 CRSD run by LLM agents — same endowments, threshold, risk probability, round structure, and a real cross-language (EN/VN) + persona manipulation — does **not** yet appear in the literature. See §8.

---

## 2. Public goods games & free-riding with LLMs 🧰

- 🎭 **Corrupted by Reasoning: Reasoning Language Models Become Free-Riders in Public Goods Games — Guzman Piedrahita, Yang, Sachan, Ramponi, Schölkopf & Jin (2025, COLM 2025).** [arXiv:2506.23276](https://arxiv.org/abs/2506.23276) · [OpenReview](https://openreview.net/forum?id=kH6LOHGjEl)
  Adapts a **public goods game with institutional choice + costly sanctioning** over repeated rounds; identifies four behavioral archetypes (stable cooperators, fluctuators, decliners, rigid).
  **Finding:** **Reasoning models (o1 series) free-ride significantly more** than some traditional LLMs; chain-of-thought can lead a model to *recognize free-riding as optimal*. Improving reasoning ≠ improving cooperation — a key cautionary result.

- 🧰 **Everyone Contributes! Incentivizing Strategic Cooperation in Multi-LLM Systems via Sequential Public Goods Games (MAC-SPGG) — (2025, OpenReview / ResearchGate).** [OpenReview PDF](https://openreview.net/pdf/6ae4e1e028d0b4d389a7e44d33b0876ce92c6c2b.pdf) · [ResearchGate](https://www.researchgate.net/publication/394292931)
  Proposes a **sequential** PGG where agents move in order, observe predecessors, and the reward structure is redesigned so that effortful contribution is the **unique Subgame-Perfect Nash Equilibrium**.
  **Finding:** A mechanism-design fix that **provably eliminates free-riding** in multi-LLM systems — contrast with the spontaneous free-riding observed elsewhere.

- **The Role of Social Learning and Collective Norm Formation in Fostering Cooperation in LLM Multi-Agent Systems — (2025, arXiv).** [arXiv:2510.14401](https://arxiv.org/pdf/2510.14401)
  Studies PGG-style cooperation emerging via social learning and norm formation.
  **Finding:** Social learning + collective norm formation raise cooperation — **emergent-norm evidence** for LLM societies.

- **Will Systems of LLM Agents Cooperate: An Investigation into a Social Dilemma — (2025, arXiv).** [arXiv:2501.16173](https://arxiv.org/abs/2501.16173)
  Prompts SOTA LLMs to generate *complete strategies* for an iterated social dilemma, then runs **evolutionary game-theory** simulations over populations of aggressive/cooperative/neutral dispositions.
  **Finding:** Distinct **model-specific biases**: ChatGPT-4o and Claude 3.5 Sonnet show a **cooperative bias**; Claude struggles to even produce effective *aggressive* strategies.

- **Simulating Cooperative Prosocial Behavior with Multi-Agent LLMs — (2025, arXiv).** [arXiv:2502.12504](https://arxiv.org/pdf/2502.12504)
  Multi-agent prosociality study aimed at informing policy.
  **Finding:** LLMs can sustain prosocial/cooperative behavior; mechanisms (reciprocity, communication) matter.

---

## 3. Iterated Prisoner's Dilemma & repeated games

- 🌐🎭 **Playing repeated games with Large Language Models — Akata, Schulz, Schölkopf, et al. (2025, *Nature Human Behaviour*; preprint 2023).** [Nature](https://www.nature.com/articles/s41562-025-02172-y) · [arXiv:2305.16867](https://arxiv.org/pdf/2305.16867) · [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12283376/)
  Systematic study of LLMs across 2×2 repeated games (incl. IPD, Battle of the Sexes).
  **Finding:** LLMs excel at **self-interested** games but are poor coordinators; **GPT-4 is unforgiving/retaliatory** in IPD (defects after a single defection) — can be nudged to forgive by noting opponents make mistakes. A landmark behavioral-economics-of-LLMs reference.

- **Can large language models overcome opportunistic behavior in the prisoner's dilemma? — (2025, ResearchGate).** [link](https://www.researchgate.net/publication/390443047)
  Tests incentive strategies (tit-for-tat, tit-for-two-tats, grim trigger) on LLM cooperation.
  **Finding:** Reciprocal incentive schemes raise LLM cooperation; **tit-for-two-tats works best** at curbing opportunism.

- **Strategies of cooperation and defection in five large language models — (2026, arXiv).** [arXiv:2601.09849](https://arxiv.org/pdf/2601.09849)
  Compares Claude Sonnet 4, Gemini 2.5 Pro, GPT-4o and others in repeated PD.
  **Finding:** Marked cross-model strategy differences in cooperation vs defection propensity.

- **Strategic Intelligence in LLMs: Evidence from evolutionary Game Theory — (2025, arXiv).** [arXiv:2507.02618](https://arxiv.org/pdf/2507.02618)
- **Strategic Behavior of LLMs: Game Structure vs. Contextual Framing — (2023, arXiv).** [arXiv:2309.05898](https://arxiv.org/pdf/2309.05898) — 🌐 framing/context can dominate game structure.
- **GPT in Game Theory Experiments — (2023, arXiv).** [arXiv:2305.05516](https://arxiv.org/pdf/2305.05516)

---

## 4. Common-pool resource / tragedy of the commons with LLMs 🧰

- 🧰 **Cooperate or Collapse: Emergence of Sustainable Cooperation in a Society of LLM Agents (GovSim) — Piatti, Jin, Kleiman-Weiner, Schölkopf, Sachan & Mihalcea (2024, NeurIPS 2024).** [arXiv:2404.16698](https://arxiv.org/abs/2404.16698) · [code](https://github.com/giorgiopiatti/GovSim)
  **GovSim** = Governance-of-the-Commons Simulation: LLM agent societies in CPR dilemmas (fishing, pasture, pollution) with a *harvest* phase and a natural-language *discussion* phase.
  **Finding:** **All but the most powerful LLMs fail** to reach a sustainable equilibrium (best survival rate **< 54%**); failure stems from inability to reason about long-term equilibrium effects. **"Universalization" moral reasoning and inter-agent communication markedly improve sustainability.** A central CPR benchmark/framework for this area.
  *Follow-ups:* Reproducibility study ([OpenReview](https://openreview.net/forum?id=ON8EMrNwww)); newer small models (e.g., DeepSeek-R1-Distill-Qwen-14B) now reach sustainable equilibria, narrowing the size gap.

- **Communication Enables Cooperation in LLM Agents: A Comparison with Curriculum-Based Approaches — (2025, arXiv).** [arXiv:2510.05748](https://arxiv.org/pdf/2510.05748)
  **Finding:** Natural-language communication is a strong lever for CPR cooperation, rivaling curriculum methods.

---

## 5. Ultimatum, dictator & trust/donor games — fairness and human-likeness

- 🎭 **Benevolent Dictators? On LLM Agent Behavior in Dictator Games — (2025, arXiv).** [arXiv:2511.08721](https://arxiv.org/pdf/2511.08721) · [ResearchGate](https://www.researchgate.net/publication/397556036)
  **Finding:** LLM "dictators" allocate **more generously than humans** on average; allocations shift with **persona/role** instructions and are not purely payoff-maximizing — fairness preferences appear, but their robustness varies.

- **Simulating Human Decision-Making in Ultimatum Games using LLMs — (2025, ACM Collective Intelligence Conf.).** [ACM](https://dl.acm.org/doi/10.1145/3715928.3737473)
  **Finding:** LLMs can approximate human UG patterns (fair proposals, rejection of unfair offers) but deviate in consistency; UG is a demanding fairness+punishment testbed.

- 🎭 **When artificial minds negotiate: Dark personality and the Ultimatum Game in LLMs — (2026, *ScienceDirect*).** [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2949882126000320) · [ResearchGate](https://www.researchgate.net/publication/401190178)
  **Finding:** Inducing **Dark-Triad personas** systematically shifts UG offers/rejections — direct evidence that **persona conditioning changes fairness behavior**.

- **GPT-3.5 altruistic advice is sensitive to reciprocal concerns but not strategic risk — (2024, PMC).** [PMC11436787](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11436787/)
  **Finding:** LLM prosocial advice tracks reciprocity but ignores strategic risk — a human-likeness asymmetry.

- **The Good, the Bad, and the Hulk-like GPT: Emotional Decisions of LLMs in Cooperation and Bargaining Games — (2024, arXiv).** [arXiv:2406.03299](https://arxiv.org/html/2406.03299v1)
  **Finding:** Emotional/persona priming (e.g., anger) shifts bargaining and cooperation outcomes.

- **Cultural Evolution of Cooperation among LLM Agents — Vallinder & Hughes (2024, arXiv).** [arXiv:2412.10270](https://arxiv.org/abs/2412.10270) · [code](https://github.com/aronvallinder/llm-donor-game/)
  Generational **Donor Game** (indirect reciprocity): 12 agents/gen, top-50% survive and pass strategies to the next generation; tests whether norms culturally evolve.
  **Finding:** **Claude 3.5 Sonnet societies evolve robust cooperation across generations** (and exploit costly punishment); **Gemini 1.5 Flash and GPT-4o do not** — strong cross-model emergent-norm result.

- **Reputation as a Solution to Cooperation Collapse in LLM-based MAS — (2025, arXiv).** [arXiv:2505.05029](https://arxiv.org/pdf/2505.05029) — reputation mechanisms restore cooperation.

---

## 6. Persona / personality effects on LLM cooperation 🎭

- 🎭 **Big Five Personality Profiles in LLMs / personality steering — (2025).** [EmergentMind topic](https://www.emergentmind.com/topics/big-five-personality-profiles-in-llms) · **Identifying Cooperative Personalities via Representation Engineering** ([arXiv:2503.12722](https://arxiv.org/html/2503.12722)) · **Dynamic Personality in LLM Agents** ([ACL Findings 2025](https://aclanthology.org/2025.findings-acl.1185.pdf))
  **Finding:** Big-Five conditioning produces **trait-consistent** play: **agreeableness ↑ cooperation, extraversion ↓ cooperation** in social dilemmas; personality can be steered via prompts or representation engineering. Direct support for persona manipulations.

- **Evolution of Cooperation in LLM-Agent Societies: punishment strategies — (2025, arXiv).** [arXiv:2504.19487](https://arxiv.org/pdf/2504.19487)
- **Explicit Cooperation Shapes Human-Like Multi-agent LLM Negotiation — (2025, ICWSM workshop).** [PDF](https://workshop-proceedings.icwsm.org/pdf/2025_34.pdf)
- **Interpretable Risk Mitigation in LLM Agent Systems — (2025, arXiv).** [arXiv:2505.10670](https://arxiv.org/pdf/2505.10670)

---

## 7. Language / cross-lingual effects on strategic behavior 🌐

> Most relevant to the **EN vs VN** axis of this project.

- 🌐🧰 **FAIRGAME: a Framework for AI Agents Bias Recognition using Game Theory — Buscemi, Proverbio, Di Stefano, Han, Castignani & Liò (2025, arXiv; rev. 2026).** [arXiv:2504.14325](https://arxiv.org/abs/2504.14325)
  Software+method framework that simulates LLM agents in classic games while varying **model, language, personality, and strategic knowledge**, and compares outcomes against game-theoretic predictions.
  **Finding:** Biased outcomes depend jointly on **which LLM, which language, and which persona** — i.e., **language and persona are first-class experimental variables**. This is the closest *methodological* analogue to the present project's design (and a candidate baseline/comparison framework).

- 🌐 **Understanding LLM Agent Behaviours via Game Theory: Strategy Recognition, Biases and Multi-Agent Dynamics — (2025, arXiv).** [arXiv:2512.07462](https://arxiv.org/abs/2512.07462)
  **Finding:** Systematic **model-specific biases that resist persona prompting**: Claude stays prosocial even under selfish framing; **GPT-4o shows extreme linguistic sensitivity**; Mistral is language-invariant. Concrete evidence that **language can shift outcomes more than persona for some models**.

- 🌐 **The Language of Bargaining: Linguistic Effects in LLM Negotiations — (2026, arXiv).** [arXiv:2601.04387](https://arxiv.org/html/2601.04387)
  **Finding:** **Language choice can shift negotiation outcomes more strongly than model architecture**; effects depend on game structure (e.g., distributive vs integrative). Direct support for expecting EN vs VN divergence.

- 🌐 **GLEE: A Unified Framework and Benchmark for Language-based Economic Environments — (2024, arXiv).** [arXiv:2410.05254](https://arxiv.org/pdf/2410.05254) — 🧰 standardized language-based economic games.

---

## 8. Benchmarks & frameworks for LLM agents in games (quick reference) 🧰

| Framework | Game(s) / focus | Link | Relevance here |
|---|---|---|---|
| **GovSim** | CPR sustainability (fishing/pasture/pollution), harvest+discussion | [arXiv:2404.16698](https://arxiv.org/abs/2404.16698) · [code](https://github.com/giorgiopiatti/GovSim) | Closest CPR analogue; universalization & communication levers |
| **FAIRGAME** 🌐🎭 | Matrix/repeated games × **language × persona** bias auditing | [arXiv:2504.14325](https://arxiv.org/abs/2504.14325) | Closest methodological analogue (lang+persona) |
| **GLEE** 🌐 | Language-based economic environments (bargaining, trading, persuasion) | [arXiv:2410.05254](https://arxiv.org/pdf/2410.05254) | Standardized economic-game harness |
| **MACHIAVELLI** | 134 text adventures; ethics vs reward, power-seeking, deception | [site](https://aypan17.github.io/machiavelli/) · [arXiv:2304.03279](https://arxiv.org/abs/2304.03279) (ICML 2023) | Ethics/deception baseline, not a dilemma game per se |
| **GAMA-Bench / γ-bench** | 8 multi-agent games incl. PGG; "gaming ability" | [arXiv:2403.11807](https://arxiv.org/pdf/2403.11807) | Includes PGG scoring |
| **GameBench / TMGBench / M3-Bench** | broad strategic-reasoning / mixed-motive suites | [M3-Bench arXiv:2601.08462](https://arxiv.org/pdf/2601.08462) | Mixed-motive process-aware eval |
| **Survey: Game Theory Meets LLMs** | taxonomy of GT×LLM research | [IJCAI 2025](https://www.ijcai.org/proceedings/2025/1184.pdf) · [arXiv:2502.09053](https://arxiv.org/abs/2502.09053) | Best single survey to cite |
| **Evaluating Collective Behaviour of Hundreds of LLM Agents** | large-N emergent dynamics | [arXiv:2602.16662](https://arxiv.org/pdf/2602.16662) | Scale dynamics |

---

## 9. Gap & positioning — what is novel about THIS project

**This project:** *LLM agents playing a **faithful Milinski-2008 collective-risk game**, with a **cross-language EN vs VN** comparison and **persona effects**.*

Synthesizing §§1–8, the literature has each ingredient **separately** but not the combination:

1. **Faithful CRSD mechanism is missing.** LLM work that touches "collective risk" almost always uses a **simplified threshold-voting / majority-survival proxy** (§1: 2603.19282, 2510.22422, 2604.07821) or studies **CPR sustainability** (GovSim, §4) or **standard/sequential PGG** (§2). None reproduces Milinski-2008's exact apparatus: fixed endowment, per-round discrete investments, an explicit **target threshold**, an explicit **risk probability *p* of catastrophic total loss** if the target is missed, and the resulting **"edge-of-collapse" / last-round** dynamics. The original human result (cooperation is **risk-dependent**) has, to our knowledge, **never been tested on LLM agents with fidelity**. → **Novelty 1: first faithful LLM reproduction of Milinski-2008 CRSD**, enabling direct human-vs-LLM comparison on the *same* payoff structure (e.g., does LLM cooperation rise with risk *p* as humans' did? do LLMs free-ride to the threshold? do they show end-game collapse?).

2. **Cross-language EN vs VN is unstudied for CRSD.** Language clearly matters (§7: FAIRGAME, 2512.07462, 2601.04387, GLEE) — language can outweigh model architecture — but existing cross-lingual work covers high-resource European and Indic languages and *non-CRSD* games. **Vietnamese (a comparatively lower-resource, culturally distinct language) in a collective-risk/climate dilemma is absent.** → **Novelty 2: a controlled EN-vs-VN comparison** isolating whether language shifts cooperation, free-riding, fairness, and threshold-reaching in a faithful CRSD — testing whether prosociality/risk-response is **language-invariant or language-dependent**, and whether VN framings (collectivist cues) raise cooperation.

3. **Persona effects within CRSD, crossed with language, are unstudied.** Persona/Big-Five conditioning reliably shifts cooperation (§6) and fairness (§5: Dark-Triad UG), and FAIRGAME varies persona — but **not inside a faithful CRSD, and not crossed with EN/VN**. → **Novelty 3: a persona × language factorial in CRSD**, asking whether persona effects are **consistent across languages** or interact with them (e.g., does an "agreeable/selfish" persona behave differently in VN vs EN?), and whether persona can rescue or destroy threshold-reaching under varying risk.

4. **Methodological contribution.** Combining (a) **fidelity to a classic human experiment** (so human data is a real baseline), (b) a **2×N language manipulation**, and (c) a **persona manipulation**, in one CRSD design, yields a uniquely clean test of *human-likeness* (do LLMs replicate the Milinski risk effect?), *robustness* (does it survive translation to VN?), and *steerability* (do personas move cooperation predictably?). This goes beyond FAIRGAME's matrix-game bias auditing and GovSim's CPR setting by targeting the **specific catastrophic-threshold-under-risk structure** most relevant to real climate/collective-action policy.

**One-line positioning:** *We provide the first faithful LLM reproduction of the Milinski-2008 collective-risk social dilemma and use it as a controlled testbed for two under-explored axes — cross-language (EN vs VN) and persona — measuring LLM cooperation, free-riding, fairness, and threshold-reaching against the human risk-dependence baseline.*

---

## 10. Key open questions this project can answer (and prior hints)

- **Risk-dependence (human-likeness):** Do LLMs cooperate more as risk *p* rises, like humans (Milinski 2008)? Prior framing-sensitivity results (§1) suggest the answer is non-trivial.
- **Free-riding / threshold behavior:** Do LLMs contribute *just enough* to hit the threshold then stop (efficient free-riding), collapse near the end, or over-contribute? PGG free-riding evidence (§2) and reasoning-model free-riding (2506.23276) are relevant priors.
- **Reasoning vs cooperation:** Do reasoning/"thinking" models free-ride more in CRSD, as in PGG (2506.23276)?
- **Language:** Is the risk effect / cooperation rate stable EN→VN, or does VN (collectivist framing, lower-resource) shift it (§7)?
- **Persona:** Do agreeableness/selfishness personas move CRSD cooperation predictably, and is the effect language-invariant (§6, FAIRGAME §7)?
- **Emergent norms / communication:** If a discussion phase is added, does communication rescue cooperation as in GovSim and §2/§4?

---

### Source index (primary links)
- Milinski 2008 CRSD — https://www.pnas.org/doi/10.1073/pnas.0709546105
- Corrupted by Reasoning (PGG free-riding, COLM 2025) — https://arxiv.org/abs/2506.23276
- MAC-SPGG (sequential PGG) — https://openreview.net/pdf/6ae4e1e028d0b4d389a7e44d33b0876ce92c6c2b.pdf
- Will Systems of LLM Agents Cooperate — https://arxiv.org/abs/2501.16173
- Playing repeated games with LLMs (Nat. Hum. Behav. 2025) — https://www.nature.com/articles/s41562-025-02172-y
- GovSim / Cooperate or Collapse (NeurIPS 2024) — https://arxiv.org/abs/2404.16698
- Cultural Evolution of Cooperation (Donor Game) — https://arxiv.org/abs/2412.10270
- Benevolent Dictators? (Dictator game) — https://arxiv.org/pdf/2511.08721
- Dark personality & Ultimatum Game — https://www.sciencedirect.com/science/article/pii/S2949882126000320
- FAIRGAME (language × persona framework) — https://arxiv.org/abs/2504.14325
- Understanding LLM Agent Behaviours via Game Theory — https://arxiv.org/abs/2512.07462
- The Language of Bargaining — https://arxiv.org/html/2601.04387
- GLEE — https://arxiv.org/pdf/2410.05254
- MACHIAVELLI (ICML 2023) — https://arxiv.org/abs/2304.03279
- Survey: Game Theory Meets LLMs (IJCAI 2025) — https://arxiv.org/abs/2502.09053
- Framing effects (threshold survival) — https://arxiv.org/pdf/2603.19282
- More Capable, Less Cooperative — https://arxiv.org/pdf/2604.07821
- Group size effects / collective misalignment — https://arxiv.org/pdf/2510.22422
