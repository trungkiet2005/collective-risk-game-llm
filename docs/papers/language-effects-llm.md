# How Prompt Language Affects LLM Behavior, Reasoning, Values, and Decision-Making

> **Scope.** A literature survey on how the *language of the prompt* (English vs. non-English, with emphasis on Vietnamese and other low/mid-resource languages) changes what large language models (LLMs) do — their reasoning quality, expressed values, risk attitudes, and choices in social/economic/game/moral settings. Built to support an **English-vs-Vietnamese (EN-vs-VN) collective-risk-game** study with **small open-source models** (Qwen, Llama, Gemma 7-8B), extending the FAIRGAME framework.
>
> **Status:** living document. **Last updated:** 2026-06-20.
> **Audience:** AI agents and researchers on this project. Dense, link-first, claim-first.

---

## 0. TL;DR (the load-bearing claims)

1. **Prompt language is a first-class experimental variable, not a cosmetic translation.** Switching the prompt language can shift baseline cooperation, fairness, risk attitude, and moral judgment by amounts **comparable to switching the model architecture itself** (FAIRGAME; Mensfelt et al.). Treat language as a manipulated factor with its own main effect and interactions.
2. **LLMs are internally English-centric.** Multilingual models tend to *reason in an English-like representation space* and translate out to the prompt language, so non-English prompts route through a partly-translated pathway. This (a) degrades reasoning, especially for low-resource languages, and (b) makes "values in language X" partly an artifact of English priors rather than genuine cultural grounding (Wendler/Zhong "Do Multilingual LLMs Think in English?"; Tam et al. "Language Matters").
3. **Cultural/value/risk shifts are real but unreliable as cultural signal.** Prompt language *does* move expressed values and risk attitudes, but often **not toward the actual values of speakers of that language** — explicit cultural framing ("answer as a Vietnamese person") moves alignment more than language alone (Kharchenko et al. 2511.03980; MENAValues).
4. **Small open models (7-8B) show the largest non-English degradation and instability.** Qwen/Gemma are comparatively balanced among small models; Llama and Mistral tend to drop more in low/mid-resource languages. Functional/reasoning gaps are much larger than static-knowledge gaps. Expect the *largest* EN-vs-VN divergence precisely in the 7-8B regime you are using.
5. **Vietnamese specifically:** mid-resource, frequently shows defection-heavy *or* unconditional-cooperation extremes depending on model — i.e., **high variance**, not a clean "collectivist => more cooperation" story. Plan for noise and per-model effects.
6. **Methodology matters more than usual.** Because effects are confounded by translation quality, tokenization, and English-pivot reasoning, a clean EN-vs-VN claim *requires* back-translation QC, semantic-equivalence checks, native review, and holding payoff/structure/seed/decoding constant. Section 6 is the protocol.

---

## 1. Cross-lingual (in)consistency of decisions and reasoning quality

### 1.1 Models think in English even when prompted otherwise

- **Do Multilingual LLMs Think in English?** — Wendler/Zhong et al. (2025). Finds LLMs emit representations *close to English* for semantically-loaded words before translating into the target language; **activation steering is more effective when computed in English** than in the input/output language. Tested on French, German, Dutch, Mandarin. Implication: non-English prompts go through an English-pivot, so "the model's decision in Vietnamese" is partly the English decision, re-skinned. arXiv: https://arxiv.org/abs/2502.15603
- **Language Matters: How Do Multilingual Input and Reasoning Paths Affect Large Reasoning Models?** — Tam et al. (2025). LRMs default to reasoning in high-resource languages (English) regardless of input language. **Forcing the model to reason in the input language *lowers* accuracy, especially for low-resource languages**, while reasoning in English preserves it. Crucially: input-language reasoning *hurts reasoning tasks but helps cultural tasks*, and safety behavior is language-specific. Directly relevant to whether you let the model "think in VN" or "think in EN, answer in VN." arXiv: https://arxiv.org/abs/2505.17407
- **Cross-lingual Collapse: How Language-Centric Foundation Models Shape Reasoning** (2025). The latent space is biased toward English; less-resourced languages form shallow, isolated clusters rather than mapping to a shared concept space. arXiv: https://arxiv.org/abs/2506.05850
- **The Reasoning Lingua Franca: A Double-Edged Sword for Multilingual AI** (2025). The reasoning-vs-language-consistency trade-off varies sharply by language, script, and prompt type; **enforcing language consistency degrades performance**. arXiv: https://arxiv.org/abs/2510.20647

### 1.2 Reasoning quality and accuracy gaps in non-English

