# Review câu chữ và cấu trúc — `paper/AAMAS/main.tex` (19-09-2026)

## ✅ Đã áp dụng (19-09-2026, chiều)

Bản `main.tex` hiện tại đã áp dụng review dưới đây. Kiểm lại sau khi sửa:

- `make_submission.py`: **OK**. Body đúng 8 trang (còn khoảng 8 dòng trống ở cột phải trang 8), references bắt đầu trang 9, không có en/em dash, không lộ tên nhóm.
- `test_paper_equilibrium.py` và `test_publication_migrations.py` qua.
- Không có ref hay citation nào undefined ở cả hai PDF.

**Đã làm:**

- **Title** mới do người dùng chọn. Abstract viết lại, `OPENREVIEW_ABSTRACT.txt` đồng bộ từng chữ.
- **Cấu trúc 8 → 7 section**: 4 Incentives (4.1 grid, 4.2 prompt controls, 4.3 value question), 5 Partners (5.1 fixed, 5.2 mixed), 6 Selection, 7 Discussion and conclusion.
- **Intro** có ba câu hỏi. Bốn bullet mang cùng tên với Figure 1c.
- **Related work** tách thành 4 đoạn. Đoạn "social dilemmas" chứa bài gần nhất (Pham et al.) và câu nói ba điểm khác.
- Mọi chỗ gọi selection là "tablemate/across-table scoring" đã đổi thành "one table / larger population". Phạm vi gồm:
  - `main.tex`, cả alt-text của Figure 1 và Figure 6;
  - section selection trong supplement;
  - nhãn panel trong `analysis/selection.py` ("One table, N=6" / "Many tables, N=30") và `supp_groups.py`;
  - các hình, bảng sinh lại từ hai script đó. Số liệu không đổi, `tables/num_selection.tex` giống hệt bản cũ.
- **16 reference mới** chuyển từ `refs_candidates.bib` sang `refs.bib`, cộng thêm EGTtools đã có sẵn. Ba bài của nhóm được cite ở ngôi thứ ba, bib ghi "tác giả đầu and others" để qua cổng tên của `make_submission.py`. **Bản camera-ready cần khôi phục danh sách tác giả đầy đủ.**
- Supplement:
  - các số section của bài chính chuyển sang `\ref{main-sec:…}`;
  - `\externaldocument` dời xuống sau các `\input` macro. Build supplement với `main.aux` mới hỏng **từ trước** (đã kiểm trên bản HEAD), vì caption Table 3 chứa `\GridOptMean`.

**Khác với đề xuất ban đầu (vì trần 8 trang):**

- Bỏ câu mở Section 4. Câu mở Section 5 gộp vào đầu 5.1.
- Ethics gộp vào đoạn "Threats, limitations and ethics".
- Viết gọn khoảng 400 từ ở các đoạn dài, không bỏ claim nào.
- Bỏ hai câu rào đón trùng ý ở Section 6 ("We do not establish the same ranking…", "These point estimates test…"). Ý "conditional on the base-prompt payoffs" vẫn giữ.

Bản review cho người viết, không đưa vào submission (`make_submission.py` chỉ đóng gói `main.pdf` và `supplement.pdf`).
Thứ tự: cấu trúc → intro/abstract → nhất quán thuật ngữ → từng câu → cơ học → reference.
Số dòng là số dòng trong `main.tex` tại commit `c834c0b`.

---

## 0. Năm việc đáng làm nhất (theo mức nặng)

1. **Section 5 hiện tại gom hai thứ không cùng loại.** Tên section là "Answers track the risk; play does not", nhưng nửa sau (scripted partners) nói "Partners matter; risk does not". Đây là lỗi logic chứ không chỉ chuyện đếm section. Sửa bằng cách xếp lại theo đúng ba danh từ trong title: **Incentives / Partners / Selection** (xem §1).
2. **Chỗ nói về selection đang mâu thuẫn với chính bài.** Dòng 355 viết "not a scoring-only intervention", nhưng dòng 117 ("switch from tablemate to across-table scoring"), heading dòng 357 ("Scoring against tablemates…"), `\Description` của Figure 1 (dòng 84) và của Figure 5 (dòng 363) vẫn dùng cách hiểu cũ "tablemate vs across-table scoring". Reviewer sẽ bắt được. Đây cũng là điều `CLAUDE.md` dặn không được khôi phục.
3. **Intro đoạn 2 tự mâu thuẫn với Section 4.** Câu "Self-play, a common test, cannot answer either question" không đứng được, vì Section 4 dùng *self-play trên lưới risk* để trả lời đúng câu hỏi 1. Cái không trả lời được là **tỉ lệ thành công của self-play ở một mức risk cố định**.
4. **Chưa có kết luận.** Bài dừng ở "Ethics". Đổi Section 8 thành "Discussion and conclusion", gộp *Threats to validity* với *Limitations* (hai đoạn đang trùng ý) để lấy chỗ, rồi thêm 2–3 câu kết.
5. **Cùng một finding đang có ba cái tên** (Figure 1c, bullet trong intro, tên section). Chọn một tên và dùng ở cả ba chỗ (§3).

---

## 1. Cấu trúc section: 8 → 7, xếp theo title

Tám section không phải con số lạ ở AAMAS. Vấn đề thật là phần kết quả bị cắt thành bốn section theo từng finding, trong đó section 5 ghép sai. Title đã hứa ba phần, **Incentives, Partners, and Selection**, nên cho phần kết quả đi đúng ba phần đó:

