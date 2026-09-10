# Kế hoạch nộp AAMAS 2027 — CRSD-LLM

**Viết 09-09-2026.** Mục tiêu: nộp main track AAMAS 2027 (Hà Nội, 3–7/05/2027).
Đây là kế hoạch **song song** với vòng revision Interface Focus, không thay thế nó.
Đọc [review-response.md](review-response.md) để biết trạng thái paper tạp chí.

---

## 0. TL;DR — ba điều phải quyết trước khi làm bất cứ gì

| # | Vấn đề | Khuyến nghị của tôi |
|---|---|---|
| 1 | **Trùng nộp với Interface Focus.** AAMAS cấm nộp công trình "substantially similar" với venue archival khác. Paper IF đang *accept with revisions* → coi như archival. | Paper AAMAS phải là **paper khác**: câu hỏi mới, thí nghiệm mới, ≥70% kết quả chưa từng có trong bản IF; trích bản IF như prior work ở ngôi thứ ba. Chi tiết §2. |
| 2 | **Còn 29 ngày** (abstract 01/10, paper 08/10). Không đủ để làm tất cả. | Chốt đúng **một** trục đóng góp mới (tôi đề xuất: *best-response + quần thể hỗn hợp*), rồi cắt thẳng tay phần còn lại. Chi tiết §4. |
| 3 | **Ngân sách $170/ngày × ~20 ngày ≈ $3.400 trần**, nhưng wall-clock và orchestration mới là thứ giới hạn. | Chương trình thí nghiệm đề xuất tốn **~$1.000** (kể cả 40% dự phòng chạy lại) và ~20 giờ wall-clock. Tiền KHÔNG phải nút thắt. Chi tiết §8. |

**Nếu chỉ đọc một mục:** §4 (paper nào) và §5 (chạy gì).

---

## 1. Sự thật về venue