- **Prompting language influences diagnostic reasoning and accuracy** — Bazoge et al. (2026), Nature-family. 180 clinical vignettes, EN vs FR, five LLMs (o3, DeepSeek-R1, GPT-4-Turbo, Llama-3.1-405B, BioMistral-7B). **4 of 5 models performed better in English** (mean diff 0.37-0.91 on an 18-pt scale, adj. p<0.05), gap spanning differential diagnosis, logical structure, internal validity. Only o3 showed no language effect. Even between two high-resource languages (EN vs FR), reasoning quality drops — expect a *larger* EN-vs-VN gap. arXiv: https://arxiv.org/abs/2605.19173
- **Beyond English: Prompt Translation Strategies across Languages and Tasks** (2025). How you translate the prompt (translate-test, native, English-instructions-with-native-content) changes outcomes per task/language. arXiv: https://arxiv.org/html/2502.09331v1
- **Cross-lingual Prompting (CLP/CLSP): Improving Zero-shot CoT Reasoning across Languages** (Qin et al., 2023). Explicit cross-lingual alignment + ensembling of reasoning paths improves non-English CoT — a usable mitigation if VN reasoning is weak. arXiv: https://arxiv.org/abs/2310.14799

**Takeaway for the project:** Decisions and their *justifications* will not be invariant across EN and VN. Some divergence is genuine "value/cultural" signal; some is just degraded VN reasoning. Section 6 separates these.

---

## 2. Cultural / value / risk-attitude shifts induced by prompt language

### 2.1 Moral values depend on prompt language

- **Ethical Reasoning and Moral Value Alignment of LLMs Depend on the Language we Prompt them in** — Agarwal, Tanmay, Khandelwal, Choudhury (LREC-COLING 2024). GPT-4, ChatGPT, Llama2-70B-Chat across English, Spanish, Russian, Chinese, Hindi, Swahili, probing deontology/virtue/consequentialism. **GPT-4 most consistent; ChatGPT and Llama2-70B show significant moral-value bias outside English**, and the *direction* of bias varies by language (even for GPT-4). This is the canonical "language changes the morality" result. arXiv: https://arxiv.org/abs/2404.18460 · ACL: https://aclanthology.org/2024.lrec-main.560/
- **Do Moral Judgment and Reasoning Capability of LLMs Change with Language?** (Defining Issues Test) — Khandelwal et al. (2024). Post-conventional moral-reasoning score is **substantially worse in Hindi and Swahili** than in Spanish/Russian/Chinese/English; moral *judgments* vary by language. Mid/low-resource languages (a class Vietnamese belongs to) reason less maturely. arXiv: https://arxiv.org/abs/2402.02135
- **One Model, Many Morals: Cross-Linguistic Misalignments in Computational Moral Reasoning** (2025). Documents systematic cross-lingual misalignment in moral reasoning. arXiv: https://arxiv.org/abs/2509.21443
- **Untangling Input Language from Reasoning Language: A Diagnostic Framework for Cross-Lingual Moral Alignment** (2026). Separates the effect of *input* language from *reasoning* language on moral alignment — methodologically a template for your EN-think vs VN-think ablation. arXiv: https://arxiv.org/abs/2601.10257
- **Speaking Multiple Languages Affects the Moral Bias of Language Models** — Hämmerl et al. (2023). Multilingual models encode *differing* moral biases across German/Czech/Arabic/Chinese/English, but these **do not cleanly track human cultural differences** — a warning against naive "language = culture" interpretation. arXiv: https://arxiv.org/abs/2211.07733
- **Reasoning or Rhetoric? / "moral ventriloquism"** (2026). LLMs overwhelmingly produce post-conventional-sounding justifications regardless of model/prompt, and some show **moral decoupling** (stated justification inconsistent with chosen action). Relevant: do not trust VN/EN justifications at face value; measure the *action*, audit the reasoning separately. arXiv: https://arxiv.org/abs/2603.21854

### 2.2 Cultural values: language moves them, but not toward the "right" culture