| Mới | Tên đề xuất | Lấy từ bản hiện tại |
|---|---|---|
| 1 | Introduction | §1 |
| 2 | Related work | §2 (tách làm 4 đoạn, xem §4) |
| 3 | Game and evaluation design | §3 (giữ nguyên 3.1, 3.2) |
| **4** | **Incentives: payment does not follow the stakes** | §4 + §5.1 |
| | 4.1 Self-play across risk | §4 ¶1–3 (flat, zero risk, three ways to lose) |
| | 4.2 Prompt controls | §4 ¶4–5 (rewording, neutral wording, goal) |
| | 4.3 Asking the agent | §5 mở đầu + §5.1 (value question, Figure 3) |
| **5** | **Partners: simple responses and fragile tables** | §5.2 + §6 |
| | 5.1 Fixed partners | §5.2 (best response, Table 5) |
| | 5.2 Mixed tables | §6 (Figure 4, Figure 5) |
| **6** | **Selection: population size changes the winner** | §7 |
| 7 | Discussion and conclusion | §8, gộp Threats + Limitations, thêm Conclusion |

Vì sao cách này dễ đọc hơn:

- Người đọc thấy title → ba câu hỏi ở intro → ba section kết quả, cùng một thứ tự và cùng tên gọi.
- Value question hỏi "lựa chọn nào trả nhiều hơn khi risk đổi", tức là câu hỏi về *incentive*, nên thuộc §4. Đoạn mở của §5 hiện tại ("Perhaps the agents simply do not understand the game.") vẫn dùng tốt làm câu mở cho 4.3.
- Scripted partners và mixed tables cùng trả lời câu "hành vi có phụ thuộc bạn chơi không", nên thuộc cùng §5.
- Bỏ được hai heading, tiết kiệm khoảng 6 dòng. Bài đang chạm trần 8 trang, nên chỗ này dùng để thêm reference.

Nếu muốn còn **6 section**, chuyển Selection thành 5.3. Tôi không khuyên cách này, vì selection là finding thứ tư trong Figure 1 và có mô hình riêng (Fermi, rare mutation), nên đáng có section riêng.

Việc kỹ thuật khi chuyển:

- Giữ nguyên các `\label`: `sec:risk` (§4), `sec:knowing` (giờ là 4.3), `sec:groups` (5.2), `sec:selection` (§6). Thêm `sec:partners` cho §5.
- Caption Figure 1 dòng 85: "Findings of Sections~\ref{sec:risk} to~\ref{sec:selection}" vẫn đúng.
- Câu mở §5 (continuation marker), ví dụ: *"Section 4 held the partners fixed as copies of the same model. We now change the partners, first to scripted players against whom the best response can be computed exactly, then to a second model."*
- Heading đoạn "Answers move with the risk; play does not." (dòng 286) đang trùng gần nguyên văn tên section. Sau khi chuyển thì đổi thành *"Answers move with the risk; payments do not."* hoặc bỏ heading.

---

## 2. Introduction

### 2.1 Có cần gộp đoạn không?

**Không cần gộp.** Năm đoạn và bốn bullet dài khoảng một trang, đúng cỡ intro AAMAS. Vấn đề nằm ở **nội dung từng đoạn**:

| Đoạn | Hiện đang làm | Vấn đề |
|---|---|---|
| P1 (dòng 89) | Bối cảnh + 2 câu hỏi | Chỉ có 2 câu hỏi, nhưng title và finding 4 nói tới selection → thiếu câu hỏi thứ 3. Câu đầu không có citation. "Each such agent is a player in a social dilemma" nói quá. |
| P2 (91) | Vì sao self-play không đủ | Mâu thuẫn với §4 (xem §0 mục 3). Thiếu citation cho "a common test". |
| P3 (93) | Giới thiệu game + benchmark | Ổn, nhưng ý quan trọng nhất về mặt phương pháp (tại p=0 và sau khi settled, trả tiền là bị dominate) chỉ nằm ở một câu cuối, lại có đại từ "it" treo lơ lửng. |
| P4 (95) | Định nghĩa "default" + phép thử zero-risk + 5 model + 4 design + câu contribution | **Một đoạn gánh bốn ý.** Định nghĩa "default" đặt trước khi người đọc biết finding, nên đọc giống câu phòng thủ. Câu contribution thì bị chôn giữa đoạn. |
| Bullet 2 (99) | Answers vs play | Câu thứ hai nói về scripted partners, không khớp tên bullet. |
| P5 (104) | Kết | "make its failures better or worse" nghe lạ. |

### 2.2 Bản viết lại đề xuất (giữ đúng số liệu và phạm vi claim hiện có)