Nguồn: [CFP AAMAS 2027](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/),
[submission instructions](https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/instructions/),
[first call trên DMANET](http://dmatheorynet.blogspot.com/2026/08/dmanet-aamas-2027-call-for-papers-first.html).

| Mốc | Ngày | Còn |
|---|---|---|
| Đăng ký tác giả | **17-09-2026** | 8 ngày |
| Nộp abstract (100–300 từ) | **01-10-2026** | 22 ngày |
| Nộp full paper | **08-10-2026** (23:59 AoE, UTC−12) | **29 ngày** |
| Rebuttal | 20–24/11/2026 | |
| Báo kết quả | 21/12/2026 | |
| Camera-ready | 25/01/2027 | |
| Hội nghị | 03–07/05/2027, Hà Nội | |

**Định dạng:** tối đa **8 trang** + số trang tài liệu tham khảo **không giới hạn**.
Bắt buộc LaTeX, template `aamas_2027_template.zip`, **không được sửa style file**.
**Double-blind.** Supplementary: 1 file zip ≤ 25MB, reviewer *không bắt buộc* đọc →
mọi thứ quyết định phải nằm trong 8 trang.

**arXiv được phép** (preprint server và workshop không proceedings không tính là archival).

**11 area, chọn area khi nộp.** Xếp theo mức phù hợp với chúng ta:

1. **GAAI — Generative and Agentic AI** ← *đề xuất chọn làm primary*
2. **SIM — Modeling and Simulation of Artificial Societies** ← secondary
3. **GTEP — Game Theory and Economic Paradigms** ← chọn nếu đẩy mạnh phần equilibrium
4. COINE — Coordination, Organizations, Institutions, Norms, Ethics (nếu làm nhánh thể chế)

**Việc phải làm ngay tuần này:** tải template, dựng skeleton 8 trang, đăng ký tác giả
trước 17/09. Đăng ký tác giả **không ràng buộc phải nộp**, nên cứ đăng ký.

---

## 2. ⛔ Ràng buộc cứng: trùng nộp với Interface Focus

Nguyên văn chính sách AAMAS 2027:

> Authors must not submit substantially similar work to AAMAS 2027 and another archival
> venue at the same time, or submit the same work elsewhere while it remains under review
> at AAMAS 2027. Violations may result in desk rejection.

**Cập nhật 09-09-2026: bản Interface Focus CHƯA nộp.** Điều này nới ràng buộc đáng kể, nhưng
không xoá nó — vì hai paper sẽ **cùng tồn tại**, và thời điểm nộp bản IF (trước hay sau 08/10)
không đổi được bản chất: nếu hai bản "substantially similar" thì bản nào nộp sau cũng vi phạm,
và bản IF nộp sau sẽ vướng chính sách công bố trùng lặp của Royal Society.

Nên kết luận không đổi: **hai paper phải khác chất**. Nhưng vì bản IF chưa khoá, ta có thêm
một quân bài mạnh — xem [§2.1](#21-vì-chưa-nộp-if-ta-được-quyền-chia-lại-vật-liệu).

Giả định làm việc: `paper/main.tex` rồi sẽ được nộp Interface Focus. Nghĩa là:

- **KHÔNG được** nộp bản rút gọn 8 trang của chính nó. Đây là desk-reject chắc chắn nếu bị phát hiện,
  và với một panel model đặc thù như thế này thì reviewer AAMAS rất dễ nhận ra khi bản IF lên online.
- **KHÔNG được** dùng lại claim trung tâm ("capability enables risk sensitivity but does not confer it")
  làm claim trung tâm của bản AAMAS.
- Bản IF sẽ được trích như prior work. Vì AAMAS double-blind mà bản IF cũng đang ẩn danh,
  trích **ngôi thứ ba**, giống cách đang xử lý `2512.07462` (xem review-response §2e).

**Đường an toàn — ba lớp:**

1. **Câu hỏi nghiên cứu khác.** IF hỏi *"LLM có tái tạo độ nhạy risk của người không?"* (machine behaviour).
   AAMAS hỏi *"LLM agent phản ứng thế nào với **agent khác** trong dilemma có rủi ro, và điều đó
   có ý nghĩa gì khi triển khai quần thể agent hỗn hợp?"* (multiagent systems).
2. **Dữ liệu chủ yếu là mới.** Kết quả trục chính của bản AAMAS (§5: E3a/E3b/E5) **chưa tồn tại**.
   Baseline null 13 model chỉ xuất hiện như **một đoạn setup + một bảng nhỏ**, có trích IF.
3. **Nói thẳng trong Related Work.** Một đoạn: *"Concurrent work [ref IF] establishes the
   single-model baseline used here; the present paper asks a different question."*
   Reviewer ghét bị giấu, không ghét overlap được khai báo.

### 2.1 Vì chưa nộp IF, ta được quyền chia lại vật liệu

Nếu bản IF đã nộp thì mọi thứ trong đó là đã khoá. Chưa nộp thì **ta chọn cái gì đi đâu**.
Một nước đi đáng cân nhắc:

**Chuyển kết quả Q8 (điểm bản lề `p*`, gemini xoay đúng EV còn gpt-5.6-sol xoay sớm một nấc)
từ bản IF sang bản AAMAS**, mở rộng thành thủ tục staircase + chỉ số CRRA (E4).

- Với bản AAMAS: nó biến đóng góp 1 từ "một quan sát" thành **một phép đo có thủ tục**,
  đúng thứ AAMAS trả điểm cao, và nó **hết trùng** với bản IF.
- Với bản IF: mất một mục kết quả, nhưng claim trung tâm ("capability enables but does not
  confer") **không dựa vào Q8** — Q8 chỉ làm sắc thêm phần "not human-like". Bản IF vẫn đứng
  vững với lưới 3 mức, và §pivot rút xuống một câu trỏ sang paper kia.
- Rủi ro: reviewer IF đã **hỏi đích danh** Q8 (mức risk trung gian). Bỏ hẳn thì mất điểm với họ.

> **Khuyến nghị:** giữ Q8 trong bản IF ở dạng **tối giản** (một bảng 5 mức, không diễn giải
> sâu về thái độ rủi ro), và đẩy **toàn bộ tầng diễn giải** — staircase, `p*` có khoảng tin cậy,
> CRRA, cell đối chứng p = 0 — sang bản AAMAS. Hai bản khi đó chia nhau rạch ròi:
> IF trả lời *"model có nhạy risk không"*, AAMAS trả lời *"nhạy đến mức nào, đo bằng cách nào,
> và khi trộn chúng với nhau thì sao"*.

Quyết định này ảnh hưởng tới việc viết cả hai paper → **chốt trước 20/09**.

---

## 3. Vì sao paper hiện tại KHÔNG hợp AAMAS

Đây không phải chê paper — nó đang là paper tốt cho *tạp chí machine-behaviour*. Nhưng đọc bằng
mắt reviewer AAMAS thì có 14 lỗ. Xếp theo mức sát thương.

### 3.1 Lỗ chí mạng (phải bịt, nếu không sẽ bị reject)

| # | Điểm yếu | Reviewer AAMAS sẽ nói gì |
|---|---|---|
| **W1** | **Đơn văn hoá (monoculture self-play).** Cả 6 ghế luôn là **cùng một model**. | *"This is not a multiagent system, it is one model talking to six copies of itself. Where is the agent interaction?"* — đây là câu giết paper ở AAMAS. |
| **W2** | **Không có giao tiếp, không có thể chế.** `agentsCommunicate` có trong config nhưng **chưa hề được cài đặt** trong engine. | *"No communication, no commitment, no sanctioning — the MAS content is thin."* Milinski còn có nhánh pledge (2011) mà paper không đụng tới. |
| **W3** | **Không có baseline agent, không có phân tích cân bằng.** Không có agent scripted nào để so, không có mô tả tập Nash của trò chơi ngưỡng có rủi ro. | *"What is the equilibrium? How far from best response are these agents? Compared to what baseline?"* Ở GTEP/GAAI đây là điều kiện cần. |
| **W4** | **Mỏ neo equal-split chưa được ablate bằng dữ liệu.** Q1 vẫn chưa chạy (đường GPU đã chết 4 lần). Prompt tự nói ra lời giải chia đều, và một số model lặp lại nó y hệt. | *"Your 'cooperation' may just be instruction-following on a supplied focal point."* Paper hiện **tự khai** điểm yếu này ở cuối intro mà không có dữ liệu phản bác. |
| **W5** | **Không có bằng chứng model *tính* EV.** Q3 (evprobe) chưa chạy. | *"You claim EV-optimal play but never test whether the model can do the comparison."* |

### 3.2 Lỗ về độ chắc (reviewer sẽ trừ điểm soundness)

| # | Điểm yếu | Cách bịt |
|---|---|---|
| **W6** | **Một prompt template duy nhất.** Toàn bộ kết luận dựa trên một cách diễn đạt. | Chạy 2 paraphrase nữa ở các cell then chốt (E6). |
| **W7** | **Một cấu hình decode duy nhất** (temperature 0.7). `r1` đã chứng minh ổn định giữa các ngày nhưng không có đối chứng temp=0. | Thêm temp=0 ở cell then chốt (E6). |
| **W8** | **SD = 0 ở 20/44 cell bậc đỉnh** → kiểm định thường vô nghĩa; n = 10 ván/cell là nhỏ. | Chuyển sang permutation/exact test, khai báo cluster theo ván, nâng rep ở cell trục chính lên 20. |
| **W9** | **Không có mức risk p = 0.** Model đóng 120 ở p = 0.1 thì có thể là "e ngại rủi ro cực đoan". Đóng 120 ở **p = 0 (không có thảm hoạ nào cả)** thì là **mù rủi ro** — không còn đường chối. | Chạy p = 0 và p = 1.0 (E-ctrl). Cell rẻ, kết quả sắc. Config `crsd_milinski_0pct_risk_*` **đã có sẵn**. |
| **W10** | **Thang capability chỉ có 1 cặp sạch** (flash-lite ↔ pro). | Chạy thang trong-họ đầy đủ (E8): luna/terra/sol, haiku↔opus, gemma-4-26b↔31b. |

### 3.3 Lỗ về khung (sửa bằng cách viết, không tốn tiền)

| # | Điểm yếu | Cách sửa |
|---|---|---|
| **W11** | **Trục ngôn ngữ EN/VN là mối quan tâm của machine behaviour, không phải của AAMAS.** Ở AAMAS nó trông như một biến lạc. | ✅ **ĐÃ QUYẾT 09-09:** bỏ hẳn khỏi bản AAMAS, chỉ chạy tiếng Anh. Trục ngôn ngữ ở lại bản Interface Focus. |
| **W12** | **Không có formalism.** Paper không có ký hiệu toán, không định nghĩa trò chơi bằng tuple, không có algorithm box. | AAMAS đọc như CS conference: cần định nghĩa hình thức + ít nhất 1 algorithm box. |
| **W13** | **Không có phần chi phí/hiệu quả.** Bao nhiêu token, bao nhiêu tiền cho mỗi mức năng lực. | Dữ liệu đã có sẵn trong log (`usage.cost`). Một bảng "performance per dollar" rất hợp gu AAMAS. |
| **W14** | **Related work thiên về EGT/behavioural, thiếu nhánh MAS.** | Bổ sung: LLM agent trong game (Akata, Fontana, Piatti/GovSim, Horton, generative agents), quần thể agent hỗn hợp, threshold public goods trong MAS. |

---

## 4. Paper AAMAS đề xuất

### 4.1 Câu chuyện

Bản IF trả lời: *model có nhạy với rủi ro không?* Câu trả lời: 11/13 không, 2/13 có, và
hai cái "có" đó cũng khác nhau.

Bản AAMAS lấy **kết quả đó làm điểm xuất phát, không phải kết luận**, và hỏi câu tiếp theo —
câu mà một người xây hệ thống multiagent thật sự cần biết:

> **Một quần thể agent gồm nhiều model khác nhau sẽ hành xử ra sao trong dilemma có rủi ro tập thể?
> Agent "duy lý" có bóc lột agent "hợp tác vô điều kiện" không? Ở tỉ lệ trộn nào thì cả nhóm sụp?
> Và có thể chế tối thiểu nào cứu được nhóm?**

Đây là câu hỏi **thuần MAS**, và nó biến điểm yếu W1 (monoculture) thành đóng góp.

### 4.2 Ba đóng góp (viết thành bullet ở cuối Introduction)

1. **Một *phép đo* thái độ rủi ro cho LLM agent, không chỉ một quan sát.**
   Thủ tục staircase thích nghi định vị điểm bản lề `p*` của từng model, quy ra chỉ số
   e ngại rủi ro (CRRA) so được giữa các model. Kèm algorithm box. *(E4)*
2. **Hàm best-response và bóc lột trong quần thể hỗn hợp.**
   (a) Đặt 1 LLM giữa 5 đối thủ scripted có chính sách biết trước → đo trực tiếp
   hàm best-response và điều kiện hoá theo đối thủ. (b) Trộn model thật với model thật,
   quét tỉ lệ k = 0…6 → đường invasion, ngưỡng sụp của nhóm, chênh lệch payoff giữa hai loại. *(E3a, E3b)*
3. **Một thể chế tối thiểu khôi phục được thành công của nhóm.** *(E5, stretch)*

### 4.3 Ba phương án title

| # | Title | Ghi chú |
|---|---|---|
| A | *Best-responding to whom? Risk attitudes and opponent-conditioning of LLM agents in collective-risk dilemmas* | An toàn, mô tả đúng nội dung |
| B | *One rational agent is enough: exploitation and collapse in mixed LLM populations under collective risk* | Đắt giá nếu E3b ra kết quả mạnh. **Chỉ dùng nếu số liệu chống được.** |
| C | *Measuring risk attitudes of LLM agents, and what happens when you mix them* | Nhấn mạnh đóng góp "phép đo" |

Khuyến nghị: viết theo A, đổi sang B nếu E3b cho ngưỡng sụp rõ ràng.

### 4.4 Bố cục 8 trang

| Mục | Trang | Nội dung |
|---|---|---|
| 1. Introduction | 1.0 | Vấn đề, gap MAS, 3 bullet đóng góp |
| 2. Related work | 0.6 | LLM trong game · quần thể agent hỗn hợp · CRSD/threshold PGG · **1 đoạn khai báo overlap với bản IF** |
| 3. Setting & formalisation | 1.0 | Tuple trò chơi, tập cân bằng theo `p`, nghiệm EV, định nghĩa loại agent, đối thủ scripted |
| 4. Measuring risk attitude | 1.0 | Algorithm box staircase, bảng `p*` + CRRA cho panel, cell đối chứng **p = 0** |
| 5. Best-response profiling | 1.4 | 1 LLM + 5 scripted; hình heatmap best-response; ai bóc lột, ai nhượng bộ |
| 6. Mixed populations | 1.6 | Quét k; đường payoff theo loại; ngưỡng sụp; welfare nhóm |
| 7. Institution (nếu kịp) | 0.8 | Pledge / hiển thị tổng tích luỹ; delta reach |
| 8. Discussion, limitations, ethics | 0.6 | Hệ quả triển khai; giới hạn; ẩn danh; reproducibility |
| Refs | ∞ | không tính trang |

Nếu §7 không kịp → giãn §5/§6 ra và ghi §7 vào future work. **Cắt §7 trước, luôn luôn.**

---

## 5. Chương trình thí nghiệm

> 🇬🇧 **QUY TẮC CHỐT 09-09-2026: mọi thí nghiệm chỉ chạy TIẾNG ANH.**
> Không chạy tiếng Việt hay ngôn ngữ nào khác trừ khi người dùng yêu cầu đích danh.
> Hệ quả: bỏ hệ số ×1.45 của tiếng Việt khỏi mọi dự toán, và **trục ngôn ngữ không xuất hiện
> trong paper AAMAS** — nó ở lại hẳn bên bản Interface Focus. Đây cũng là một cách tách hai
> paper tốt: kết quả đa ngôn ngữ (146.8 điểm, lật reach 100%→0%) là đóng góp đặc trưng của
> bản IF, để nguyên bên đó thì overlap giữa hai bản càng mỏng.

Ký hiệu ưu tiên: **P0** = không có thì không nộp · **P1** = nên có, reviewer sẽ hỏi ·
**P2** = tốt thì có, cắt được.

Đơn giá thật đo được (EN, p = 0.9, 60 lượt/ván): `gemini-3.1-pro` $0.61 · `claude-opus-5` $0.68 ·
`gpt-5.6-sol` $0.35 · `grok-4.20-reasoning` $0.13 · `grok-nr` ~$0.02 · `flash-lite` $0.022 ·
`gpt-5.4-nano` $0.007. **Hệ số:** cell p=0.1 ×1.7 · tiếng Việt ×1.45 · cả hai ×2.4.

| ID | Thí nghiệm | Trả lời điểm yếu | Quy mô | $ | Ưu tiên |
|---|---|---|---|---|---|
| **E0** | *Engineering* — model theo ghế + agent scripted + probe pledge | W1, W2, W3 | 0 ván | $0 | **P0** |
| **E1** | Ablation bỏ mỏ neo equal-split (`exp_nohint`) **trên proxy**, không dùng GPU | W4 | 6 model × 3 risk × EN × 10 rep = 180 ván | ~$75 | **P0** |
| **E2** | Probe so sánh EV (`exp_evprobe`) | W5 | 8 model × 3 risk × 10 rep = 240 ván | ~$95 | **P0** |
| **E-ctrl** | **p = 0 và p = 1.0** | W9 | 6 model × 2 risk × 10 rep = 120 ván | ~$66 | **P0** |
| **E3a** | **Best-response profiling**: 1 LLM + 5 scripted | W1, W3 | 6 model × 4 profile đối thủ × 5 risk × 10 rep = 1.200 ván (chỉ 10 lượt/ván) | ~$85 | **P0** |
| **E3b** | **Quần thể model hỗn hợp**, quét k = 0…6 | W1 | 3 cặp × 7 k × 3 risk × 10 rep = 630 ván | ~$290 | **P0** |
| **E4** | Staircase thích nghi định vị `p*` + CRRA | đóng góp 1 | 10 model × ~20 ván = 200 ván | ~$100 | **P1** |
| **E6** | Robustness: 2 paraphrase + temp 0 | W6, W7 | 4 model × 2 risk × 3 điều kiện × 10 rep = 240 ván | ~$147 | **P1** |
| **E8** | Thang capability trong-họ | W10 | 12 model × 3 risk × 10 rep = 360 ván | ~$120 | **P2** |
| **E5** | Thể chế: pledge / hiển thị tổng | W2, đóng góp 3 | 2 model × 3 thể chế × 3 risk × 10 rep = 180 ván | ~$130 | **P2 (stretch)** |
| **E7** | Baseline scripted + phân tích cân bằng | W3 | 0 ván (chạy offline) | **$0** | **P0** |

**Tổng: ~3.200 ván, ~$1.008.** Cộng 40% dự phòng chạy lại → **~$1.400**.

> ⚠️ **Bảng trên là dự toán CŨ, viết cho panel rộng 6–12 model. KHÔNG còn hiệu lực.**
> Panel đã khoá ở **5 model** (§5.0), nên mọi cột "Quy mô" phải quy về 5 model đó và tổng
> thật là **$83**, không phải $1.400. Giữ bảng này lại chỉ để tham chiếu khi nào người dùng
> duyệt mở rộng panel. **Đừng lấy nó làm kế hoạch chạy.**

### 5.0 Panel — KHOÁ ở 5 model, CHỐT 09-09-2026

> 🔒 **QUY TẮC KHOÁ PANEL.** Chỉ chạy đúng 5 model trong bảng dưới. **Muốn thêm bất kỳ model
> nào — kể cả `gemini-3.1-pro` mà tôi khuyến nghị ở §5.0.2, kể cả để "kiểm tra nhanh" — phải
> HỎI người dùng trước.** Không tự ý mở rộng panel, không tự ý thay model đã chết bằng model
> khác. Mọi con số quy mô ở bảng §5 bên trên (viết cho panel 6/8/12 model) **đều phải quy về
> panel 5 model này** cho tới khi người dùng duyệt mở rộng.

Người dùng chọn chạy **một model mỗi nhà cung cấp**, tất cả ở bậc rẻ:

**Cả 5 đã probe server-side 09-09-2026 — SỐNG HẾT.**

| Slug | Nhà | Probe 09-09 | $/ván | Đã có data? |
|---|---|---|---|---|
| `qwen3-235b-a22b-instruct-2507` | Alibaba | ✅ OK | 0,019 | ❌ chưa |
| `grok-4.20-0309-non-reasoning` | xAI | ✅ OK | **0,023 đo thật** | ✅ 60 ván baseline |
| `gemini-3.5-flash-lite` | Google | ✅ OK | 0,034 | ❌ chưa |
| `gpt-5.6-luna` | OpenAI | ✅ OK | 0,073 | ❌ chưa |
| `claude-haiku-4-5-20251001` | Anthropic | ✅ OK | 0,125 | ❌ chỉ 1 ván smoke |

Tổng **$0,274 cho một ván chạy trên cả 5 model.**

**`qwen3-235b` sống lại là tin tốt thật:** ngày 12-08 nó 503 cả hai proxy, ngày 09-09 chạy
bình thường. Panel giờ có **5 nhà cung cấp gồm cả một lab Trung Quốc** — trước đó nhánh
frontier chỉ có 4 nhà phương Tây, và đó là một lỗ hổng coverage mà reviewer hay chỉ ra.

#### 5.0.1 Chi phí — panel này rẻ gấp 4 lần dự toán ban đầu

**Chỉ tiếng Anh** (quy tắc đầu §5) — bỏ hết cột tiếng Việt khỏi mọi bước.

| Bước | Quy mô (EN only) | $ |
|---|---|---|
| Baseline sweep (khoá join với mọi thứ khác) | 3 risk × 10 rep = 30 ván/model, **chỉ 4 model** — `grok-nr` đã có sẵn 30 ván EN (§5.0.3) | 10 |
| E1 ablation mỏ neo | 30 ván/model | 11 |
| E-ctrl p = 0 | 10 ván/model | 5 |
| E2 probe EV (5 rep) | 15 ván/model | 7 |
| E3a best-response | 200 ván/model (chỉ 1/6 ghế gọi API) | 13 |
| E3b một cặp trong panel | 210 ván | 13 |
| E7 baseline scripted + equilibrium | offline | 0 |
| | **Cộng** | **59** |
| | +40% dự phòng | 24 |
| | **Tổng Core** | **~$83** |

**$83 thay vì $450**, tính trên giá probe thật ngày 09-09 chứ không phải ước tính cũ.
Chỉ tiếng Anh vừa rẻ hơn vừa **cắt một nửa số shard phải điều phối** — wall-clock mới là
nút thắt thật. Toàn bộ Core gọn trong **nửa ngày credit**, còn thừa $87 trong ngày để thêm
`gemini-3.1-pro` ngay lập tức.

#### 5.0.2 ⚠️ Một cảnh báo phải nói trước khi chạy

**Cả 5 model đều ở bậc rẻ, mà bậc rẻ CHƯA BAO GIỜ nhạy với risk** trong toàn bộ dữ liệu
đã có: `gemini-3.1-flash-lite` −1,8 · `gpt-5.4-nano` +7,5 · `grok-4.20-non-reasoning` +23,6
(và cái +23,6 này là nới biên an toàn, không phải quyết định). Dự đoán: **trục risk sẽ null
sạch trên cả panel.**

Với **E3a thì không sao** — thậm chí còn tốt: *"model bậc rẻ không best-respond ngay cả khi
best response là hiển nhiên (profile `carry`)"* là một claim sạch và mạnh.

Nhưng **E3b thì hỏng**: nó cần tương phản giữa **một loại EV-optimal** và **một loại hợp tác
vô điều kiện**. Panel này không có loại nào EV-optimal → đường invasion sẽ phẳng, không có
ngưỡng sụp, mất luôn kết quả headline.

> ❓ **CÂU HỎI MỞ, CHỜ NGƯỜI DÙNG DUYỆT — đừng tự chạy.**
> Đề xuất thêm đúng một model đắt làm đối cực: **`gemini-3.1-pro-preview`**, model
> EV-optimal **duy nhất còn lại** sau khi `gpt-5.6-sol` bị gỡ khỏi catalog 09-09
> (xem [model-availability.md](model-availability.md)). Chi phí: E3a $28 + một cặp E3b $97.
> **Nếu không có nó, §6 (quần thể hỗn hợp) mất kết quả headline** và paper phải dựa hoàn
> toàn vào §5 (best-response).
>
> Đây là quyết định của người dùng, không phải của tôi. Panel vẫn khoá ở 5 model cho tới
> khi có câu trả lời. Hạn nên chốt: **cùng lúc với kết quả E3a**, vì lúc đó mới biết §5
> mạnh tới đâu và §6 có thật sự cần thiết không.

Chạy panel 5 model rẻ trước vẫn đúng dù quyết thế nào — nó thông đường ống, kiểm engine trộn
model, và chỉ tốn $83. Kết quả E3a của nó là dữ liệu để quyết có cần model thứ 6 hay không.

#### 5.0.3 Dữ liệu cũ: cái gì dùng lại được, cái gì không

Kiểm kê thật ngày 10-09-2026. **Kế hoạch KHÔNG chạy lại bất cứ thứ gì đã có** — nhưng cũng
phủ được rất ít, vì panel mới gần như không giao với panel cũ.

**✅ Dùng lại được ngay, miễn phí:**

| Tài sản | Quy mô | Dùng vào đâu |
|---|---|---|
| `grok-4.20-non-reasoning` baseline **tiếng Anh** | **30 ván** (3 risk × 10 rep) | **Đúng bằng toàn bộ bước "Baseline sweep" của model này.** 1/5 bước đó đã xong — **đừng chạy lại** |
| 13 model × 1.150+ ván (7 open-weight + 6 frontier) | toàn bộ `results/` | Bảng tham chiếu trong paper; cơ sở phân loại "type" biện minh cho thiết kế E3b |
| `exp_persona` 420 ván × 3 model + 210 ván nano | 1.470 ván | **Phương án C dự phòng cho E3b** nếu engine trộn model hỏng |
| Script phân tích `paper/revision/r1`–`r7` | — | Chạy lại được trên data mới, không phải viết lại |
| E7 (baseline scripted + equilibrium) | — | Offline, không cần data nào |

**❌ Không phủ được, phải chạy lần đầu (không phải "chạy lại"):**

- **4/5 model trong panel chưa có một ván nào**: `qwen3-235b`, `gemini-3.5-flash-lite`,
  `gpt-5.6-luna`, `claude-haiku-4-5`.
- **E3a, E3b, E1, E2, E-ctrl chưa từng chạy trên bất kỳ model nào.** Đây là thí nghiệm mới
  hoàn toàn, không có gì để tái sử dụng.
- **Một nửa dữ liệu cũ là tiếng Việt** → đóng băng, để nguyên cho bản Interface Focus.
- **7 model open-weight không chạy thêm được nữa** (đường GPU chết 4 lần) → chỉ còn giá trị
  lịch sử, không mở rộng được.
- **`gpt-5.6-sol` 80 ván**: dữ liệu vẫn tốt, nhưng model đã bị gỡ khỏi catalog → không thêm
  được ván nào.

> ⚠️ **Sửa vào bước Baseline sweep ở §5.0.1:** chỉ chạy **4 model**, không phải 5.
> `grok-4.20-non-reasoning` đã có đủ 30 ván EN. Chạy lại là đốt tiền và tạo ra hai tập số
> hơi khác nhau cho cùng một cell — phiền hơn là tốn. Nên chạy **1 ván đối chiếu** để xác
> nhận engine/prompt chưa trôi, rồi dùng lại 30 ván cũ.

**Câu trả lời ngắn cho "có chạy lại từ đầu không":** không. Nhưng dữ liệu cũ đắt tiền ($110
cho panel bậc đỉnh) **hầu như không đỡ được gì cho panel mới**, vì panel mới toàn model khác.
Bù lại, panel mới rẻ tới mức chạy mới toàn bộ cũng chỉ **$83** — rẻ hơn số tiền đã tiêu cho
dữ liệu cũ. Nên đây không phải mất mát, chỉ là hai tập dữ liệu phục vụ hai paper khác nhau.

### 5.1 E3a là thí nghiệm quan trọng nhất — và nó rẻ bất ngờ

Đặt **1 agent LLM giữa 5 đối thủ scripted**. Bốn profile đối thủ:

| Profile | Chính sách | Best response của LLM (nếu duy lý) |
|---|---|---|
| `all_defect` | luôn 0 | không thể đạt target một mình → **bỏ mặc** ở mọi `p` |
| `all_coop` | luôn 2 (nhóm đạt 100 mà không có mình) | góp đúng 20 ở `p` cao, **free-ride** ở `p` thấp |
| `carry` | luôn 4 (nhóm đạt 200 không cần mình) | **luôn góp 0** — target đã chắc chắn đạt |
| `conditional` | khớp trung bình vòng trước | có ảnh hưởng, đáng để đầu tư |

**Vì sao thí nghiệm này mạnh:**

- Nó biến "LLM có duy lý không" thành câu hỏi **kiểm chứng được từng ô**: ta biết chính xác
  best response ở mỗi ô, nên đo được **khoảng cách tới best response** thành một con số.
- Profile `carry` là bẫy sắc nhất trong cả thiết kế: nhóm đã đạt 200 mà không cần mình,
  **góp thêm một xu nào cũng là lỗ thuần**. Model nào vẫn góp 2 mỗi vòng ở đây là **không hề
  chơi game** — nó đang tuân theo hướng dẫn trong prompt. Đây là bằng chứng cho W4 mạnh hơn cả
  ablation E1, và nó tách hẳn "hợp tác" khỏi "tuân lệnh".
- **Chỉ 1/6 số ghế gọi API** → 10 lượt/ván thay vì 60 → **rẻ gấp 6 lần**. 1.200 ván mà chỉ ~$85.
- Không cần multi-client → **không phụ thuộc rủi ro kỹ thuật của E3b** (xem §9).

### 5.2 E3b — rủi ro kỹ thuật phải pilot trong 48h đầu

Task server hiện dùng `load_default_model()`, tức **một model cho cả run**, chọn bằng
`kaggle b t run -m <slug>`. Nhóm hỗn hợp cần **mỗi ghế một slug khác nhau trong cùng một run**.

Về nguyên tắc làm được: proxy là OpenAI-compatible, slug nằm trong **body** (`{"model": "..."}`),
nên POST thẳng tới `<MODEL_PROXY_URL>/openapi/chat/completions` với slug tuỳ ý là đủ.
**Nhưng chưa ai kiểm proxy production có chấp nhận slug ≠ model đã chọn hay không.**

> **Việc đầu tiên phải làm, ngày 1:** một shard 1 ván, 6 ghế 2 slug khác nhau. Nếu proxy từ chối
> → chuyển ngay sang phương án B, đừng đốt thời gian sửa.

**~~Phương án B~~ — ĐÃ BỎ (10-09-2026).** Trước đây định dùng **local staging proxy** (nhận slug
trong body chắc chắn, phục vụ 6 model, trộn được `gemini-3.1-flash-lite` × `gpt-5.4-nano` ×
`gemini-3.6-flash`). Nhưng quy ước mới là **chỉ chạy server-side, không sinh data ở local**
(xem [CLAUDE.md](../CLAUDE.md#-kaggle-benchmarks-chỉ-chạy-server-side-không-chạy-local)) — data
local chỉ có 6/38 model nên không so sánh được với phần còn lại của panel. Nếu proxy chặn thì
nhảy thẳng sang phương án C, hoặc hỏi người dùng trước khi mở lại đường local.

**Phương án C:** thay "loại model" bằng **"loại persona"** — đã chạy rồi, đã có 420 ván/model.
Yếu nhất vì trùng với bản IF. Chỉ dùng làm phao.

**E3a không dính rủi ro này** → đó là lý do E3a phải chạy trước E3b.

### 5.3 E4 — staircase, thủ tục cụ thể

```
Input: model M, khoảng [0, 1], n_probe = 5 ván/điểm
1. Đo tại p ∈ {0.0, 0.5, 1.0}. Nếu reach không đổi trên cả ba → báo "không có bản lề", dừng.
2. Xác định khoảng [lo, hi] mà reach đổi từ 0% sang 100%.
3. Lặp 3 lần: p_mid = (lo+hi)/2; đo n_probe ván; thu hẹp khoảng.
4. Trả về p* = trung điểm khoảng cuối, độ rộng khoảng = độ bất định.
5. Quy ra CRRA: giải u(20) = (1-p*)·u(40), u(x) = x^(1-γ)/(1-γ).
```

~20 ván/model, độ phân giải cuối ~0.06. **Đây là thứ biến quan sát thành phép đo**, và là
đóng góp dễ bảo vệ nhất trước câu hỏi *"cái này khác gì một bài benchmark?"*

### 5.4 E7 — miễn phí, nhưng làm tăng điểm soundness nhiều nhất

Chạy hoàn toàn offline, không gọi API:

- Cài 5 chính sách scripted (`always_0`, `always_2`, `always_4`, `ev_maximiser`, `conditional`)
  chạy qua **đúng engine đó** → đường tham chiếu cho mọi hình.
- Chính sách "người": lấy phân phối đóng góp từ Milinski 2008 (đã có trong paper) → đường "human-like".
- Mục §3: đặc trưng hoá tập cân bằng của trò chơi ngưỡng 10 vòng có rủi ro `p`.
  Ít nhất phải nói được: (i) mọi profile đạt đúng target là Nash khi `p` đủ lớn,
  (ii) "tất cả bỏ mặc" là Nash với mọi `p` (không ai một mình cứu được nhóm),
  (iii) nghiệm EV không phải cân bằng mà là **mốc chuẩn tắc** — đúng như bản IF đã nói.

---

## 6. Việc engineering (E0) — làm trước, chặn mọi thứ khác

| # | Việc | File | Ước lượng |
|---|---|---|---|
| 1 | **Model theo ghế.** Thêm `modelsPerSeat` vào config; viết `send_batch` định tuyến: phân hoạch danh sách prompt phẳng theo model, gọi từng backend, ghép lại **đúng thứ tự**. | `crsd/runner/batch.py`, `crsd/runner/run_experiment.py`, `crsd/models/factory.py` | 1 ngày |
| 2 | **Agent scripted.** Backend giả trả contribution theo chính sách, dùng chung interface `send_batch` → không phải sửa engine. | `crsd/models/scripted.py` (mới) | 0.5 ngày |
| 3 | **Task server hỗ trợ nhóm hỗn hợp.** Dựng nhiều client, mỗi client một slug, POST thẳng với slug trong body. | `kaggle/benchmarks/crg_task_server.py` | 0.5 ngày |
| 4 | **Pledge round (chỉ nếu làm E5).** Cài `agentsCommunicate`: mỗi vòng thêm 1 lượt gọi sinh 1 câu cam kết công khai, chèn vào prompt vòng sau. | `crsd/engine/round.py`, `crsd/engine/prompt.py` | 1 ngày |
| 5 | **Script phân tích cho E1/E2.** review-response §0.4 ghi rõ: *"Chưa có script cho hai việc đó — phải viết."* | `paper/revision/` hoặc `analysis/` | 0.5 ngày |
| 6 | Unit test cho 1–4 | `crsd/tests/` | 0.5 ngày |

**Tổng ~4 ngày công.** Đây là đường găng — bắt đầu ngay hôm nay.

⚠️ **Ràng buộc bắt buộc:** đừng đổi tên ba game config cũ (`crsd_milinski_{low,medium,high}_risk`) —
chúng là khoá join với nhánh open-weight và `results/` đã có dữ liệu mang tên đó
(bẫy đã vấp một lần ở Q8).

---

## 7. Lịch 29 ngày

| Ngày | Việc | Đầu ra |
|---|---|---|
| **09–11/09** | E0 mục 1–3 + 6. **Pilot E3b 1 ván** (chốt rủi ro multi-slug). Probe lại 38 slug (`probe_all_models.py`) → chốt panel. | Engine trộn model chạy được, panel chốt |
| **12–13/09** | E7 (baseline scripted + mục equilibrium — viết luôn §3 của paper). Phóng **E1 + E-ctrl** (batch 1). | §3 xong, 300 ván |
| **14–16/09** | Phóng **E3a** (batch 2, 1.200 ván nhưng rẻ và nhanh). Viết §4 methods. **Đăng ký tác giả 17/09.** | Dữ liệu best-response |
| **17–19/09** | Phân tích E3a → hình heatmap best-response. Phóng **E2 + E4** (batch 3). | §5 có hình |
| **20–23/09** | Phóng **E3b** (batch 4, đắt nhất). Viết §5. | Dữ liệu quần thể hỗn hợp |
| **24–26/09** | Phân tích E3b → đường invasion + ngưỡng sụp. Viết §6. **Chốt title.** | §6 có hình |
| **27–30/09** | Phóng **E6** (batch 5). Viết §1, §2, §8. **Viết abstract.** | Draft đủ 8 trang |
| **01/10** | ⚠️ **Nộp abstract (100–300 từ).** | |
| **01–04/10** | E5 nếu còn thời gian, nếu không thì E8. Siết 8 trang, làm supplementary zip. | |
| **05–07/10** | Đọc soát toàn bộ, kiểm ẩn danh, kiểm reference, kiểm mọi con số trong text khớp bảng. | |
| **08/10** | ⚠️ **Nộp paper.** Nộp sớm 12h, đừng chờ AoE. | |

**Điểm quyết định (go/no-go) 26/09:** nếu E3b không cho kết quả dùng được, chuyển sang paper
chỉ dựa trên E3a + E4 + E1/E2 (vẫn đủ 8 trang, vẫn là paper AAMAS hợp lệ), và ghi E3b vào future work.

---

## 8. Ngân sách

Trần $170/ngày = 16 account sống × $10/account/ngày (bỏ `trnnguynchis`, chưa verify SĐT).

### 8.1 $1.400 đó là tiền gì — bóc từng đồng

Cách tính: **giá một ván = tổng giá/ván của các model trong panel × hệ số cell.**
Panel 6 model bậc đỉnh, giá/ván đo thật ở cell EN/p=0.9:

`gemini-3.1-pro` $0.61 + `claude-opus-5` $0.68 + `gpt-5.6-sol` $0.35 + `grok-r` $0.13 +
`grok-nr` $0.02 + `flash-lite` $0.02 = **$1.81 cho một ván chạy trên cả 6 model**.

Hệ số cell (đo thật trên opus-5): p=0.1 ×1.7 · p=0 ước ×1.8 · tiếng Việt ×1.45.

| ID | Phép tính | $ | % |
|---|---|---|---|
| **E3b** quần thể hỗn hợp | 210 ô (k,risk,rep) × $1.20 (tổng 3 cặp) × 1.25 | **315** | 30% |
| **E6** robustness | 60 ván/model × $1.77 (4 model) × 1.35 | **143** | 14% |
| **E5** thể chế *(stretch)* | 90 ô × $0.74 (2 model) × **2** (pledge nhân đôi lượt gọi) × 1.25 | **150** | 14% |
| **E2** probe EV | 30 ván/model × $1.84 (8 model) × 1.3 risk × **1.3 probe** | **93** | 9% |
| **E3a** best-response | 200 ván/model × **$1.81 ÷ 6** × 1.4 | **85** | 8% |
| **E1** ablation mỏ neo | 30 ván/model × $1.81 × 1.3 | **71** | 7% |
| **E-ctrl** p = 0 và p = 1.0 | 20 ván/model × $1.81 × 1.8 | **65** | 6% |
| **E4** staircase | 20 ván/model × $2.08 (10 model) × 1.5 | **65** | 6% |
| **E8** thang capability | 30 ván/model × $0.70 (12 model rẻ) × 1.3 | **50** | 5% |
| **E7** baseline scripted + equilibrium | chạy offline, 0 lượt gọi API | **0** | 0% |
| | **Cộng** | **1.037** | |
| | Dự phòng chạy lại 40% | 415 | |
| | **Tổng** | **~1.450** | |

**Vì sao gấp 10 lần cái $110 đã tiêu cho panel bậc đỉnh?** Không phải vì model đắt hơn —
mà vì **số ván**. Panel bậc đỉnh cũ = 360 ván. Chương trình này = **~3.200 ván**, gấp 9 lần.
Đơn giá/ván gần như y hệt. Nói cách khác: $1.400 mua **9× lượng dữ liệu**, không mua gì sang hơn.

**Độ tin của con số:** giá của 4 model đắt (chiếm ~85% chi phí) là **đo thật** trên 37 shard
đã chạy. Giá của model rẻ lấy từ [model-availability.md](model-availability.md), file đó tự
khai sai số **±3×** — nhưng chúng chỉ chiếm ~5% nên không lệch tổng. Sai số thực tế của
tổng: khoảng **±30%**.

### 8.2 Ba mức ngân sách — chọn một

Không bắt buộc tiêu hết. Paper AAMAS hợp lệ chỉ cần **mức Core**:

| Mức | Gồm | Base | +40% dự phòng | Được gì |
|---|---|---|---|---|
| **Core** | E7 + E3a + E1 + E-ctrl(chỉ p=0) + E2(5 rep) + E3b **1 cặp** | **$320** | **$450** | Đủ 8 trang, đủ 3 đóng góp, bịt hết 5 lỗ chí mạng ở §3.1 |
| **Strong** ⭐ | Core + E3b đủ 3 cặp + E4 + E6 | **$700** | **$980** | Thêm phép đo `p*`/CRRA và chống được câu "artifact của prompt" |
| **Full** | Strong + E8 + E5 | **$1.037** | **$1.450** | Thêm thang capability và nhánh thể chế |

**Khuyến nghị: chạy Core trước (tuần 1–2), xem kết quả, rồi mới quyết lên Strong.**
E3a và E1 xong là biết paper có đứng được không. Nếu E3a ra kết quả mạnh thì nâng lên Strong
là đáng; nếu yếu thì $980 kia không cứu được gì, và nên dừng ở Core rồi dồn thời gian vào viết.

Cần **≥ 3 ngày chạy đầy tải cho Core**, ≥ 6 ngày cho Strong. Kế hoạch có 12 ngày chạy → dư
rộng ở mọi mức. **Tiền không phải nút thắt; thời gian viết mới là.**

**Nút thắt thật là orchestration:**
- `kaggle b t push` bị **từ chối im lặng** (rc=1, output rỗng, 3 giây) nếu version trước còn
  đang validate → **tối đa 3 push đồng thời**, phải chờ + retry. Dùng mô hình 2 pha của
  `stage_day_b.py`, đừng phóng kiểu Ngày A.
- Push mất ~26 phút cho 8 shard; run 8 shard × 10 ván mất ~105 phút.
- Ước tính: 5 batch × (0.5h push + 2–3h run) ≈ **20 giờ wall-clock**, chạy đêm được.

**Ba sự thật đắt tiền** (chép lại từ [README.md](README.md), đừng phát hiện lại):
1. Local (`mp-staging`) phục vụ 6/38 model, server-side phục vụ 28/38 → **503 ở local không có
   nghĩa model chết**. Hệ quả: **mọi ván phải chạy server-side**, local chỉ để probe.
2. **503 là lỗi phía Kaggle, không phải hết quota** — đã kiểm bằng 3 account cho ra cùng tập 503.
   Đổi account vô ích.
3. **Proxy đặt cọc theo `max_output_tokens`**, không theo token thực tiêu → không cap thì model
   đắt bị 403 dù thực tế tốn vài xu.

---

## 9. Sổ rủi ro

| Rủi ro | Xác suất | Ảnh hưởng | Xử lý |
|---|---|---|---|
| **Proxy từ chối slug ≠ model đã chọn** → E3b bất khả thi | Trung bình | Cao | Pilot ngày 1. Phương án C (persona) — phương án B (local proxy) đã bỏ vì quy ước chỉ-chạy-server-side. Paper vẫn đứng được nhờ E3a. |
| **Bị nghi trùng nộp với bản IF** | Thấp nếu làm đúng §2 | **Desk reject** | ≥70% kết quả mới; khai báo overlap trong Related Work; không dùng lại claim trung tâm |
| **Model chết giữa chừng** (3 lab Trung Quốc đã 503 sạch) | Cao | Trung bình | Probe lại ngày 1, **chốt panel trước 20/09**, không đổi panel sau đó |
| **Không kịp 8 trang** | Trung bình | Cao | Cắt §7 (E5) trước; sau đó dồn ngôn ngữ + comprehension xuống supplementary |
| **E3a ra kết quả null** (LLM không phản ứng với đối thủ) | Thấp | Trung bình | Null **cũng là kết quả tốt** ở đây: *"LLM agent không best-respond ngay cả khi best response là hiển nhiên"* — mạnh hơn cả kết quả dương với reviewer AAMAS |
| **Đường dẫn Windows 260 ký tự làm hỏng download** | Đã từng xảy ra | Trung bình | Dùng `redownload_all.py`; **đừng chạy lại run**, data vẫn còn trên server |
| **Tiến trình mồ côi** — TaskStop/Ctrl-C chỉ giết shell cha | Đã từng xảy ra | Trung bình | Quét `Get-CimInstance Win32_Process` trước mỗi lần phóng (lệnh ở README.md) |
| **Lưới risk mới làm chết cả loạt shard** | Đã từng xảy ra ở Q8 | Cao | E-ctrl có p = 0 và 1.0 → **chạy 1 shard 1 ván ở mức mới trước**. Pha push KHÔNG bắt được lỗi này. |

---

## 10. Checklist chống reviewer

Trước khi nộp, mỗi dòng phải trả lời được bằng một chỗ cụ thể trong paper:

- [ ] *"Đây có phải multiagent system không, hay chỉ là một model tự nói chuyện với chính nó?"* → §5, §6
- [ ] *"Cân bằng của trò chơi là gì?"* → §3
- [ ] *"So với baseline nào?"* → E7, 5 chính sách scripted trên mọi hình
- [ ] *"Hợp tác hay chỉ là tuân theo focal point prompt đã cho?"* → E1 + profile `carry` của E3a
- [ ] *"Model có thật sự tính EV không?"* → E2
- [ ] *"Có phải artifact của prompt/decoding không?"* → E6
- [ ] *"n = 10 ván có đủ không?"* → nâng lên 20 ở cell trục chính, permutation test, khai báo cluster
- [ ] *"Có tái lập được không?"* → repo ẩn danh + prompt + seed + config trong supplementary
- [ ] *"Khác gì paper [ref IF]?"* → một đoạn tường minh trong Related Work
- [ ] Kiểm ẩn danh: không tên tác giả, không tên account Kaggle, không link repo lộ danh tính,
      trích `2512.07462` và bản IF ở **ngôi thứ ba**
- [ ] Mọi con số trong text khớp bảng (sinh bảng bằng script `\input`, như `tab_effects.tex` đang làm)

---

## 11. Cần bạn quyết

1. ✅ **Hướng paper — CHỐT 09-09-2026:** best-response + quần thể hỗn hợp (§4).
2. ✅ **Bản Interface Focus CHƯA nộp** (09-09-2026) → mở ra quyền chia lại vật liệu, xem [§2.1](#21-vì-chưa-nộp-if-ta-được-quyền-chia-lại-vật-liệu).
   **Còn phải quyết:** Q8 để ở bản IF hay chuyển sang AAMAS. Hạn chốt 20/09.
3. ✅ **Panel KHOÁ ở 5 model** (09-09-2026), chỉ tiếng Anh, **Core $83**. Mọi mở rộng phải hỏi.
   Ba mức ngân sách cũ ở [§8.2](#82-ba-mức-ngân-sách--chọn-một) chỉ còn giá trị tham chiếu.
   **Còn phải quyết:** có thêm `gemini-3.1-pro` làm đối cực EV-optimal không ([§5.0.2](#502--một-cảnh-báo-phải-nói-trước-khi-chạy)) — nên quyết cùng lúc với kết quả E3a.
4. **E5 (pledge/thể chế) có làm không?** Thêm ~1 ngày code + $130. Tôi khuyên: **để stretch**,
   quyết lại vào 01/10.
5. **Ai viết?** Nếu tôi viết draft thì cần bạn chốt title + abstract trước 25/09 để còn kịp
   nộp abstract 01/10.

---

## 12. Việc làm ngay hôm nay

```bash
# 1) Panel còn sống không — probe lại 38 slug
python plan/scripts/probe_all_models.py

# 2) Quét tiến trình mồ côi trước khi phóng bất cứ gì
#    (PowerShell — lệnh đầy đủ ở plan/README.md)

# 3) Tải template AAMAS 2027, dựng skeleton 8 trang trong paper/aamas/
```

Và ba việc không cần chạy gì: tải template, đăng ký tác giả (hạn 17/09), viết §3 (formalisation
+ equilibrium) — mục này **không phụ thuộc dữ liệu nào cả** nên viết được ngay.