- **LLMs and Cultural Values: the Impact of Prompt Language and Explicit Cultural Framing** — Kharchenko et al. (2025). 10 LLMs (Claude, GPT-3.5/4/4o, Gemini, Llama, Mistral, Qwen, DeepSeek) × 11 languages, Hofstede VSM + World Values Survey (63 items). Key results: **prompt language alone produces variation but does NOT bring values closer to actual speakers' values**; **explicit cultural framing improves alignment more than language**; all models stay anchored to **NL/DE/US/JP defaults** regardless of prompt. "Responsive enough to vary, too anchored to represent diversity." This is the single most important caution for interpreting EN-vs-VN value differences. arXiv: https://arxiv.org/abs/2511.03980
- **MENAValues** — Zahraei & Asgari (2025). Crosses 3 perspective framings × 2 language modes (English vs native Arabic/Persian/Turkish). Names three phenomena you will likely see in VN: **(1) Cross-Lingual Value Shifts** (identical question, drastically different answer by language); **(2) Reasoning-Induced Degradation** (asking for reasoning *worsens* cultural alignment — note: opposite sign to reasoning helping accuracy); **(3) Logit Leakage** (model refuses but internal probabilities reveal hidden preferences). Also: models **collapse diverse nations into monolithic categories** when run in native language. arXiv: https://arxiv.org/abs/2510.13154
- **Whose Morality Do They Speak? Unraveling Cultural Bias in Multilingual Language Models** — (2024/2025). MFQ in 8 languages across GPT-3.5-Turbo, GPT-4o-mini, Llama 3.1, Mistral-NeMo: significant cultural/linguistic variability, challenging "universal moral consistency." arXiv: https://arxiv.org/abs/2412.18863 · ScienceDirect: https://www.sciencedirect.com/science/article/pii/S2949719125000482
- **LLM-GLOBE** — Karinshak et al. (2024). GLOBE framework; **US models pick individual reward, Chinese models (GLM-4, Qwen, Ernie) pick group reward** on institutional-collectivism items; GPT-4 leans individualist, Qwen-7B leans collectivist. Suggests *model provenance* interacts with prompt language on collectivism — relevant since you use Qwen. arXiv: https://arxiv.org/abs/2411.06032
- **Politeness across languages** — Yin et al. (2024). Optimal prompt politeness differs by language (EN/ZH/JA); impolite prompts hurt, over-polite doesn't help. A reminder that *register/wording within a language* is itself a hidden variable to control in translation. arXiv: https://arxiv.org/abs/2402.14531

### 2.3 Risk attitude and prospect-theory behavior

- **Can Large Language Models Capture Human Risk Preferences? A Cross-Cultural Study** — (2025). Lottery/stated-preference data from Sydney, Dhaka, Hong Kong, Nanjing; ChatGPT-4o & o1-mini under CRRA. Both models **more risk-averse than humans**; **predictions in Chinese deviate more from actual responses than in English** — i.e., prompt language degrades risk-preference simulation for the non-English language. arXiv: https://arxiv.org/abs/2506.23107
- **Evaluating and Aligning Human Economic Risk Preferences in LLMs** (2025). LLMs systematically risk-averse vs humans; methods to align. arXiv: https://arxiv.org/abs/2503.06646
- **Rethinking Prospect Theory for LLMs** (2026). PT fit is *not consistently reliable* across models and **not robust to epistemic markers** ("likely," "probably") injected into prompts — and such markers translate non-trivially into VN, a translation-control concern. arXiv: https://arxiv.org/abs/2508.08992
- **Probing Outcome-Level Resemblance vs Mechanism-Level Alignment (St. Petersburg game)** (2026). LLMs can look human-like in risk outcomes while using non-human *mechanisms*; controlled perturbations expose this. Lesson: measure mechanism (sensitivity to risk/threshold/endowment), not just the headline contribution number. arXiv: https://arxiv.org/abs/2606.04978
- **Quantifying Risk Propensities via DOSPERT/EDRAS + role-play** (Zeng, 2024). Adapts cognitive-science risk scales to LLMs; role-play (persona) shifts risk personality — interacts with language-as-implicit-persona. arXiv: https://arxiv.org/abs/2411.08884
- **Strategic behavior & framing vs structure** (Lorè & Heydari and follow-ups). Verbal/contextual *framing* can rival game structure in determining LLM behavior; LLMs show human-like framing effects in economic domains. Reinforces that EN-vs-VN wording is a framing manipulation. ResearchGate: https://www.researchgate.net/publication/382998710

**Takeaway:** Prompt language reliably *shifts* values and risk attitude, but the shift is (a) often not aligned to the target culture, (b) entangled with English-pivot reasoning, and (c) sometimes worsened by asking for explicit reasoning. Interpret EN-vs-VN value gaps as "model behavior under language X," not "what Vietnamese people believe."

---

## 3. Performance & reasoning gaps in non-English, especially small 7-8B open models

This is the regime of your study (Qwen / Llama / Gemma 7-8B). The literature is consistent: **small models degrade most and most erratically off-English.**