> **P1.** Language-model agents are starting to act for people in shared settings: they spend budgets, draw on shared compute and negotiate over common resources~[CITE]. Many of these settings are social dilemmas, because what one agent pays helps the group but costs its owner. Before deploying such agents, a designer needs to answer three questions. Does an agent's cooperation depend on what is at stake? Does it depend on what the other agents do? And which agents prevail when a system keeps or copies the ones that earn the most?
>
> **P2.** The usual evidence, success in self-play at a fixed level of risk~[CITE piatti2024cooperate, huang2025competing, kumar2026cooperative], cannot answer these questions. When every seat holds a copy of the same model, an agent that weighs the stakes and an agent that repeats a fixed rule can leave the same record of play. A success rate also hides how far a group is from the best it could have done: a group can reach its goal and still waste most of its money. And a prompt that states a group target and a number of rounds already suggests an equal split, so an agent that repeats that split looks cooperative on the usual summary measures.
>
> **P3.** We study these questions in the collective-risk social dilemma, a game introduced to study climate cooperation~\cite{milinski2008collective}. Players pay into a shared pool over several rounds, and if the pool misses a target, a catastrophe destroys everyone's savings with probability $p$. For risk-neutral players, group welfare is highest when nobody pays below $p=\tfrac12$ and when the group reaches the target exactly above it, for example by each paying the \emph{fair share}, the target split equally. The game also contains two situations in which paying only lowers a player's own cash: when there is no risk, and once the outcome is settled. Neither risk attitude nor concern for the group can explain payment in these situations, so they separate a default from a response to the stakes.
>
> **P4.** We evaluate five low-cost production models, Claude Haiku 4.5, Gemini 3.5 Flash-Lite, GPT-5.6 Luna, Qwen3-235B and Grok 4.20, with four linked designs: self-play over a full risk grid with prompt controls and value questions; scripted partners against whom the best response can be computed exactly; tables that mix two models; and payoff-based selection over those tables, with each model treated as a strategy of an empirical game~\cite{wellman2006methods,tuyls2018generalised}. Our contribution is this evaluation, which compares every design with a computed optimum, and what it reveals about these five models; we propose no new equilibrium concept or selection principle. We use \emph{default} for near-flat payment across risk levels under a fixed prompt, a description of behaviour rather than of internal reasoning. We report four findings (Figure~\ref{fig:overview}).
>
> *(bullets: xem §3 để thống nhất tên; chuyển câu "Beside scripted partners who make every payment a loss…" từ bullet 2 sang bullet 3)*
>
> **P5.** For the five models we test, payment is a default rather than a response to the stakes. A default can work well beside copies of itself; whether it fails elsewhere depends on who the partners are, on whether the agent's goal is stated, and on how the system selects among agents.

Chỗ `[CITE]` ở P1: cần nguồn cho câu "agents act for people…". Agent tìm reference đang kiểm chứng Hammond et al. 2025 (*Multi-Agent Risks from Advanced AI*) và Tomasev et al. 2025 (*Virtual Agent Economies*). Chỉ dùng khi đã xác minh được.

---

## 3. Nhất quán thuật ngữ

### 3.1 Cùng một finding, ba cái tên

| Finding | Figure 1c (TikZ, dòng 179–226) | Bullet intro | Tên section |
|---|---|---|---|
| 1 | Near-flat payments for most models | Risk does not change the default | Risk does not change the default |
| 2 | Answers track the risk; **payments** do not | Answers track the risk; **play** does not | như bullet |
| 3 | One late dropout breaks a fair-share table | An exact fair share has no slack | Defaults in mixed groups |
| 4 | Population size changes who is selected | như figure | Which agent wins under selection |

Đề xuất: **lấy tên trong Figure 1 làm chuẩn cho bullet**, vì figure vẽ tay, sửa tốn công hơn. Tên section theo §1 (Incentives / Partners / Selection). Nếu bullet 3 gom cả scripted partners thì heading "One late dropout breaks a fair-share table" vẫn là ý chính, giữ được.

### 3.2 Selection: bỏ hẳn từ vựng "scoring / tablemate vs across-table"

Các chỗ cần sửa để khớp dòng 355 ("not a scoring-only intervention"):

| Dòng | Hiện tại | Đề xuất |
|---|---|---|
| 84 (`\Description` Fig 1) | "…favours the smallest payer when agents are compared with their tablemates… when agents are compared across tables…" | "…favours the smallest payer in a population of one table ($N=6$)… favours the table that reaches the target in a larger randomly mixed population ($N=30$)…" (figure đã ghi "one table ($N=6$)", chỉ có alt-text là cũ) |
| 117 | "showing that the switch from tablemate to across-table scoring happens at seven or eight agents" | "and show that the selected model changes once the population grows beyond one table, at seven or eight agents" |
| 357 (heading) | "Scoring against tablemates rewards the smallest payer." | "In a population of one table, selection rewards the smallest payer." |
| 363 (`\Description` Fig 5) | "With tablemates, … Across tables, …" | "With one table ($N=6$), … In the larger population ($N=30$), …" |
| 385 | "Audit how population size and the comparison process affect selection" | Giữ được, nhưng "comparison process" gợi lại ý scoring. Gọn hơn: "Audit how population size and the imitation process affect selection" |

Các chỗ còn lại dùng "tablemate" theo nghĩa đen (người ngồi cùng bàn, dòng 350, 355, 358, 369) thì đúng, giữ nguyên.

### 3.3 Các cặp từ

- **equal share / fair share / equal split / exact split.** Bài định nghĩa *fair share* (20/seat) và *exact split* (2 mỗi vòng) trong Table 1, rồi abstract lại dùng "near the equal share". Chỉ dùng "equal split" khi nói về gợi ý trong prompt (dòng 91, 207, 247), còn lại dùng "fair share".
- **contribute / pay.** Abstract dùng "contribute", thân bài dùng "pay". Chấp nhận được, nhưng abstract nên dùng "pay" cho khớp (38 lần "pays" trong thân bài).
- **"tells no risk apart from some risk"** (dòng 234, 250) là cách nói tự chế, đọc khó. Thay bằng: *"distinguishes zero risk from positive risk but not low risk from high risk"*.
- Chính tả Anh–Mỹ: đã nhất quán kiểu Anh (behaviour, favour, randomised). Tốt, giữ vậy.

---

## 4. Abstract và title

### 4.1 Câu hỏi của bạn: "Language-model agents increasingly act in shared environments where one local choice can expose a whole group to collective loss."

**Ngữ pháp đúng**, nhưng có ba chỗ nên sửa:

