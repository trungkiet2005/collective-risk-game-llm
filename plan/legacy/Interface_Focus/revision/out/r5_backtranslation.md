# Vietnamese decision prompt: line-by-line back-translation

Source: [`crsd/prompts/crsd_en.txt`](../../../crsd/prompts/crsd_en.txt) and
[`crsd/prompts/crsd_vn.txt`](../../../crsd/prompts/crsd_vn.txt), both 30 lines, both
carrying the identical multiset of 42 `{placeholder}` slots (verified mechanically by
`r5_translation_qa.py`; no game parameter is written as a literal in either template —
every number reaches the agent through a placeholder, so the two languages cannot
disagree about a value).

Back-translation is literal, not idiomatic: it is meant to expose drift, not to read
well. `‖` marks a segment carrying a number or a conditional — the two things the
reviewer asked us to verify.

| # | English (original) | Vietnamese (as run) | Back-translation of the Vietnamese | Verdict |
|---|---|---|---|---|
| 5 | You are `{currentPlayerName}`, player `{playerPosition}` of `{nPlayers}`, in a group experiment that simulates a collective-risk social dilemma. | Bạn là `{currentPlayerName}`, người chơi số `{playerPosition}` trong `{nPlayers}` người, trong một thí nghiệm mô phỏng "tình thế lưỡng nan rủi ro tập thể". | You are `{currentPlayerName}`, player number `{playerPosition}` of `{nPlayers}` people, in an experiment simulating a "collective-risk dilemma". | ‖ identical role and count; "group" is carried by "trong `{nPlayers}` người" |
| 7 | At the start, each player privately receives an endowment of `{endowment}` monetary units. Your final cash payoff depends on the rules below. The game lasts exactly `{nRounds}` rounds. | Khi bắt đầu, mỗi người chơi được nhận riêng một khoản vốn `{endowment}` đơn vị tiền. Số tiền mặt cuối cùng bạn thực nhận phụ thuộc vào các quy tắc dưới đây. Trò chơi kéo dài đúng `{nRounds}` vòng. | At the start, each player privately receives a capital of `{endowment}` money units. The final cash you actually receive depends on the rules below. The game lasts exactly `{nRounds}` rounds. | ‖ faithful; "đúng" carries "exactly" |
| 9 | Each round, all `{nPlayers}` players decide simultaneously and in private how much to put into a shared "climate account". The only amounts allowed are `{contributionOptions}`. | Mỗi vòng, tất cả `{nPlayers}` người chơi đồng thời và riêng tư quyết định đóng bao nhiêu vào một "quỹ khí hậu" chung. Các mức được phép chỉ gồm `{contributionOptions}`. | Each round, all `{nPlayers}` players simultaneously and privately decide how much to contribute to a shared "climate fund". The permitted amounts consist only of `{contributionOptions}`. | ‖ faithful; action set closed by "chỉ gồm" = "consist only of" |
| 11 | The group's target: by the end of the game, the combined contributions of all `{nPlayers}` players must reach at least `{target}` (an average of `{fairShare}` per player per round). | Mục tiêu của nhóm: đến cuối trò chơi, tổng đóng góp của cả `{nPlayers}` người chơi phải đạt ít nhất `{target}` (trung bình `{fairShare}` mỗi người mỗi vòng). | The group's target: by the end of the game, the total contribution of all `{nPlayers}` players must reach at least `{target}` (on average `{fairShare}` per person per round). | ‖ faithful, **including the equal-split hint**, which is present in both languages and therefore cannot generate a language effect |
| 12 | If the group reaches `{target}`: every player keeps, in cash, whatever they did not contribute (for example, contributing `{fairShare}` every round leaves you `{fairShareKept}` at the end). | Nếu nhóm đạt `{target}`: mỗi người giữ lại (bằng tiền mặt) toàn bộ số tiền mình không đóng góp (ví dụ, đóng `{fairShare}` mỗi vòng thì cuối cùng bạn còn `{fairShareKept}`). | If the group reaches `{target}`: each person keeps (in cash) all the money they did not contribute (for example, contributing `{fairShare}` every round leaves you with `{fairShareKept}` at the end). | ‖ faithful; the worked example survives with both numbers |
| 13 | If the group does not reach `{target}`: the computer runs a lottery: with probability `{riskPercent}`% the group is hit by a disaster and every player loses all of their remaining money (final cash payoff 0); with the remaining `{safePercent}`% probability, each player keeps their remaining money. | Nếu nhóm không đạt `{target}`: máy tính quay xổ số: với xác suất `{riskPercent}`% nhóm gặp thảm hoạ và mọi người chơi mất tất cả số tiền còn lại (tiền mặt cuối cùng = 0); với xác suất `{safePercent}`% còn lại, mỗi người giữ được số tiền còn lại của mình. | If the group does not reach `{target}`: the computer draws a lottery: with probability `{riskPercent}`% the group meets a disaster and every player loses all remaining money (final cash = 0); with the remaining `{safePercent}`% probability, each person keeps their remaining money. | ‖ **the critical conditional.** Antecedent, both branches, both percentages and the zero payoff all preserved in the same order |
| 14 | Money put into the climate account is gone for good and is never refunded, whether or not the target is reached. | Tiền đã bỏ vào quỹ khí hậu là mất hẳn, không bao giờ được hoàn lại, dù có đạt mục tiêu hay không. | Money put into the climate fund is lost for good, never refunded, whether or not the target is reached. | faithful |
| 16 | After each round, all `{nPlayers}` contributions for that round are revealed to everyone. Names are hidden, but each player always appears in the same fixed position. Players cannot talk to or message each other. | Sau mỗi vòng, đóng góp của cả `{nPlayers}` người trong vòng đó được hiển thị cho mọi người. Danh tính được ẩn, nhưng mỗi người luôn xuất hiện ở cùng một vị trí cố định. Người chơi không được trao đổi hay nhắn tin cho nhau. | After each round, the contributions of all `{nPlayers}` people in that round are displayed to everyone. Identities are hidden, but each person always appears in the same fixed position. Players may not converse or message each other. | faithful ("Names" → "Danh tính"/identities is the only drift, and it is not load-bearing) |
| 18–20 | Current state: — Round `{currentRound}` of `{nRounds}`. — Your remaining money: `{remainingEndowment}`. | Tình trạng hiện tại: — Vòng `{currentRound}` trên tổng `{nRounds}`. — Số tiền còn lại của bạn: `{remainingEndowment}`. | Current situation: — Round `{currentRound}` of a total `{nRounds}`. — Your remaining money: `{remainingEndowment}`. | ‖ faithful |
| 21 | The climate account so far holds `{groupAccount}` of the `{target}` target. | Quỹ khí hậu đến lúc này có `{groupAccount}` trên mục tiêu `{target}`. | The climate fund so far has `{groupAccount}` of the `{target}` target. | ‖ faithful (this is the printed-total A/B arm) |
| 24 | Previous rounds (each player keeps the same position; you are position `{playerPosition}`): | Các vòng trước (mỗi người giữ nguyên vị trí; bạn là vị trí `{playerPosition}`): | Previous rounds (each person keeps the same position; you are position `{playerPosition}`): | faithful |
| 28–30 | Now decide your contribution for round `{currentRound}`. Allowed choices: `{contributionOptions}`. Output only your decision as a final line: `CONTRIBUTION: <one of {contributionOptions}>` | Bây giờ hãy quyết định mức đóng góp của bạn cho vòng `{currentRound}`. Các lựa chọn hợp lệ: `{contributionOptions}`. Chỉ xuất ra quyết định của bạn ở dòng cuối: `CONTRIBUTION: <một trong các giá trị {contributionOptions}>` | Now decide your contribution for round `{currentRound}`. Valid choices: `{contributionOptions}`. Output only your decision on the final line: `CONTRIBUTION: <one of the values {contributionOptions}>` | ‖ faithful; **the answer token `CONTRIBUTION:` is left untranslated in both**, so parsing is language-independent |