- **MuBench: Multilingual Capabilities across 61 Languages** (2025). Larger models have *relatively stable* multilingual performance; **smaller models show sharper per-language drops**. Among small models, **Gemma and Qwen are more balanced** across languages but still weaker in low-resource ones. arXiv: https://arxiv.org/abs/2506.19468
- **Multi-lingual Functional Evaluation for LLMs** (2025). Distinguishes *static* benchmarks (M-MMLU, Belebele) from *functional/reasoning* ones. Qwen3-8B shows small gaps on static high-resource benchmarks (M-MMLU 4.78%, Belebele 3.00%) but a **large gap on functional reasoning**. Implication: in a *reasoning-heavy* collective-risk game, expect EN-vs-VN gaps far bigger than knowledge benchmarks suggest. arXiv: https://arxiv.org/abs/2506.20793
- **Turning English-centric LLMs into Polyglots: How Much Multilinguality Is Needed?** (2023). Even small amounts of multilingual data shift behavior; base models are heavily English-anchored. arXiv: https://arxiv.org/abs/2312.12683
- **LinguaMap: Which Layers of LLMs Speak Your Language** (2026). Localizes where language-specific processing happens — useful if you want a mechanistic ablation rather than only behavioral. arXiv: https://arxiv.org/abs/2601.20009
- **Corrupted by Reasoning: Reasoning Language Models Become Free-Riders in Public Goods Games** (2025). **Directly relevant**: turning on reasoning makes models *free-ride more* in public-goods (threshold-collective) settings. Since reasoning quality differs by language, the reasoning-vs-cooperation interaction will differ EN vs VN. arXiv: https://arxiv.org/abs/2506.23276
- **More Capable, Less Cooperative? When LLMs Fail at Zero-Cost Collaboration** (2026). Capability does not imply cooperation — a confound when comparing a model that is "more capable in EN" vs "less capable in VN." arXiv: https://arxiv.org/abs/2604.07821

### Vietnamese-specific resources (mid-resource baseline calibration)

- **Crossing Linguistic Horizons: Finetuning and Comprehensive Evaluation of Vietnamese LLMs** — Truong et al. (2024). Open LLMs are *limited* in Vietnamese; 10 tasks / 31 metrics; **more parameters can introduce more bias and miscalibration**; data quality dominates. Use this to set realistic VN-capability expectations for 7-8B models. arXiv: https://arxiv.org/abs/2403.02715
- **ViLLM-Eval** (2024). Vietnamese eval suite (MCQA + next-word); even best models have substantial room. arXiv: https://arxiv.org/abs/2404.11086
- **Symbol Binding Ability for MCQ in Vietnamese General Education** (2023). Vietnamese MCSB across BLOOMZ-7.1B, LLaMA-2-7B/70B, GPT-3/3.5/4. Baseline for VN answer-format reliability of small models. arXiv: https://arxiv.org/abs/2310.12059
- **Sailor 7B/14B** (SEA-LION family, Qwen1.5-based, finetuned on SEA incl. Vietnamese) — a candidate VN-strengthened open model to include as a robustness arm. (Discussed in cultural-values surveys above.)

**Takeaway:** With 7-8B models, a fraction of any EN-vs-VN behavioral gap is *capability*, not values. Include a **VN-competence floor check** (Section 6.5) so you can attribute differences correctly.

---

## 4. Work where language changed cooperation, fairness, or risk behavior

This section is the closest prior art to a collective-risk EN-vs-VN study.

### 4.1 FAIRGAME — the most directly relevant prior work (and your codebase)

- **FAIRGAME: a Framework for AI Agents Bias Recognition using Game Theory** (Mensfelt, Stathis, Trencsenyi et al., 2025). Modular framework that simulates repeated games to **quantify cooperation/competition/bias induced by prompt language and personality**. arXiv: https://arxiv.org/abs/2504.14325 · HTML: https://arxiv.org/html/2504.14325
  - **Games:** Prisoner's Dilemma (harsh/conventional/mild payoff variants) and Battle of the Sexes. (Your local repo extends the template/config set to Stag Hunt, Snowdrift, Harmony.)
  - **Models:** Llama 3.1 405B, Mistral Large, GPT-4o, Claude 3.5 Sonnet.
  - **Languages:** English, French, Arabic, Vietnamese, Mandarin Chinese.
  - **Findings on language:**
    - **English yields more consistent cooperation** (lower penalties) for GPT-4o and Claude 3.5, especially when number of rounds is unknown — consistent with English being the primary training/alignment language.
    - **Mandarin and Vietnamese keep penalties high (less cooperative), especially for Mistral Large.**
    - **French / Arabic show broad variability and high penalties**, attributed to linguistic/cultural interpretation difficulty.
    - **Language can shift baseline cooperation as much as switching model architecture.**
  - **Translation method (the template they used, and your starting point):** template authored in English, machine-translated to each target language, then **manually edited/verified by a native speaker** for accuracy and cultural appropriateness.
- **Strategic Communication and Language Bias in Multi-Agent LLM Coordination** (2025). With GPT-4o and Llama 4 Maverick: communication shifts behavior, but **its effect varies by language, personality, and game**. Reports nuanced VN behavior — e.g., **Vietnamese prompts eliciting the highest frequency of *unconditional* cooperation (AllC)** in some conditions, consistent with retrieval of collectivist/community norms; while in early rounds cooperation starts at ~40-60% across conditions, **Vietnamese trajectories can collapse faster**. Note the *contradiction* with FAIRGAME's "VN less cooperative" — i.e., **VN effects are model- and condition-dependent (high variance), not a fixed sign.** arXiv: https://arxiv.org/abs/2508.00032 · Springer: https://link.springer.com/chapter/10.1007/978-981-95-4963-4_24
- **Understanding LLM Agent Behaviours via Game Theory: Strategy Recognition, Biases and Multi-Agent Dynamics** (2025). Catalogues strategy archetypes and language/personality biases across repeated games — useful taxonomy for coding your VN/EN behaviors (AllC, AllD, WSLS, TFT). arXiv: https://arxiv.org/abs/2512.07462