1. **"local choice"**: "local" không rõ nghĩa. Ý bạn là "lựa chọn của một agent", nhưng với reviewer MAS, "local" thường gợi *local information* hoặc *local interaction* (tương tác trên mạng/lưới). Thế là người đọc bị dẫn sang hướng khác ngay câu đầu.
2. **"a whole group … collective loss"**: lặp ý, vì "whole group" và "collective" nói cùng một thứ.
3. **Câu này chưa nêu thế lưỡng nan.** Nó chỉ nói "một lựa chọn có thể gây hại cho nhóm" (externality). Thế lưỡng nan của CRSD là: *muốn nhóm tránh thiệt hại thì từng agent phải bỏ tiền của mình ra*. Finding chính của bài lại là agent **trả tiền bất kể stakes**, nên câu mở cần dựng cả hai phía: cái giá cá nhân và cái lợi của nhóm.

Hai phương án:

- (a, khuyên dùng) *"Language-model agents increasingly act for people in shared settings, where a group avoids a common loss only if each agent gives up some of its own resources."*
- (b, giữ ý gốc) *"Language-model agents increasingly act in shared settings, where one agent's choice can decide whether the whole group suffers a loss."*

### 4.2 Các câu khác trong abstract

| Câu gốc | Vấn đề | Sửa |
|---|---|---|
| "agents contribute to a shared threshold over repeated rounds" | Không ai "contribute to a threshold". Người ta góp vào *pool* để *đạt* threshold. | "agents pay into a shared pool over repeated rounds" |
| "a catastrophe destroys savings when the threshold is missed" | **Thiếu xác suất**, trong khi $p$ là biến chính của cả bài | "…and if the pool misses a target, a catastrophe destroys all savings with a given probability" |
| "a dissociation between cooperative-looking play and incentive response" | "incentive response" là cụm danh từ ghép khó đọc | "a gap between cooperative-looking play and the response to incentives" |
| "Four models contribute near the equal share … and most also pay at zero risk" | "most" không rõ là most của 4 hay của 5 | "Four models pay about an equal share of the target at every positive risk level, and four of the five also pay at zero risk, where paying cannot help" |
| "answer risk comparisons correctly in separate questions" | Mơ hồ | "correctly answer, in separate questions, which choice pays more at each risk level" |
| "some pay after the outcome is settled" | "settled" chưa định nghĩa trong abstract | "some keep paying after payment can no longer change the outcome" |
| "In mixed tables, one late under-contributor can break…" | "mixed tables" chưa định nghĩa | "In tables that mix two models, one late under-contributor can make an otherwise successful group fail" |
| "harms group success" | Cụm lạ | "lowers how often groups reach the target" |
| "conditional on the base-prompt payoffs" | "base prompt" chưa định nghĩa | "hold for the payoffs measured under our base prompt" |
| "These selection results… These findings…" | Hai câu liên tiếp mở bằng "These" | Câu sau đổi thành "Together, the findings show…" |

Abstract hiện dài khoảng 260 từ, dày đặc như một danh sách. Bản gọn, khoảng 230 từ, không có số đo:

> Language-model agents increasingly act for people in shared settings, where a group avoids a common loss only if each agent gives up some of its own resources. We ask whether such agents cooperate because of the stakes, because of their partners, or by default. Five low-cost production models play a collective-risk social dilemma: over ten rounds, six players pay into a shared pool, and if the pool misses a target, a catastrophe destroys all savings with a given probability. We combine self-play across risk levels, prompt controls, value questions, scripted partners, mixed tables and payoff-based selection. Four models pay about an equal share of the target at every positive risk level, and four of the five also pay at zero risk, where paying cannot help. Removing normative wording leaves this pattern intact, whereas stating that only the agent's own cash matters removes most zero-risk payment. Several models correctly answer which choice pays more at each risk level but barely change what they pay. Against fixed partners, no model consistently plays the best response, and some keep paying after the outcome is settled. In tables that mix two models, one late under-contributor can make an otherwise successful group fail. With payoffs measured under our base prompt, rare-mutation imitation in a population of one table selects the smallest payer and lowers group success, whereas a larger mixed population selects an exact fair-share player at moderate and high risk. Evaluations of multiagent systems should therefore state the agent's objective, compare play with a computed optimum, include situations where paying is dominated, and test mixed populations.

Nhớ sửa `OPENREVIEW_ABSTRACT.txt` theo, vì file đó phải khớp từng chữ.

### 4.3 Title

"When Low-Cost Language Models Cooperate by Default: …" đọc được theo hai nghĩa: *"khi nào thì chúng hợp tác mặc định?"* hoặc *"trong trường hợp chúng hợp tác mặc định"*. Ngoài ra, "Low-Cost" đặt đầu title dễ mời reviewer nghĩ "model rẻ thì yếu, có gì lạ". Phạm vi vẫn phải nói rõ, nhưng nói ở abstract là đủ. Hai phương án:

- *Cooperating by Default: Language-Model Agents, Stakes, Partners, and Selection in a Collective-Risk Dilemma*
- *Cooperation Without Incentive Response: Language-Model Agents in a Collective-Risk Dilemma*

Nếu giữ title hiện tại thì cũng không sai. Đây là mục tùy chọn.

---

## 5. Sửa từng câu

### Introduction

