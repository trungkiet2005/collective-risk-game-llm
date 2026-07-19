# Milinski et al. (2008) — The Collective-Risk Social Dilemma and the Prevention of Simulated Dangerous Climate Change

> AI-readable summary for faithful experimental replication. All numbers below are taken directly from the primary source (PNAS full text) unless explicitly flagged.

## Citation

Milinski M, Sommerfeld RD, Krambeck H-J, Reed FA, Marotzke J (2008). "The collective-risk social dilemma and the prevention of simulated dangerous climate change." *Proceedings of the National Academy of Sciences (PNAS)* 105(7): 2291–2294. DOI: [10.1073/pnas.0709546105](https://doi.org/10.1073/pnas.0709546105). PMID: 18287081. Received 8 October 2007; approved 18 December 2007 (editor: Robert May); published 19 February 2008. Freely available (PNAS open access).

Affiliations: Max Planck Institute for Evolutionary Biology (Plön), University of Maryland, Max Planck Institute for Meteorology (Hamburg). Experiment run at the University of Cologne and the University of Bonn (Germany).

---

## 1. One-paragraph summary

The paper introduces and experimentally tests the "collective-risk social dilemma": a group must reach a fixed monetary target through repeated voluntary contributions, and every member risks losing all their privately retained money (with a stated probability) if the group fails to reach the target. This is framed as an analogue for preventing dangerous climate change (invest now to avoid a future collective loss). The central manipulation is the probability of loss-on-failure (90%, 50%, 10%). Main result: only under high risk (90%) did half the groups reach the target; at 50% and 10% groups generally failed. The policy takeaway is that voluntary cooperation to avert climate change requires people to be convinced that failure to invest enough is very likely to cause grave individual loss.

---

## 2. Exact experimental setup

| Parameter | Value |
|---|---|
| Group size | **6 subjects per group** |
| Endowment per player | **€40 each** (initial private endowment) |
| Number of rounds | **10 rounds** (called "climate rounds") |
| Contribution options per player per round | **€0, €2, or €4** (three discrete choices only) into a "climate account" |
| Collective target sum | **€120 per group**, to be reached at the end of 10 rounds (cumulative across all 6 players × 10 rounds) |
| Fair-share benchmark | €120 / (6 players × 10 rounds) = **€2 per person per round on average** |
| Investments are lost | Yes — **no refunds**; money put into the climate account is never returned regardless of outcome |
| Max a player could possibly contribute | €4 × 10 = €40 (i.e., the entire endowment) |

**If the target IS reached** (total group contributions ≥ €120 after 10 rounds): all group members keep, in cash, whatever they did *not* invest. Example from the paper: a player who invested €2 per round (€20 total) receives the remaining €20. Players who exactly reach the target collected, on average, €20 per player (i.e., they had on average invested their fair share).

**If the target is NOT reached** (total < €120): the computer "throws dice." With the treatment-specific loss probability, **all group members lose all their remaining (private) savings**. With the complementary probability they keep their remaining savings. (The money already invested in the climate account is gone in either case — no refunds.)

> Note: A group can also *overshoot* €120. Overshooting is wasteful — the paper notes the optimal strategy in the 90% treatment is to reach *exactly* €120, with each player investing less than €36 (see Nash equilibrium below). Exceeding the target lowers expected earnings.

---

## 3. Risk treatments (the core manipulation)

Three between-groups treatments, each with **10 groups of 6** (so 60 participants per treatment). They differ only in the probability that all members lose their remaining savings when the group fails to reach €120:

| Treatment | Loss probability if target missed | Groups |
|---|---|---|
| High risk | **90%** | 10 |
| Medium risk | **50%** | 10 |
| Low risk | **10%** | 10 |

### Payoff structure — Table 1 of the paper (expected end-of-game account value, € per player, under three *pure* strategies where every player uses the same strategy the whole game)

| Loss probability | Free rider (invests €0/round) | Fair sharer (invests €2/round) | Altruist (invests €4/round) |
|---|---|---|---|
| **90%** | **€4** | **€20** | **€0** |
| **50%** | **€20** | **€20** | **€0** |
| **10%** | **€36** | **€20** | **€0** |

How these are derived:
- **Fair sharer** keeps €20 regardless of risk: 6 players × €2 × 10 rounds = €120 reaches the target, so everyone keeps the uninvested €20 with certainty.
- **Altruist** invests all €40 (€4 × 10), keeping €0 in every condition.
- **Free rider** invests €0, keeps €40, but the group fails (if everyone free-rides, total = €0 < €120), so the €40 is exposed to the loss lottery:
  - 90% loss → keeps €40 only 1 time in 10 → expected €4.
  - 50% loss → keeps €40 half the time → expected €20.
  - 10% loss → keeps €40 9 times in 10 → expected €36.

**Incentive interpretation (key to the design):**
- At **90%**: the rational/optimal individual strategy is to invest the fair share (€2/round); free-riding yields only €4 expected. Reaching the target is favored.
- At **50%**: free-riding (€20 expected) and fair-sharing (€20 expected) give *identical* expected earnings — indifference point. The loss probability equals the necessary average investment proportion.
- At **10%**: free-riding is the rational strategy (€36 > €20). The dilemma is "switched off" in favor of defection.

### Nash equilibrium (90% treatment)
Any course of play that exactly reaches €120 — regardless of who contributes how much, *as long as each player invests less than €36* — is a Nash equilibrium: no single player can gain by deviating. Once one player irrationally switches (either jeopardizing the target or pushing past it), the others' best responses also shift — either "cut losses" and free-ride, or "maintain investment" and become more altruistic (a snowdrift-game scenario: cooperate when you expect your partner to defect). A formal description is in the paper's SI Appendix (not reproduced here).

---

## 4. Mechanic, information, and communication

- **Game family:** a public goods game (cf. Ledyard 1995) modified into a *threshold* public goods game with a *collective-risk* twist — the public good is "avoiding a loss" rather than "realizing a gain," so strategies are expected to be risk-averse. Distinguishing features the authors list: (i) repeated decisions before the outcome is evident; (ii) investments are lost (no refunds); (iii) the effective value of the public good is unknown; (iv) the remaining private good is at stake with a probability if the target is missed.
- **Contribution timing:** Each round, all 6 players choose €0/€2/€4. **After each round, the six decisions were displayed on all computers simultaneously** — i.e., contributions are revealed per round (effectively simultaneous within a round, sequential across the 10 rounds).
- **Information shown each round:**
  - Every subject could see **how much each other subject contributed after each round**.
  - **Each subject's decisions appeared in the same fixed position every round**, so individual strategies (altruist / fair sharer / free rider / strategy-switcher) were trackable across rounds. Players were *not anonymous within the game* in this positional sense, but identities were never disclosed.
  - **The cumulative running total was NOT displayed on screen.** Subjects were given **pen and paper** and encouraged to take their own notes to track the cumulative sum.
- **Anonymity:** Subjects were anonymous as people (separated by opaque partitions; paid out in a way that did not reveal identity; could not build cross-context reputation). But within a single game their per-round choices were individually traceable via the fixed display position.
- **Communication:** No verbal/free communication. Subjects were separated by opaque partitions and interacted only through laptops to a main computer. The only "communication" was the per-round display of everyone's contributions.
- **"Little information" framing:** Subjects were told the pooled climate-account money (across all groups) would fund a real press advertisement on climate protection in a German newspaper, but were given the "little information" version (from Milinski et al. 2006, ref. 28) so that motivation to invest *for the advertisement's sake* was expected to be very weak. The dominant motivation was the monetary game itself.

---

## 5. Main empirical findings

### Target-reaching vs. risk probability (Fig. 1)
- **90% treatment: 5 of 10 groups** reached the target (€120). Significantly different from the rational prediction that *all* groups reach it (n = 10, P < 0.0001, binomial test).
- **50% treatment: only 1 of 10 groups** reached the target.
- **10% treatment: 0 of 10 groups** reached the target (as expected).
- Difference among treatments in failing to reach the target: P = 0.008, n = 30, df = 2,29, χ² = 9.66. (Difference among treatments for the **final amounts collected** is reported as **P = 0.0001**, n = 30, df = 2,29, F = 13.784 — see Fig. 2 result below.)

### Average final amount collected per group (Fig. 2)
- **90% treatment: €118.2 ± 1.9** (mean ± SE) — just barely failed *on average* to reach €120.
  - The five 90% groups that did *not* reach the target collected on average **€112.8 ± 1.2**. "Just failing" is the worst outcome: low savings AND no collective benefit.
- **50% treatment: €92.2 ± 9.0** — missed by far.
- **10% treatment: €73.0 ± 4.4** — missed by far, but still ~61% of target; notably the 10% groups did **not** rationally invest nothing (they collected >50% of the target despite free-riding being individually optimal), suggesting intrinsic/risk-averse motivation to cooperate.
- Overall difference among the three treatments for final amount collected: **P = 0.0001, n = 30, df = 2,29, F = 13.784**. (The paper reports this as the exact value "P = 0.0001," not "P < 0.0001.")

### Fair-sharers and free-riders (per group of 6)
- Number of subjects who provided **at least their fair share (≥ €2/round)**: **3.3 ± 1.3** (90%), **2.1 ± 0.6** (50%), **1.1 ± 0.3** (10%). (P = 0.003, n = 30, df = 2,29, F = 7.137.)
- The **extreme free rider** in each group contributed on average only **€1.4 ± 0.1/round (90%), €0.9 ± 0.2/round (50%), €0.5 ± 0.2/round (10%)**. (P = 0.0003, n = 30, df = 2,29, F = 11.137.)
- Some free riders invested nothing and **won their big savings in 8 of 10 groups** (i.e., in groups that failed, free riders still kept their €40 when the loss lottery did not trigger).

### Round dynamics: intermediate vs. final (Figs. 2 & 3)
- **Almost all groups started cooperatively:** in round 1 nearly everyone contributed €2 (an all-fair-sharer situation).
- In later rounds some players contributed €0; others noticed (confirmed by post-game questionnaire), and **motivation to contribute declined steadily** — especially in the 50% and 10% treatments, where many subjects cut investments after round 6.
- Strategy-act dynamics, first half (rounds 1–5) vs. second half (rounds 6–10), per group (Fig. 3), with paired t-tests:
  - **90% treatment:** selfish acts (€0) **decreased** (P = 0.023, z = 2.739), fair-share acts (€2) **decreased** (P = 0.038, z = 2.433), **altruistic acts (€4) strongly increased** (P = 0.0001, z = −6.325). (The paper reports the altruistic-acts P as the exact value "P = 0.0001," not "P < 0.0001.") Net effect: a slightly **U-shaped** cumulative curve that nearly reaches €120 by round 10 — players raised contributions late to try to save the collective outcome (short-term vs. long-term tension).
  - **50% treatment:** selfish acts **increased** (P = 0.011, z = −3.188), fair-share acts **strongly decreased** (P = 0.0006, z = 5.161), altruistic acts slightly increased (P = 0.035, z = −2.473). Altruists tried to compensate for free riders, usually in vain.
  - **10% treatment:** selfish acts **increased** from an already high level (P = 0.011, z = −3.196), fair-share acts decreased (P = 0.001, z = 4.776), altruistic acts stayed at a low constant level (P = 0.8, z = 0.259, not significant).

### Last-round / endgame effects
- In the 90% treatment, failure sometimes occurred in an **"extremely irrational" way in the last round**: it became clear that all prior contributions would be wasted unless many players made the maximal (€4) contribution, yet an insufficient number did so, and the group just missed the target.
- The authors attribute this partly to **fairness / reluctance to reward perceived-unfair behavior**: players would rather forfeit than bail out free riders, even at personal risk. This is the opposite of the standard "last-round defection" prediction — here some players *increased* contributions at the end (90% treatment), while others refused to compensate free riders.

### Inequality / fairness dynamics
- The design lets free riders force fair-sharers/altruists to over-contribute to save the group, generating within-group inequality.
- Perceived unfairness produced "irrational" (expected-value-lowering) choices — both refusing to over-contribute to save the group, and (in the low-risk groups) over-contributing relative to the rational defect strategy. The authors connect this to inequity-aversion / fairness preferences (Fehr & Schmidt 1999).

---

## 6. Sample sizes

- **Total participants: 180 undergraduates.**
- **30 groups of 6** subjects each.
- **10 groups per treatment** (90% / 50% / 10%) → 60 participants per treatment.
- Recruited at the **University of Cologne and University of Bonn**, Germany.
- Statistical n for treatment comparisons = 30 groups (df = 2,29).

---

## 7. Key conclusions and climate-policy relevance

The paper states three explicit conclusions:

1. **Convince people the risk is high and personal.** To achieve effective voluntary cooperation, people must be convinced of a *very high probability* that individuals will be personally harmed by dangerous climate change if the emissions-reduction target (cited as 50% of present level by 2050) is not met. If they believe the probability is low, climate protection may fail — as in the 50% and 10% treatments. (Encouragingly, even the 10% groups invested far more than the rational zero, so informing/motivating people is "worth the effort.")
2. **People are not reliably rational.** Programs that appeal to a human sense of fairness — everyone contributing a "fair share" — are more likely to avoid irrational, self-detrimental behavior.
3. **Scale makes it harder.** Even small (6-person) groups struggled to reach the target; the much larger global "game" will be harder still. Small-group settings such as G8/climate summits may have a better chance. Additional incentives beyond fear (e.g., social reputation, sanction institutions) are likely needed; otherwise free-riding fulfills Hardin's prediction that "freedom in the commons brings ruin to all."

Caveats the authors raise: real climate change does not hit everyone equally (the equal-loss assumption is a simplification, though dangerous change would affect everyone in a globalized world); the strict €120 cutoff is a simplification, though many climate elements genuinely have threshold properties; real summits are non-anonymous (and anonymity impedes cooperation, ref. 28), so the lab result may *underrate* real-world cooperation potential in summit settings while also underrating the difficulty at global scale.

---

## 8. Replication checklist

Everything needed to reimplement the game:

**Group / population**
- [ ] Group size = **6** players.
- [ ] **10 groups per treatment**, **3 treatments** → 30 groups, **180 participants** total (if matching the original power).
- [ ] Between-subjects assignment: each group experiences exactly one loss-probability treatment.

**Endowment & currency**
- [ ] Per-player initial private endowment = **€40**.
- [ ] Real-money incentive (or scaled equivalent); payouts made privately/anonymously.

**Rounds & actions**
- [ ] **10 rounds** per game.
- [ ] Each round, every player simultaneously chooses a contribution from **{€0, €2, €4}** into the shared "climate account."
- [ ] Contributions are **non-refundable** (sunk regardless of outcome).

**Target & success rule**
- [ ] Collective target = **€120** cumulative (sum over all 6 players × 10 rounds).
- [ ] Fair share = **€2/player/round** (€20/player total).
- [ ] Success condition: cumulative total **≥ €120** after round 10.

**Outcome resolution**
- [ ] If target reached: each player receives, in cash, **endowment minus own total contribution** (their retained private money), guaranteed.
- [ ] If target not reached: run a single loss lottery — with probability **p** *all* players lose their entire remaining private savings; with probability **1 − p** they keep it. (Already-contributed money is gone either way.)
- [ ] Loss probability **p ∈ {0.90, 0.50, 0.10}** by treatment.

**Information / interface**
- [ ] After each round, display **all six players' contributions** for that round, simultaneously, to everyone.
- [ ] Keep each player's choices in a **fixed display position** across rounds (so individual strategies are trackable), but never reveal real identities.
- [ ] **Do NOT display the running cumulative total** — provide pen and paper / require players to self-track.
- [ ] Players seated behind **opaque partitions**; **no communication** other than the per-round contribution display.
- [ ] (Optional framing) Tell players the pooled funds support a real climate cause, but use a low-salience ("little information") framing so it does not drive contributions.

**Measurements to record (for matching the analyses)**
- [ ] Per group: target reached (yes/no); final cumulative total.
- [ ] Per group: number of players contributing ≥ €2/round (fair-sharers); minimum mean contribution (extreme free rider).
- [ ] Per player per round: choice ∈ {€0, €2, €4} (for first-half vs second-half dynamics).
- [ ] Cumulative-sum-by-round trajectory per group.

---

## 9. Confidence / uncertainty flags

All structural numbers below are **verified directly from the PNAS full text** and carry high confidence: group size 6; endowment €40; 10 rounds; options €0/€2/€4; target €120; risk treatments 90/50/10%; Table 1 payoffs (4/20/0; 20/20/0; 36/20/0); 30 groups / 180 participants / 10 groups per treatment; success counts 5/1/0; final means €118.2/€92.2/€73.0; fair-sharer counts 3.3/2.1/1.1; extreme-free-rider means €1.4/€0.9/€0.5; the no-cumulative-display + pen-and-paper detail; opaque partitions / no communication; Cologne & Bonn.

**Note on P-value notation (verified against source):** The paper uses "P < 0.0001" *only* for the two binomial tests (each with n = 10) showing that the per-treatment failure rate differs from "all groups reach the target." For the two ANOVA-style across-treatment tests it reports the **exact value "P = 0.0001"**: (a) final amount collected, F = 13.784; and (b) altruistic acts increasing in the 90% treatment, z = −6.325. These are *not* "P < 0.0001." This is the one place where the original draft over-stated significance, now corrected.

Items to flag as **not fully specified in the main text** (would require the SI Appendix or assumptions for an exact reimplementation):
- The **precise wording of instructions** and the exact framing shown to subjects (only summarized; full text is in SI / ref. 28).
- The **exact monetary conversion / show-up fee** structure beyond the €40 endowment (the paper describes endowment and game payoffs; any additional participation fee is not detailed here).
- The **formal Nash-equilibrium / rational-decision derivations** for non-pure (mixed/heterogeneous) strategies live in the **SI Appendix**, which was not retrieved for this summary — the main-text Table 1 covers only the three *pure* strategies.
- Whether the loss lottery is one draw per group at the end (the text "the computer threw dice … all group members would lose all their savings") indicates a **single group-level draw** at game end; this is the natural reading and is treated as such above, but the literal mechanic (one shared draw vs. independent per-player draws) is best confirmed against the SI for a bit-exact replication. The shared-draw reading is consistent with "all group members would lose all their savings."

---

## 10. Sources

- Primary full text (PNAS open access, retrieved via NPR Planet Money mirror): https://media.npr.org/assets/blogs/planetmoney/pdfs/milinski%20paper.pdf
- PNAS landing page: https://www.pnas.org/doi/10.1073/pnas.0709546105
- PubMed record: https://pubmed.ncbi.nlm.nih.gov/18287081/
- PMC full text (open access, NIH): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2268129/ (PMCID: PMC2268129)

---

## Verification notes

Independent re-check performed by extracting the full text of the local PDF (`D:\tmp\milinski_npr.pdf`, 4 pages) and cross-checking publication metadata against PubMed (PMID 18287081). The decoded glyph mapping used to read the PDF's special characters: `/H11021` = "<", `/H11005` = "=", `/H11002` = "−", `/H92732` = "χ²".

**Confirmed correct (matched primary text exactly):**
- Setup: 6 subjects/group; €40 endowment each; 10 rounds; contribution options {€0, €2, €4}; target €120 ("reached or surpassed €120 at the end of the 10 rounds"); fair share €2/person/round; "€20 if a person had invested €2 per round"; no refunds; max possible €40.
- Risk treatments: 90% / 50% / 10% loss probability; 10 groups of six per treatment.
- Table 1 payoffs (free rider / fair sharer / altruist): 90% → 4/20/0; 50% → 20/20/0; 10% → 36/20/0. Verbatim.
- Nash-equilibrium clause: "each player invests less than €36" — verbatim.
- Mechanic/info/communication: per-round simultaneous display of all six decisions; fixed display position so individual strategies are trackable ("individual players were not anonymous within the game"); cumulative sum NOT displayed; pen and paper provided; opaque partitions; no communication; "little information" advertisement framing from ref. 28 — all confirmed.
- Findings — target reached: 5/10 (90%), 1/10 (50%), 0/10 (10%). Binomial tests n = 10, **P < 0.0001** (confirmed; the "<" notation is correct for the binomial tests). Failure-rate difference among treatments: P = 0.008, n = 30, df = 2,29, χ² = 9.66 — verbatim.
- Final group means: €118.2 ± 1.9 (90%), €92.2 ± 9.0 (50%), €73.0 ± 4.4 (10%); the five 90% groups that missed: €112.8 ± 1.2. Verbatim.
- Fair-sharers per group: 3.3 ± 1.3 / 2.1 ± 0.6 / 1.1 ± 0.3 (P = 0.003, n = 30, df = 2,29, F = 7.137). Extreme free rider/round: €1.4 ± 0.1 / 0.9 ± 0.2 / 0.5 ± 0.2 (P = 0.0003, n = 30, df = 2,29, F = 11.137). "in 8 of 10 groups won their big savings." All verbatim.
- Round dynamics z-statistics (now added): 90% selfish z = 2.739, fair-share z = 2.433, altruistic z = −6.325; 50% selfish z = −3.188, fair-share z = 5.161, altruistic z = −2.473; 10% selfish z = −3.196, fair-share z = 4.776, altruistic z = 0.259. All verbatim.
- Sample: 180 undergraduates, 30 groups of six, University of Cologne and University of Bonn. Verbatim ("We tested 180 undergraduates who participated in 30 groups of six subjects each ... at the University of Cologne and the University of Bonn").
- Citation metadata: PNAS 105(7):2291–2294, 2008; DOI 10.1073/pnas.0709546105; PMID 18287081; edited/approved by Robert May, approved December 18, 2007, received October 8, 2007; published February 19, 2008. Confirmed via PubMed. (Added PMCID PMC2268129.)

**Corrections made (draft was wrong; source value substituted):**
1. **Final-amount across-treatment test:** draft wrote "P < 0.0001 ... F = 13.784." Source reports the **exact value P = 0.0001** (glyph `/H11005` = "="). Corrected in Sections 5 and 9.
2. **Altruistic acts increasing in the 90% treatment:** draft wrote "P < 0.0001, z = 6.325." Source reports **P = 0.0001** (exact "=", not "<") and **z = −6.325** (negative sign present in source). Corrected in Section 5; the binomial-test "P < 0.0001" elsewhere is correct and was left unchanged.
3. Added the missing z-statistics for the 50% and 10% treatment dynamics (P-values were already correct).

**Numbers that remain uncertain (require the SI Appendix, not retrieved):**
- The literal loss-lottery mechanic: a single shared group draw vs. independent per-player draws. Main text ("the computer threw dice ... all group members would lose all their savings") reads as one group-level draw; not bit-exact confirmable without the SI Appendix.
- The "df = 2,29" rendering: the χ² line shows `df=2,29` clearly; the F-test lines render as `df=2.29` in the PDF text layer (a comma/period typesetting artifact). Both denote the same 2-and-29 degrees of freedom; the document normalizes to "df = 2,29," which is correct, but the source's own rendering is internally inconsistent.
- Full instruction wording, any show-up fee beyond the €40 endowment, and the formal non-pure-strategy equilibrium derivations — all live in the SI Appendix / ref. 28 and were not retrieved.

No factual numeric errors were found beyond the two "P = 0.0001 vs. P < 0.0001" overstatements above; all structural game-design parameters and reported results in the draft match the PNAS primary text.