## Dynamic strings (built by the engine, not the template)

`crsd/engine/prompt.py::_LANG_STRINGS` localises the round history as well, so no
English leaks into a Vietnamese prompt:

| Element | English | Vietnamese | Back-translation |
|---|---|---|---|
| self marker | `(you)` | `(bạn)` | (you) |
| round label | `Round {n}` | `Vòng {n}` | Round {n} |
| history line | `you contributed {own}; group round total {total}` | `bạn đóng {own}; tổng nhóm vòng này {total}` | you contributed {own}; group total this round {total} |
| cumulative | `(cumulative {c})` | `(tích luỹ {c})` | (cumulative {c}) |

## Quantitative QA, from the comprehension battery

The battery is a behavioural translation test: if the Vietnamese prompt had corrupted a
number, a rule or the conditional, the agents reading it would answer questions about
that content worse. It does not.

| Probe | EN | VN | Gap |
|---|---|---|---|
| Rules axis, all questions (20,160 probes) | 99.40% | 98.74% | **+0.66 pp** |
| `rules_risk_pct` — state the catastrophe probability | 98.02% | 98.97% | **−0.95 pp** (VN better) |
| `rules_payoff_disaster` — payoff if the disaster fires | 100.00% | 100.00% | 0.00 pp |
| `rules_actions` / `rules_endowment` / `rules_n_rounds` | 100.00% | 100.00% | 0.00 pp |
| `rules_target` | 100.00% | 91.03% | +8.97 pp |
| State axis (arithmetic the agent must perform) | 73.63% | 61.80% | +11.83 pp |

Two things follow. First, the conditional clause that carries the catastrophe
probability survives translation intact — it is the one probe where Vietnamese is
*better*. Second, the only Rules question with a gap, `rules_target`, is not a
translation defect but one model: Llama-3.1-8B falls from 100% to 37.2% while the other
six models answer at 100% in both languages. A corrupted prompt would degrade every
reader of it.

| `rules_target` | EN | VN |
|---|---|---|
| Qwen2.5-7B, Gemma-2-9B, Gemma-2-27B, Qwen2.5-32B, Llama-3.3-70B, Qwen2.5-72B | 100% | 100% |
| Llama-3.1-8B | 100% | 37.2% |

## Tokenisation

Measured on the rendered prompts logged in `turns.jsonl`, matched by round, with the
`o200k_base` encoding as a proxy for the hosted tokenisers (which are not public):

| | EN | VN | ratio |
|---|---|---|---|
| mean prompt length (tokens) | 537.4 | 642.6 | **1.203** |

Vietnamese costs about 20% more tokens for identical content. Both are far below the
4,096-token context used for the open-weight arm, so nothing is truncated in either
language, but the ratio is worth stating: any per-token effect on attention or on cost
is 1.2× larger in Vietnamese.