### 4.2 Cooperation / fairness / social dilemmas in LLMs (language-relevant)

- **Playing repeated games with LLMs** — Akata et al. (2023). Foundational behavioral-game-theory baseline; GPT-4 cooperates well in self-interest-aligned games (iterated PD) but is **unforgiving** (defects permanently after one defection) and bad at coordination (Battle of Sexes). Establishes the behavioral signatures language will perturb. arXiv: https://arxiv.org/abs/2305.16867
- **Will Systems of LLM Agents Cooperate: An Investigation into a Social Dilemma** (2025). Different LLMs have distinct cooperative/aggressive biases; populations can converge to poor equilibria. arXiv: https://arxiv.org/abs/2501.16173
- **When Ethics and Payoffs Diverge: LLM Agents in Morally Charged Social Dilemmas (MoralSim)** (2025). PD + public-goods where norms vs incentives conflict — design pattern for embedding moral framing in a collective-risk game. arXiv: https://arxiv.org/abs/2505.19212
- **Everyone Contributes! Incentivizing Strategic Cooperation via Sequential Public Goods Games** (2025). Public-goods / threshold-collective mechanics in multi-LLM systems. arXiv: https://arxiv.org/abs/2508.02076
- **Pro-social bias / fairness reasoning** (from the game-theory survey, 2502.09053): LLMs frequently over-prioritize fairness and cooperation over game-theoretic rationality; CoT reveals fairness reasoning is central. The *strength* of this pro-social prior plausibly differs EN vs VN. arXiv: https://arxiv.org/abs/2502.09053

### 4.3 The collective-risk dilemma itself (human baseline — your `papers/` folder)

The collective-risk game is a **threshold public-goods game**: a group must reach a common target to avoid a probabilistic collective loss; each member is tempted to free-ride. Your repo already contains the canonical human-experiment literature:

- **Milinski et al. (2008)** — *The collective-risk social dilemma and the prevention of simulated dangerous climate change*, PNAS. Under **high risk**, ~half of groups reach the target; under low risk most fail. Establishes **risk probability as the key lever** you can translate/manipulate. PNAS: https://www.pnas.org/doi/10.1073/pnas.0709546105
- **Santos & Pacheco (2011)** — *Risk of collective failure provides an escape from the tragedy of the commons*, PNAS. Evolutionary-dynamics treatment; risk perception drives cooperation. PNAS: https://www.pnas.org/doi/10.1073/pnas.1015648108
- **Van Segbroeck et al. (PRL 108, 158104)** — strategy evolution in the collective-risk dilemma (in `papers/`).
- Related: **Co-evolution of risk and cooperation under wealth inequality**, PNAS Nexus (2024): https://academic.oup.com/pnasnexus/article/3/12/pgae550/7919236

**Research gap this project fills:** There is rich human CRD literature and rich LLM-game literature, but **almost no work running LLM agents in a *collective-risk* (threshold-PGG) dilemma**, and **none isolating EN-vs-VN prompt language with small open models**. FAIRGAME covers PD/BoS in VN/EN but not the collective-risk/threshold structure where *risk perception* is the central variable — which is exactly where prompt language might bend risk attitude and cooperation.

---

## 5. Cross-cutting confounds you must control

| Confound | Why it threatens an EN-vs-VN claim | Mitigation (see §6) |
|---|---|---|
| **English-pivot reasoning** | "VN values" may be EN values translated | EN-think vs VN-think ablation; report reasoning language |
| **Translation quality / drift** | Payoff or risk wording subtly changes meaning | Back-translation + semantic similarity + native review |
| **Tokenization / length** | VN diacritics & word segmentation change token counts, costs, truncation | Match max tokens; log token counts; check truncation |
| **Register/politeness** | Politeness shifts performance differently per language (Yin 2024) | Fix register; native review for tone parity |
| **Numeral/format parsing** | VN number/percent formatting, answer-symbol binding weaker in small models | Constrain output schema; parse robustly; VN format checks |
| **Reasoning-induced degradation** | Asking for rationale can *worsen* cultural alignment (MENAValues) yet *improve* accuracy | Run with and without elicited reasoning; treat as a factor |
| **Capability vs values** | 7-8B VN weakness mimics a "value" difference | VN-competence floor check (comprehension probe) |
| **Decoding stochasticity** | Temperature/seed noise swamps small effects | Fix seeds; many repetitions; report CIs |
| **Logit leakage / refusals** | Model refuses in one language but not other | Track refusal rate by language; inspect logits if available |