| Dòng | Gốc | Vấn đề | Sửa |
|---|---|---|---|
| 89 | "Each such agent is a player in a social dilemma" | Nói quá: không phải agent nào cũng ở trong một social dilemma | "Many of these settings are social dilemmas, because…" |
| 89 | "share compute" | Không có citation cho cả câu | Thêm citation (§2.2) |
| 91 | "Self-play, a common test, cannot answer either question." | Mâu thuẫn với §4 | "The usual evidence, success in self-play at a fixed level of risk, cannot answer…" |
| 91 | "looks cooperative on every summary measure" | "every" nói quá | "on the usual summary measures" |
| 93 | "For risk-neutral players, it is to pay nothing below risk one half and exactly reach the target above it." | "the benchmark … is to pay" lủng củng; "risk one half" là cách nói lạ | Xem P3 ở §2.2 |
| 93 | "so risk attitude alone cannot explain it" | "it" không có danh từ đi kèm | "so risk attitude cannot explain any payment there" |
| 95 | "Four designs combine a full self-play risk grid, …" | Động từ sai: bốn design không "combine" bốn thứ | "Four designs cover…" |
| 95 | "Our contribution is this linked evaluation" | "linked evaluation" mơ hồ | Xem P4 ở §2.2 |
| 100 | "a table that overpays absorbs it" | "it" mơ hồ | "absorbs the shortfall" |
| 104 | "can make its failures better or worse" | "failures better" nghe lạ; "its" mơ hồ | Xem P5 ở §2.2 |

### Related work

Đề xuất tách đoạn "Language models in games" (dòng 117, 14 citation) thành hai đoạn. Những bài gần nhất (Kumar, Willis, Celiktemel, Slumbers) là đối thủ trực tiếp, xứng đáng có đoạn riêng với câu "We differ…" rõ ràng:

1. *Collective risk and selection*: giữ, thêm các bài EGT của nhóm Han (§7).
2. *Language models as strategic players*: economic subjects, repeated games, focal points, knowing-doing gap.
3. *Language models in social dilemmas and collective risk*: GovSim, public goods, Slumbers, Kumar, Willis, Celiktemel, FAIRGAME / nhóm Han. **Kết đoạn bằng ba điểm khác biệt.**
4. *Multiagent evaluation*: giữ.

| Dòng | Gốc | Sửa |
|---|---|---|
| 114 | "was built to study why groups fail" | "was introduced to study why groups fail" |
| 114 | "inequality and communication change the result" | "inequality and communication change how often groups succeed" |
| 114 | "Games with a threshold have many equilibria" | "Threshold public goods games have many equilibria" |
| 114 | "This literature tells us that behaviour *should* move with the risk" | "This literature predicts that behaviour moves with the risk" ("tells us" là văn nói) |
| 117 | "showing that the switch from tablemate to across-table scoring…" | Xem §3.2 |
| 120 | Câu 41 từ "Tournaments that mix language models…, cooperation evolves…, and cooperation sustained…" | Tách: "In tournaments that mix language models with classic strategies, models show distinct strategic fingerprints in the prisoner's dilemma~\cite{payne2025strategic}. In a donor game, cooperation evolves differently across base models~\cite{vallinder2025cultural}, and cooperation sustained by repetition weakens when co-players differ~\cite{tewolde2026coopeval}." |

### Section 3

| Dòng | Gốc | Sửa |
|---|---|---|
| Table 1, dòng 153 | "Risk above which reaching the target pays" | "pays" mơ hồ (trả tiền hay có lợi?) → "Risk above which reaching the target maximises group welfare" |
| 166 | Câu 45 từ "The ten-round game, in which strategies can react…" | Tách đôi: "…has the same totals in pure-strategy Nash equilibrium; the supplementary material gives the full proof. We claim nothing about subgame perfection, …" |
| 169 | "This is not a unique equilibrium…" | Linter bắt "This" trơ → "This benchmark is not…" |
| 169 | "Paying is dominated in own cash at $p=0$ and after the outcome is settled, provided a missed target still leaves a positive chance of keeping savings ($p<1$)." | Điều kiện $p<1$ chỉ áp cho vế "settled"; ghi rõ ra: "Paying is dominated in own cash at $p=0$ and, for $p<1$, after the outcome is settled." |
| 210 | "A reply that is cut off at the output limit of 3,000 tokens is asked again with a larger limit rather than guessed" | Câu bị động với chủ ngữ sai ("a reply is asked"). Sửa: "When a reply reaches the 3,000-token output limit, we request it again with a larger limit instead of guessing the move, and all but … could be read." |

### Section 4 (sẽ thành 4.1–4.2)

| Dòng | Gốc | Sửa |
|---|---|---|
| 231 | "Human groups with the same rules reach the target…" | "In the original experiment with the same rules, human groups reached the target…" (kết quả của người khác nên dùng quá khứ) |
| 234, 250 | "tells no risk apart from some risk" | Xem §3.3 |
| 237 | Đoạn "Three ways to lose" dài nhất bài, có câu 45 từ và câu **71 từ** | Tách thành hai đoạn: (i) *Three ways to lose*: ba kiểu mất (trả ở risk thấp / trả quá target / bỏ vòng cuối) và câu "Success rates hide all of this"; (ii) *Last-round rules*: Qwen theo đồng hồ, Luna theo pivot, Haiku đọc được pool. |
| 237 | Câu 71 từ "The skip follows the clock, not the pool, much as … and it almost never stops in an earlier round once the target is met." | "The skip follows the clock, not the pool. Across all games with the base prompt, Qwen3-235B skips the last payment as often when its payment is needed as when the others' fair shares already suffice (\StratQwenZeroPivotal\% of seats in both cases). It almost never stops in an earlier round once the target is met. Human contributions show a similar end-game decline in repeated public goods games~\cite{andreoni1988free}." |
| 247 | "so the hint set a ceiling and guided precision but was not the source of the cooperation" | "guided precision" mơ hồ → "so the hint capped some models' payments and helped others pay exactly 2 per round, but it was not the source of the payment" |
| 250 | "The default does not come from the normative words." | Nói hơi chắc → "The normative words are not the main source of the default." |
| 250 | Câu 43 từ "With neutral wording, most models still pay…" | Tách sau "…what they paid before." rồi viết tiếp "GPT-5.6 Luna plays the exact split less often, and Grok 4.20 pays even more (Table~\ref{tab:robust})." |
| 253 (caption Table 4) | "…with permutation $P<0.01$, every bold shift has $P<0.001$…" | Lỗi comma splice → "…with permutation $P<0.01$; every bold shift also has $P<0.001$, below…" |

### Section 5 (sẽ thành 4.3 và 5.1)

| Dòng | Gốc | Sửa |
|---|---|---|
| 272 | "In the in-game question games we question the first seat at the start, in the middle and at the end of the game, about the state it has just decided on." | Lặp "question" hai lần → "In the question games, we ask the first seat at the start, middle and end of the game about the state in which it has just moved." |
| 272 | "We therefore rest on one value question" | "We therefore rely on one value question" |
| 286 | Heading trùng tên section | Xem §1 |
| 291 | "We found the best response to each kind by trying every possible sequence…" | Dùng thì hiện tại, nói rõ quy mô: "We compute the best response to each kind by enumerating all $3^{10}$ sequences of the model's own moves." |
| 291 | Câu 44 từ "Beside partners who always pay 0 the target cannot be reached, and…" | Tách: "Beside partners who always pay 0, the target cannot be reached; beside partners who always pay 4, it is reached without the model. The best response to both is therefore to pay nothing, and once the history settles the outcome, paying is also dominated." |
| 297 | Câu 50 từ "For Claude Haiku 4.5, …, the kind of partner explains most of the variation (…) and the risk …" | Tách trước "while for an exact best responder…": "…at most \ScrRiskShareMax\%. For an exact best responder in the same games, the risk would explain half of it." |
| 307 | "Gemini 3.5 Flash-Lite pays its usual rate, and it and Claude Haiku 4.5 stop once…" | "and it and" đọc vấp → "Gemini 3.5 Flash-Lite pays its usual rate; both it and Claude Haiku 4.5 stop once…" |

### Section 6 (sẽ thành 5.2)

| Dòng | Gốc | Sửa |
|---|---|---|
| 339 | "GPT-5.6 Luna also loses success." | "tables with GPT-5.6 Luna also succeed less often." |
| 342 | "Generous partners are free-ridden on." | Bị động kết thúc bằng giới từ → "Agents free-ride on generous partners." |

### Section 7 (sẽ thành §6)

| Dòng | Gốc | Sửa |
|---|---|---|
| 355 | "Under Fermi imitation, an agent copies…" / "We assume rare mutation…" | **Thiếu citation cho hai giả định mô hình quan trọng nhất**: Fermi rule (Szabó & Tőke 1998; Traulsen, Nowak & Pacheco 2006) và giới hạn đột biến hiếm (Fudenberg & Imhof 2006). Reviewer EGT sẽ hỏi ngay. |
| 357 | Heading "Scoring against tablemates…" | Xem §3.2 |
| 358 | Câu 52 từ "At $p=0.5$, where …, and at $p=0.9$, where …, the selected population reaches it far less often…" | Tách: "Reaching the target is one of two optima at $p=0.5$ and the only one at $p=0.9$. At both risks, the selected population reaches it far less often than a model picked at random (… at $p=0.9$), and stronger selection pushes group success close to zero." |
| 358 | "One game shows the mechanism." | Đây là ví dụ tính tay, không phải một ván quan sát được → "A worked example shows the mechanism." |
| 369 | "Its observed self-play attains the welfare optimum, but Nash equilibrium alone does not imply resistance to payoff-based imitation." | Câu nhảy từ "welfare optimum" sang "Nash" mà không có cầu nối → "Its self-play attains the welfare optimum above the pivot, and an all-fair-share table is a Nash equilibrium there, but neither property guarantees that imitation selects it." |

### Section 8 (sẽ thành §7)

| Dòng | Gốc | Sửa |
|---|---|---|
| 382 | Câu 53 từ, ba giả thuyết nối bằng dấu chấm phẩy | Tách thành ba câu, mỗi câu một giả thuyết một citation |
| 388 | "Shared prompts can also affect models differently." | Mơ hồ, không nói được gì → bỏ, hoặc nói cụ thể (ví dụ cùng một prompt nhưng mỗi model hiểu "must" khác nhau) |
| 388 + 391 | *Threats to validity* và *Limitations* là hai đoạn trùng ý | Gộp thành một đoạn "Threats and limitations" |
| (mới) | Chưa có kết luận | Thêm đoạn *Conclusion*, 2–3 câu, nói điều **chỉ nói được sau khi đã đọc kết quả**, ví dụ: *"Cooperative-looking self-play can come from a default that ignores the stakes. Such a default fails in predictable places: where paying is dominated, beside one late dropout, and under selection in small populations. These are the places an evaluation of multiagent systems should probe."* Không viết lại intro ở thì quá khứ. |

---

## 6. Cơ học (linter `paper_lint.py`, 23 cảnh báo)