---

## 6. Methodology: designing a clean EN-vs-VN collective-risk-game comparison with small open models

Goal: attribute any behavioral difference to **prompt language**, not to translation noise, capability, or decoding randomness. The design below is FAIRGAME-compatible.

### 6.1 Hold everything constant except language (the core principle)

Single manipulated factor = **prompt language ∈ {EN, VN}**. Everything else identical across the two arms:
- **Game structure & payoffs:** identical threshold/target, endowment, risk probability, rounds, group size. Use *numerals not number-words* where possible so payoffs survive translation literally.
- **Model & decoding:** same checkpoint, same `temperature`, `top_p`, `max_tokens`, **same random seed schedule**, same system prompt structure, same tool/format scaffolding.
- **Personality/persona:** if used (FAIRGAME supports it), keep the persona constant across languages; persona is a separate factor, not a confounder.
- **Prompt skeleton:** identical ordering of instructions, identical placeholders (`{endowment}`, `{target}`, `{risk}`), identical output schema.

### 6.2 Translation pipeline with back-translation QC

Adopt the **LLM + human-expert in-the-loop, 3-stage** pipeline that is now standard in multilingual eval (see refs below):
1. **Forward translation EN→VN.** Either (a) professional/native translator, or (b) strong LLM (e.g., GPT-4o) at **low temperature for determinism**, with explicit instructions to *preserve meaning, tone, numerals, and structural placeholders* (do not translate `{...}` tokens, schema keys, or numbers).
2. **Native-speaker manual correction.** A Vietnamese native edits for fluency, register parity (match EN politeness), domain terms (risk, contribution, threshold), and cultural appropriateness. (This mirrors FAIRGAME's own template procedure.)
3. **Back-translation VN→EN** by an *independent* translator/model, then compare to the original EN.

**Quantitative QC gates (report these):**
- **Semantic equivalence:** multilingual sentence-encoder cosine similarity (LaBSE / multilingual-MPNeT) between original EN and back-translated EN; also EN↔VN cross-lingual similarity. Strip placeholder tokens before computing. Target median ≳ **0.90-0.95** (cf. reported macro-median ~0.955 in best-practice pipelines; Polish moral-corpus study reports mean cosine 0.86 with AUC gaps 0.01-0.02).
- **Back-translation surface metrics:** BLEU / chrF as a secondary signal (not primary — they penalize legitimate paraphrase).
- **Numeral & placeholder integrity:** automated check that every number, `{placeholder}`, and schema key appears identically in EN and VN. Regenerate on failure.
- **LLM-as-judge adequacy** (optional, with caution): a separate model rates EN/VN as semantically equivalent; treat as triangulation, not ground truth.

Refs for this protocol: *Moral Semantics Survive Machine Translation* (Skorski 2026, https://arxiv.org/abs/2605.22660); *Multi-Method Validation of LLM Medical Translation across High/Low-Resource Languages* (2026, https://arxiv.org/abs/2603.22642); *Towards Multilingual LLM Evaluation for European Languages* (2024, https://arxiv.org/abs/2410.08928); back-translation framework (https://arxiv.org/abs/2506.08174).

### 6.3 The English-pivot ablation (separating reasoning language from values)

Because models think in English (§1.1, §2.1), include a **2×2 (or 2×3) reasoning-language design** to decompose effects:

| Arm | Input/prompt language | Reasoning (CoT) language | Output language |
|---|---|---|---|
| A | EN | EN | EN |
| B | VN | VN | VN |
| C | VN | EN (forced "think in English") | VN |
| (D opt.) | EN | VN | EN |

- A vs B = total prompt-language effect (what a VN user experiences).
- B vs C = how much of the VN effect is *degraded VN reasoning* vs *genuine VN-language priors* (cf. Tam et al.; Untangling Input from Reasoning Language, 2601.10257).
- Log the *actual* reasoning language the model used (it may ignore instructions and revert to English).

### 6.4 Outcome measures (action + mechanism, not just headline)

Measure both *what* the agent does and *how it responds to incentives* (cf. St. Petersburg mechanism paper):
- **Contribution / cooperation rate** per round; **threshold-reaching rate** (group success); time-to-collapse.
- **Risk sensitivity:** sweep the collective-risk probability (e.g., low/med/high, as in Milinski) and measure the *slope* of contribution vs risk — separately in EN and VN. A pure values claim should survive controlling for this slope.
- **Strategy classification:** AllC / AllD / TFT / WSLS / GRIM (use the FAIRGAME / 2512.07462 taxonomy).
- **Fairness:** dispersion of contributions; responses to free-riders.
- **Reasoning audit:** code the elicited rationale for fairness/risk/self-interest/collectivist appeals; check **moral decoupling** (stated rationale vs action mismatch).
- **Refusal & format-failure rate** per language (logit leakage / parsing).

### 6.5 Validity & robustness checks (do these or reviewers will ask)

- **VN-competence floor check.** Before the game, give each model a short VN comprehension probe on the *exact* game rules (e.g., "what is the target?", "what happens if the group misses it?"). If a model can't restate the rules in VN, its VN game behavior reflects misunderstanding, not values. Report per-model VN comprehension.
- **Repetitions & statistics.** Many seeds per condition (small effects + small-model noise). Report mean ± CI; use mixed-effects models with random effects for seed and (if agents interact) opponent. Pre-register the primary contrast (A vs B) and effect-size threshold.
- **Model panel.** Run ≥3 small open models — **Qwen2.5-7B, Llama-3.1-8B, Gemma-2-9B** — plus optionally a VN-strengthened arm (**Sailor / SEA-LION**) to test whether VN-finetuning closes the gap. Per-model effects matter: §4 shows VN can be *more* or *less* cooperative depending on model, so **do not pool across models without checking the interaction.**
- **Translation-robustness arm.** Produce *two* independent VN translations (different translator/model) and confirm the EN-vs-VN effect replicates across both — this rules out "one translation happened to be loaded."
- **Order/format controls.** Counterbalance option ordering; fix answer schema; test that results survive an alternate but equivalent VN phrasing (paraphrase robustness).
- **Decoding sweep.** Confirm the direction of the EN-vs-VN effect holds at ≥2 temperatures.

### 6.6 Pre-registration-style hypotheses (suggested)

- **H1 (consistency):** EN and VN produce significantly different contribution/cooperation rates in the collective-risk game (directional sign TBD — literature is mixed for VN).
- **H2 (risk slope):** The sensitivity of contribution to collective-risk probability differs EN vs VN.
- **H3 (capability share):** Part of any EN-vs-VN gap is explained by VN reasoning degradation (B vs C narrows the gap).
- **H4 (model interaction):** The sign/size of the VN effect depends on the model (Qwen vs Llama vs Gemma).
- **H5 (framing > language):** Explicit cultural framing moves behavior more than language alone (testable add-on, per Kharchenko 2511.03980).

---

## 7. Annotated source list (grouped, with links)

### Cross-lingual reasoning / English-pivot
- Do Multilingual LLMs Think in English? — https://arxiv.org/abs/2502.15603
- Language Matters: Multilingual Input & Reasoning Paths (Tam et al.) — https://arxiv.org/abs/2505.17407
- Cross-lingual Collapse — https://arxiv.org/abs/2506.05850
- The Reasoning Lingua Franca — https://arxiv.org/abs/2510.20647
- Beyond English: Prompt Translation Strategies — https://arxiv.org/html/2502.09331v1
- Cross-lingual Prompting (CLP/CLSP) — https://arxiv.org/abs/2310.14799
- Prompting language influences diagnostic reasoning (EN vs FR) — https://arxiv.org/abs/2605.19173
- LinguaMap (layer localization) — https://arxiv.org/abs/2601.20009

### Moral reasoning & values by language
- Ethical Reasoning Depends on the Language we Prompt them in — https://arxiv.org/abs/2404.18460 · https://aclanthology.org/2024.lrec-main.560/
- Do Moral Judgment/Reasoning Change with Language? (DIT) — https://arxiv.org/abs/2402.02135
- One Model, Many Morals — https://arxiv.org/abs/2509.21443
- Untangling Input Language from Reasoning Language (moral) — https://arxiv.org/abs/2601.10257
- Speaking Multiple Languages Affects Moral Bias — https://arxiv.org/abs/2211.07733
- Reasoning or Rhetoric? (moral ventriloquism) — https://arxiv.org/abs/2603.21854
- UniMoral (multilingual moral pipeline) — https://arxiv.org/abs/2502.14083

### Cultural values & cross-lingual value shift
- LLMs and Cultural Values: Prompt Language & Cultural Framing (Kharchenko et al.) — https://arxiv.org/abs/2511.03980
- MENAValues (cross-lingual value shift, reasoning degradation, logit leakage) — https://arxiv.org/abs/2510.13154
- Whose Morality Do They Speak? — https://arxiv.org/abs/2412.18863 · https://www.sciencedirect.com/science/article/pii/S2949719125000482
- LLM-GLOBE (collectivism; Qwen vs US models) — https://arxiv.org/abs/2411.06032
- Politeness across languages — https://arxiv.org/abs/2402.14531

### Risk attitude & economic decision-making
- Can LLMs Capture Human Risk Preferences? Cross-Cultural (EN vs Chinese deviation) — https://arxiv.org/abs/2506.23107
- Evaluating & Aligning Human Economic Risk Preferences — https://arxiv.org/abs/2503.06646
- Rethinking Prospect Theory for LLMs (epistemic markers) — https://arxiv.org/abs/2508.08992
- St. Petersburg game: outcome vs mechanism — https://arxiv.org/abs/2606.04978
- Risk Propensities via DOSPERT/EDRAS + role-play — https://arxiv.org/abs/2411.08884

### Game theory / cooperation / fairness (language-relevant)
- FAIRGAME (PD/BoS, EN/FR/AR/VN/ZH; language ≈ architecture effect) — https://arxiv.org/abs/2504.14325 · https://arxiv.org/html/2504.14325
- Strategic Communication & Language Bias in Multi-Agent Coordination (VN AllC; GPT-4o, Llama 4) — https://arxiv.org/abs/2508.00032
- Understanding LLM Agent Behaviours via Game Theory (strategy taxonomy, biases) — https://arxiv.org/abs/2512.07462
- Playing repeated games with LLMs (Akata et al.) — https://arxiv.org/abs/2305.16867
- Game Theory Meets LLMs: Systematic Survey — https://arxiv.org/abs/2502.09053
- Corrupted by Reasoning: reasoning models free-ride in public-goods — https://arxiv.org/abs/2506.23276
- Will Systems of LLM Agents Cooperate (social dilemma) — https://arxiv.org/abs/2501.16173
- When Ethics and Payoffs Diverge (MoralSim) — https://arxiv.org/abs/2505.19212
- Everyone Contributes! Sequential Public Goods — https://arxiv.org/abs/2508.02076
- More Capable, Less Cooperative? — https://arxiv.org/abs/2604.07821
- GLEE: language-based economic environments benchmark — https://arxiv.org/abs/2410.05254
- Can LLMs Serve as Rational Players in Game Theory? — https://arxiv.org/abs/2312.05488

### Small open models / multilingual performance gaps
- MuBench (61 languages; small-model drops; Gemma/Qwen balanced) — https://arxiv.org/abs/2506.19468
- Multi-lingual Functional Evaluation (Qwen3-8B static vs functional gaps) — https://arxiv.org/abs/2506.20793
- Turning English-centric LLMs into Polyglots — https://arxiv.org/abs/2312.12683

### Vietnamese-specific
- Crossing Linguistic Horizons: Finetuning & Eval of Vietnamese LLMs — https://arxiv.org/abs/2403.02715
- ViLLM-Eval — https://arxiv.org/abs/2404.11086
- Symbol Binding for MCQ in Vietnamese General Education — https://arxiv.org/abs/2310.12059

### Translation QC / methodology
- Moral Semantics Survive Machine Translation (LaBSE/CKA/judge/classifier-parity; cosine 0.86) — https://arxiv.org/abs/2605.22660
- Multi-Method Validation of LLM Medical Translation (high/low-resource) — https://arxiv.org/abs/2603.22642
- Towards Multilingual LLM Evaluation for European Languages — https://arxiv.org/abs/2410.08928
- Back-translation as terminology/standardization framework — https://arxiv.org/abs/2506.08174

### Collective-risk dilemma (human baseline; in repo `papers/`)
- Milinski et al. 2008, PNAS — https://www.pnas.org/doi/10.1073/pnas.0709546105
- Santos & Pacheco 2011, PNAS — https://www.pnas.org/doi/10.1073/pnas.1015648108
- Co-evolution of risk and cooperation under wealth inequality, PNAS Nexus 2024 — https://academic.oup.com/pnasnexus/article/3/12/pgae550/7919236

---

## 8. One-paragraph synthesis for the paper's Related Work

> Prompt language is now established as a substantive driver of LLM behavior rather than a surface variable. Models reason in an English-centric latent space and translate outward, so non-English prompts incur reasoning degradation that is largest for small (7-8B) open models and for mid/low-resource languages such as Vietnamese (Wendler/Zhong 2025; Tam et al. 2025; MuBench 2025). Independently, prompt language shifts expressed moral values, cultural orientations, and risk attitudes — but typically *not* toward the genuine values of that language's speakers, and sometimes in directions that *reverse* under reasoning elicitation (Agarwal et al. 2024; Kharchenko et al. 2025; MENAValues 2025; risk-preference cross-cultural 2025). In strategic settings, prompt language can change cooperation as much as changing the model: FAIRGAME (Mensfelt et al. 2025) shows English eliciting more consistent cooperation and Vietnamese/Mandarin more defection in PD/BoS, while a parallel multi-agent study finds Vietnamese sometimes eliciting the *highest* unconditional cooperation — i.e., the Vietnamese effect is model- and condition-dependent. No prior work isolates English-vs-Vietnamese prompt language in a *collective-risk (threshold public-goods)* dilemma with small open models, where risk perception is the central lever; this project fills that gap, with a translation-QC and English-pivot-ablation design that separates genuine language-induced behavioral shifts from translation noise and capability deficits.