- **8 câu dài hơn 40 từ**: 120, 166, 236/237 (×2), 249/250, 291, 296/297, 357/358, 381/382. Đã có bản sửa cho từng câu ở §5.
- **3 lỗi "This/These" trơ**: 169, 339, 358. Dòng 169 đã sửa ở trên. Dòng 339 và 358 là "This is an arithmetic repair" và "This is the known result". Hai câu này đọc vẫn hiểu, nhưng thêm danh từ thì tốt hơn: "This repair is arithmetic, not a tested intervention" và "This outcome is the known result that…".
- **Bib entries không được cite**: `dickinson1985actions`, `fernandezdomingos2023egttools`. `analysis/selection.py` (dòng 47–49) **có dùng** `egttools.analytical.StochDynamics` để kiểm chéo mọi xác suất fixation và vẽ invasion diagram, nên phải cite EGTtools, ví dụ ở cuối đoạn *Selection process*: "…we cross-check every fixation probability with EGTtools~\cite{fernandezdomingos2023egttools}." (Lenaerts là đồng tác giả; nhóm này rất gần nhóm thầy Han.) `dickinson1985actions` thì kiểm lại: nếu không cần thì xoá.
- **Brace cả title trong bib** (`BIB_TITLE_BRACED`, 4 entry): chỉ cần brace acronym, ví dụ `{EGTtools}: Evolutionary game dynamics in {Python}` là đúng rồi. Linter báo nhầm ở đây vì title bắt đầu bằng `{EGTtools}`. Mục này bỏ qua được.
- Cảnh báo `aamas.cls`: "CCS concepts are mandatory for papers over two pages". Template mẫu AAMAS không có CCS; kiểm lại CFP 2027, nếu không yêu cầu thì bỏ qua.
- `main.log` ghi "10 pages" trong khi `main.pdf` hiện có 9 trang: log là của một lần build cũ. Build lại trước khi nộp.
- Trang: nội dung hết trang 8, reference ở trang 9. **Không còn dòng trống nào.** Mọi reference thêm vào phải lấy chỗ từ các thay đổi ở §1 (bỏ 2 heading) và §5 (gộp Threats + Limitations).

---

## 7. Reference mới

`refs_candidates.bib` (cùng thư mục) có **59 entry**. Tất cả đã được kiểm với Crossref, trang publisher, arXiv API, ACL Anthology, PMLR/NeurIPS hoặc OpenReview; không có entry nào viết từ trí nhớ. Không trùng key, không trùng DOI với `refs.bib`. Đã compile thử với `aamas.cls` + `ACM-Reference-Format.bst`: ra đủ 59 bibitem, không lỗi. Các cảnh báo thiếu address/publisher là bình thường, vì `refs.bib` hiện cũng có 23 cảnh báo loại này. Bốn DOI quan trọng nhất đã được kiểm lại lần hai bằng tay.

Cách dùng: chuyển những entry chọn được sang `refs.bib` (giữ một file bib duy nhất), hoặc thêm `\bibliography{refs,refs_candidates}`. Entry không được cite thì không hiện trong PDF.

### 7.1 ⚠️ Double-blind và bài của chính nhóm

- **`pham2026humans`** (arXiv 2608.01193, *Humans Are More Diverse: Frontier LLMs Show Extreme Policies in Idealised AI Development Races*; Pham, Dao Sy, **Huynh**, …, Tran, …, Han). Bài này có **thiết kế rất gần paper AAMAS**: game rủi ro nhiều người chơi, audit gate (rule recall / state tracking / payoff calculation), so với benchmark EGT và dữ liệu người. Reviewer đọc cả hai bài sẽ hỏi paper AAMAS khác gì. **Bắt buộc cite, và phải nói rõ điểm khác.**
- **`huynh2026payoff`** (arXiv 2601.19082) và **`huynh2025understanding`** (arXiv 2512.07462): FAIRGAME mở rộng sang PD có scale payoff và PGG. Bài 2601.19082 cho thấy stakes càng lớn LLM càng hợp tác, **ngược** với dự đoán EGT. Kết quả này ủng hộ trực tiếp giả thuyết "post-training favours cooperation" ở Discussion.
- Luật AAMAS: **cite ở ngôi thứ ba** ("Pham et al. show…"). Không viết "our prior work", không bỏ cite để giấu danh tính.
- **Bài Interface Focus của nhóm** ("Large language models comprehend the collective-risk dilemma but do not act on its risk", accept-with-revisions 13-08-2026) dùng **cùng game và cùng chủ đề "không phản ứng với risk"**. Chưa tìm thấy bản public nào (arXiv và Crossref đều trống). Đây là việc bạn phải tự quyết, kiểm với chính sách dual-submission của AAMAS 2027 và hỏi thầy: nếu bài đó xuất bản trước hạn AAMAS thì phải cite ở ngôi thứ ba và nói rõ điểm khác (panel model khác; ở đây có thêm phép thử dominated, best response, mixed tables, selection). Nếu chưa xuất bản thì theo CFP, cite dạng ẩn danh hoặc nộp kèm cho chair.

### 7.2 Danh sách rút gọn (~16 mục) và chỗ đặt

Bài đang chạm trần 8 trang. Phần lớn citation dưới đây **gắn thêm key vào câu có sẵn** hoặc chỉ cần thêm một mệnh đề ngắn. Chỗ trống lấy từ §1 (bỏ 2 heading) và §5 (gộp Threats + Limitations).

**Nhóm thầy Han (8):**

| Key | Bài | Đặt ở đâu | Câu đề xuất |
|---|---|---|---|
| `buscemi2025fairgame` | FAIRGAME, ECAI 2025 | RW: LLMs in games | "FAIRGAME runs language-model agents through standard games to expose biases due to the model, the language and the persona~\cite{buscemi2025fairgame}." |
| `buscemi2025llms` | LLM agents trong mô hình EGT về AI regulation | RW: LLMs in games | "…and language-model agents embedded in an evolutionary model of AI regulation are less trusting than game-theoretic agents~\cite{buscemi2025llms}." |
| `pham2026humans` | AI race, audit gate | RW: đoạn "social dilemmas" (đối thủ gần nhất) | "In multi-player AI-development races, Pham et al.~\cite{pham2026humans} audit rule recall, state tracking and payoff calculation before interpreting play, and find that correct rule recall can coexist with weak expected-payoff calculation." Thêm câu khác biệt: "We add conditions in which paying is dominated, exact best responses to fixed partners, and selection over real mixed tables." |
| `huynh2026payoff` | Stakes ↑ → hợp tác ↑, ngược EGT | Discussion, *Possible causes* | "…consistent with models being more cooperative than people~\cite{mei2024turing} and cooperating more as stakes grow, against the evolutionary prediction~\cite{huynh2026payoff}." |
| `duong2026cost` | Chi phí incentive dưới quy tắc Fermi, **có collective risk game** | RW: collective risk & selection | "Finite-population models under the Fermi rule price the institutional incentives that sustain cooperation, including in the collective-risk game~\cite{duong2026cost}." |
| `han2024evolutionary` | Cơ chế tối đa hợp tác ≠ tối đa phúc lợi (JRSI 2024) | Discussion, *Consequences for design* | "Report $\mathrm{opt}(p)$…, since success can coexist with wasted money, as cooperation and welfare can diverge in evolutionary models~\cite{han2024evolutionary}." Khớp với Grok: target 100% nhưng giữ được ít tiền nhất. |
| `han2022emergent` | EGT để hiểu hành vi emergent trong MAS (AI Comm. 2022) | RW: Multiagent evaluation, câu đầu | "…and evolutionary game theory offers tools to analyse emergent behaviour in multiagent systems~\cite{han2022emergent}." |
| `hammond2025multi` | Multi-agent risks from advanced AI | Intro P1 | Gắn vào câu "agents act for people in shared settings" cùng `chan2024visibility` |

Dự phòng khi còn chỗ: `zimmaro2024emergence` (AI agent cố định trong quần thể lai người–AI, khớp với scripted partners, đặt cạnh `terrucha2024art`), `han2017evolution` (commitment trong PGG, JAAMAS, cùng hệ AAMAS), `han2018cost`, `duong2021cost`.

**Ngoài nhóm Han (8):**

| Key | Bài | Đặt ở đâu | Ghi chú |
|---|---|---|---|
| `traulsen2006stochastic` | Fermi process, fixation trong quần thể hữu hạn | §7 dòng 355, *Selection process* | **Bắt buộc**: "Under Fermi imitation~\cite{traulsen2006stochastic}…" |
| `fudenberg2006imitation` | Giới hạn đột biến hiếm → Markov chain nhúng | §7 dòng 355 | **Bắt buộc**: "We assume rare mutation~\cite{fudenberg2006imitation}…" |
| `fernandezdomingos2023egttools` | *(đã có trong refs.bib, chưa cite)* | §7 | "…and cross-check every fixation probability with EGTtools~\cite{fernandezdomingos2023egttools}." |
| `abouchakra2012evolutionary` | Chiến lược tiến hoá trong CRD: risk thấp không góp, risk cao góp fair share | RW para 1 | "…and evolved strategies in the same game contribute only when the risk is high~\cite{abouchakra2012evolutionary}." Tăng sức nặng cho câu "behaviour should move with the risk". |
| `fernandezdomingos2022delegation` | Người uỷ thác cho agent nhân tạo trong CRD → group success tăng | RW: Multiagent evaluation, cạnh `terrucha2024art` | Rất khớp chủ đề; nhóm Lenaerts, gần nhóm Han |
| `lore2024strategic` | Framing ngữ cảnh vs cấu trúc game, khác nhau theo model (Sci Rep 2024) | RW: LLMs in games | Hỗ trợ thí nghiệm neutral wording |
| `pal2026large` | 5 LLM frontier trong repeated PD: hợp tác, thường robust về tiến hoá (PNAS Nexus 2026) | RW: LLMs in games | LLM + EGT mới nhất |
| `chan2024visibility` | Agents act for people (FAccT 2024) | Intro P1 | Nguồn đã peer-review cho câu mở |

Dự phòng: `shen2025mind` (giá trị nói ra ≠ hành động, EMNLP 2025; thêm vào `\cite{fan2024can,schmied2026llms}`), `barrett2012climate`, `nowak2004emergence` (sự phụ thuộc vào N, cho N=6 vs N=30), `hu2020other` (other-play: convention của self-play gãy với partner mới, hỗ trợ trực tiếp luận điểm "self-play không đủ").

### 7.3 Không đưa vào `.bib` vì không kiểm chứng được

- "Through the Lens of Game Theory: Behavioral Biases and Incentive Sensitivity in LLMs" (Buscemi et al.) và "More at Stake: How Payoff and Language Shape LLM Agent Strategies…" (Huynh et al.): chỉ thấy trên trang lab, ghi *under review*, không có arXiv hay DOI. Bài thứ hai có thể là 2601.19082 đổi tên. Bạn là đồng tác giả nên tự xác nhận.
- Ba bài Phil. Trans. R. Soc. A 2026 trên trang lab chưa có DOI, nên `.bib` dùng bản arXiv.
- `tomasev2025virtual` (Virtual Agent Economies) vẫn là preprint. Nếu cần nguồn đã peer-review cho câu mở intro thì dùng `chan2024visibility`.
