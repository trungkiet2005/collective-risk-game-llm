# Kế hoạch nộp AAMAS 2027 — CRSD-LLM

**Viết 09-09-2026, gộp một mối 10-09-2026.** Đây là **file kế hoạch DUY NHẤT** của nhánh
AAMAS: vừa "viết paper gì" (Phần I) vừa "chạy cái gì, ngày nào" (Phần II) vừa "kiểm gì
trước khi nộp" (Phần III). Trước đó nội dung nằm ở hai file và **số liệu mâu thuẫn nhau**
(ngân sách $1.400 vs $457, panel 6–12 model vs 5 model, hai cái lịch khác nhau) — đã gộp
để mỗi con số chỉ sống ở đúng một chỗ.

- Deadline: **abstract 01-10-2026**, **full paper 08-10-2026** (23:59 AoE), đăng ký tác
  giả **17-09-2026**. Hôm nay 10-09 → còn **28 ngày**.
- Data cũ ở `Legacy_Results/` = **đóng băng**, không đọc, không trộn. Vòng này chạy lại
  toàn bộ vào `results/`.

---

## 0. TL;DR — sáu điều phải đọc

| # | Điều | Chi tiết |
|---|---|---|
| 1 | **Paper AAMAS phải KHÁC paper Interface Focus.** Câu hỏi mới, ≥70% kết quả chưa từng có ở bản IF, trích bản IF ở ngôi thứ ba. Vi phạm = desk reject. | §2 |
| 2 | **Hướng đã chốt:** best-response + quần thể hỗn hợp. Biến điểm yếu "monoculture self-play" thành đóng góp. | §4 |
| 3 | **Bạn KHÔNG tiêu hết được $160/ngày với panel này.** Cả chương trình tốn ~$210, trải 28 ngày = ~$8/ngày, đỉnh $49. Nút thắt là wall-clock và orchestration, không phải tiền. | §6 |
| 4 | ⚖️ **Luật cân bằng:** cả 5 model chạy **đúng cùng số ván** ở mọi thí nghiệm. Giá chỉ được quyết định *cách chia shard*, không bao giờ quyết định *n*. Có cổng QA chặn. | §7 |
| 5 | 🇬🇧 **Chỉ tiếng Anh.** Ba chỗ mặc định `en,vn` trong code đã lật về `en` ngày 10/09 — quên một cờ là ra data tiếng Việt. | §5.1 |
| 6 | **Đường găng là E0 (engineering), không phải tiền.** Model-theo-ghế + agent scripted + writer CSV chặn mọi thí nghiệm phía sau. | §8 |

**Nếu chỉ đọc một mục:** §11 (lịch theo ngày) và §7 (chạy thí nghiệm gì).

> 📖 **Quy ước ký hiệu.** `§N` = mục **của file kế hoạch này**. `P-N` = mục **của bài
> paper** (bố cục 8 trang ở §4.4) — ví dụ `P-5` là mục "Best-response profiling" của paper,
> không phải §5 của file này. Hai hệ thống số này từng bị lẫn khi gộp file; tách ký hiệu ra
> để đừng lẫn nữa.

---

# PHẦN I — PAPER

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
  trích **ngôi thứ ba**, giống cách đang xử lý `2512.07462`.

**Đường an toàn — ba lớp:**

1. **Câu hỏi nghiên cứu khác.** IF hỏi *"LLM có tái tạo độ nhạy risk của người không?"* (machine behaviour).
   AAMAS hỏi *"LLM agent phản ứng thế nào với **agent khác** trong dilemma có rủi ro, và điều đó
   có ý nghĩa gì khi triển khai quần thể agent hỗn hợp?"* (multiagent systems).
2. **Dữ liệu chủ yếu là mới.** Kết quả trục chính của bản AAMAS (§7: E3a/E3b/E5) **chưa tồn tại**.
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

Cột "Mục" dưới đây chính là các `P-N` được nhắc tới ở §11 (lịch viết) và §14 (checklist).

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

Nếu **P-7** không kịp → giãn **P-5**/**P-6** ra và ghi P-7 vào future work. **Cắt P-7 trước, luôn luôn.**

---

---

# PHẦN II — CHẠY

## 5. Phạm vi chạy — panel khoá 5 model, chỉ tiếng Anh

| Tag thư mục (`model_tag`) | Slug gọi proxy | Nhà | $/ván | `--max-out` |
|---|---|---|---|---|
| `anthropic-claude-haiku-4-5` | `claude-haiku-4-5-20251001` | Anthropic | 0,125 | **3000** 🚨 |
| `openai-gpt-5.6-luna` | `gpt-5.6-luna` | OpenAI | 0,073 | 6000 |
| `google-gemini-3.5-flash-lite` | `gemini-3.5-flash-lite` | Google | 0,034 | 6000 |
| `xai-grok-4.20-0309-non-reasoning` | `grok-4.20-0309-non-reasoning` | xAI | 0,023 | 3000 |
| `qwen-qwen3-235b-a22b-instruct-2507` | `qwen3-235b-a22b-instruct-2507` | Alibaba | 0,019 | 3000 |

🚨 **`claude-haiku-4-5` sinh 476/512 token mỗi quyết định — 93% cap mặc định.** Khi output
bị cắt trước dòng `CONTRIBUTION: n`, parser rơi xuống nhánh "quét mọi chữ số trong văn bản
rồi lấy số cuối thuộc {0,2,4}" và trả `parse_failed=False`. Nghĩa là **`parse_fail_rate =
0.0` vẫn xanh trong khi dữ liệu là bịa.** Mọi cổng kiểm tra sức khoẻ của repo đều dựa vào
chỉ số này → **nâng cap là việc P0 của ngày 10/09**, và nó gần như miễn phí
($0,1765 → $0,178/ván, nằm trong sai số).

**Kiểm sau mỗi run:** `usage_output_tokens / n_decisions` phải < 60% cap. Ghi số này vào
log QA hằng ngày.

> ⚠️ `gpt-5.6-luna` trả **404 "model not found" trên local staging proxy cho cả 14
> account**. Đó **không** phải model chết — nó chỉ có server-side. Đừng đọc nhầm 404 này
> thành "account hỏng" rồi đi đổi account.

### 5.1 🇬🇧 CHỈ TIẾNG ANH — và ba chỗ code từng làm rò

**Mọi ván trong vòng chạy này chỉ chạy `en`.** Không tiếng Việt, không fr/zh/ar, cho tới
khi người dùng yêu cầu đích danh. Hệ quả: **trục ngôn ngữ không xuất hiện trong paper
AAMAS** — nó ở lại hẳn bên bản Interface Focus. Đây cũng là cách tách hai paper tốt: kết
quả đa ngôn ngữ (146,8 điểm, lật reach 100% → 0%) là đóng góp đặc trưng của bản IF, để
nguyên bên đó thì overlap giữa hai bản càng mỏng.

Ngoài lý do khoa học còn lý do vận hành: **mỗi ngôn ngữ thêm vào nhân đôi số shard phải
push, run, download và merge** — mà orchestration mới là nút thắt thật của dự án này
(§6.2), không phải tiền.

#### Ba chỗ mặc định từng là `en,vn` — đã lật về `en` ngày 10-09-2026

Đây là bẫy im lặng: không cần làm gì sai, chỉ cần **quên một cờ** là ván tiếng Việt tự
sinh ra, và nó nhân đôi chi phí lẫn số shard mà không báo gì.

| File | Trước | Sau |
|---|---|---|
| `kaggle/benchmarks/crg_task_server.py:159` | `CRG_LANGS` mặc định `"en,vn"` | `"en"` |
| `plan/scripts/launch_shard.py:213` | `--langs` mặc định `"en,vn"` | `"en"` |
| `plan/scripts/merge_shards.py:34` | `EXPECTED_LANGS = {"en","vn"}` | `{"en"}` |

Chỗ thứ ba là chỗ nguy hiểm nhất theo kiểu khác: nó không sinh data thừa mà **báo động
giả** — cổng phủ-cell sẽ liệt kê hàng loạt cell `vn` "còn thiếu" cho một sweep vốn không
định chạy `vn`, và người đọc log rất dễ đi "vá" cho đủ. Giờ nó im.

⚠️ **`crsd/configs/experiment/*.json` vẫn ghi `"languages": ["en","vn","fr","zh","ar"]` —
CỐ Ý ĐỂ NGUYÊN.** Đó là bản ghi lịch sử của những gì đã chạy cho bản Interface Focus, sửa
đi là mất provenance của `Legacy_Results/`. Chúng **không ảnh hưởng** tới vòng chạy này vì
đường server-side đọc `CRG_LANGS` chứ không đọc file JSON đó. Nhưng **đừng chạy
`run_experiment.py` thẳng từ các config này** mà không set `CRG_LANGS=en`.

**Cổng kiểm:** `verify_wide.py` assert `set(df.language) == {"en"}` cho mọi file trong
`results/`. Một dòng khác `en` là exit 1.

---

## 6. Số học của $160/ngày — sự thật khó chịu

### 6.1 Credit là 21 hũ $10, không phải một hũ $210

Trần là **$10/account/24h**, và **một `kaggle b t run` không chia được qua nhiều account**.
**21 account sống × $10 = ~$210/ngày** (cập nhật 11-09-2026: thêm `kakagotto` +
`tonngohan`, cả hai sống và còn nguyên $10 — xem CLAUDE.md). Hệ quả cứng:

- **Mỗi shard phải ≤ $5** (nhắm một nửa trần, chừa chỗ cho một cú đắt bất ngờ). Đã từng
  mất 3 shard vì tin probe "còn quota" rồi đẩy shard $7.80 vào — nó vẫn 403.
- **Muốn tiêu $210 thì phải chạy ≥ 21 shard/ngày trên ≥ 21 account.** Chạy sâu trên ít
  account là cách chắc chắn nhất để **không** tiêu được credit.
- Quota là **cửa sổ trượt 24h, không reset lúc nửa đêm** (`acc5` vẫn 403 sau nửa đêm UTC).
  "Dùng không hết thì mất" đúng theo nghĩa *không tích luỹ được*, chứ không phải *mất lúc 0h*.
  Account chạy shard $7 lúc 22:00 thì tới 22:00 hôm sau mới dùng lại được.

### 6.2 Panel 5 model không đủ "đói" để ăn hết $10/account

Giá đo thật ngày 09–10/09, một ván = 6 ghế × 10 vòng = 60 lượt gọi:

| Model | $/ván | Số ván để tiêu hết $10 của MỘT account | Khả thi trong 1 ngày? |
|---|---|---|---|
| `claude-haiku-4-5-20251001` | **0,125** | 80 | ⚠️ vừa đủ căng |
| `gpt-5.6-luna` | 0,073 | 137 | ❌ không |
| `gemini-3.5-flash-lite` | 0,034 | 294 | ❌ không |
| `grok-4.20-0309-non-reasoning` | 0,023 | 435 | ❌ không |
| `qwen3-235b-a22b-instruct-2507` | 0,019 | 526 | ❌ không |
| | **Tổng 0,274/ván-panel** (1 ván chạy trên cả 5 model) | | |

Để tiêu $160 trong một ngày cần **~584 ván-panel = 2.920 ván-model = ~175.000 lượt gọi
LLM**. Với `--concurrency 4` (đo thật: nhanh 3,0×) một ván haiku mất ~104 giây, và push bị
giới hạn ~3 shard đồng thời. Throughput thật khoảng **1.000–1.200 ván-model/ngày** →
**$40–70/ngày là trần thực tế**, không phải $160.

### 6.3 Vậy nên làm gì với phần credit thừa

**Đừng cố tiêu cho hết** — tiêu bừa tạo thêm shard phải điều phối, mà orchestration mới là
thứ giết deadline. Thay vào đó, credit thừa được dùng đúng ba việc, tất cả đều **miễn phí
về mặt quyết định** vì tiền không còn là ràng buộc:

1. **~~n = 20~~ → n = 10** (người dùng chốt 10-09-2026). Trước đó tôi đề xuất n=20 vì
   reviewer AAMAS hay hỏi "n=10 có đủ không"; người dùng chọn 10. Hệ quả: câu hỏi đó
   **phải trả lời bằng thống kê chứ không bằng cỡ mẫu** — permutation/exact test thay cho
   t-test, khai báo cluster theo ván, báo khoảng tin cậy bootstrap (W8 ở §3.2).
2. **Lưới risk 7 điểm thay vì staircase thích nghi.** Kết quả Q8 cho thấy độ nhạy rủi ro
   là **đặc trưng của từng model**, và hai model "EV-optimal" bản lề ở **hai chỗ khác
   nhau** — nên quét thẳng lưới dày còn sạch hơn staircase, và rẻ hơn công code.
3. **Chạy lại là miễn phí.** Shard hỏng thì phóng lại, không phải cân nhắc.

Muốn thật sự dùng hết credit thì phải **mở panel** → xem §15, cần bạn duyệt.

---

## 7. Chương trình thí nghiệm (n = 10)

> ### ⚖️ LUẬT CÂN BẰNG — chốt 10-09-2026
>
> **Số ván của một model do THIẾT KẾ quyết định, không bao giờ do GIÁ quyết định.**
> Trong mọi thí nghiệm, cả 5 model chạy **đúng cùng một số ván, cùng một lưới cell,
> cùng số rep**. `claude-haiku-4-5` đắt gấp 6,6 lần `qwen3-235b` — điều đó **chỉ được
> phép ảnh hưởng tới cách chia shard** (§10), tuyệt đối không ảnh hưởng tới n.
>
> Vì sao đây là luật chứ không phải sở thích: nếu model đắt chạy ít ván hơn, mọi so sánh
> giữa các model đều **lẫn hiệu ứng thật với sai số lấy mẫu khác nhau**. Model đắt sẽ có
> khoảng tin cậy rộng hơn, và bất kỳ kết luận "model X ít nhạy rủi ro hơn model Y" nào
> cũng có thể chỉ là do X có ít ván hơn. Đây là loại lỗi reviewer bắt được ngay và
> **không sửa được sau khi đã chạy** — phải cân bằng từ lúc thiết kế.
>
> Cột **"ván/model"** dưới đây là cột phải kiểm: **trong mỗi hàng nó là MỘT con số duy
> nhất áp cho cả 5 model.** `verify_wide.py` kiểm bất biến này (§9.5).

| ID | Thí nghiệm | Thiết kế | **Ván/model** | Tổng ván-model | $ | Ưu tiên |
|---|---|---|---|---|---|---|
| **E0** | Engineering: model-theo-ghế, agent scripted, writer CSV mới, fix `--max-out` | smoke 1 ván/model | **1** | 5 | 3 | **P0** |
| **B** | **Lưới risk dày 11 điểm** p = 0.0 → 1.0 bước 0.1 — **440/550 ván tái dùng từ data cũ**, chỉ chạy lại qwen (§7.0) | 11 risk × 10 rep | **110** | 550 (chỉ 110 phải chạy) | **2** | **P0** |
| **E1** | Ablation bỏ mỏ neo equal-split (`exp_nohint`) | 3 risk × 10 rep | **30** | 150 | 8 | **P0** |
| **E2** | Probe so sánh EV (`exp_evprobe`) | 3 risk × 10 rep | **30** | 150 | 11 | **P0** |
| **E3a** | **Best-response**: 1 LLM + 5 scripted | 4 profile × 5 risk × 10 rep | **200** | 1.000 | 9 | **P0** |
| **E3b** | **Quần thể hỗn hợp, round-robin đủ 10 cặp** (§7.4) | 4 cặp/model × 5 k × 3 risk × 10 rep | **600** | 1.500 | 82 | **P0** |
| **E6** | Robustness: 2 paraphrase + temp 0 | 2 risk × 3 điều kiện × 10 rep | **60** | 300 | 16 | **P1** |
| **E5** | Thể chế: pledge / hiển thị tổng *(stretch)* | 3 thể chế × 3 risk × 10 rep | **90** | 450 | 49 | **P2** |
| **E7** | Baseline scripted + đặc trưng hoá cân bằng | offline | — | 0 | **0** | **P0** |
| | | | | **4.105** | **$181** | |
| | +40% dự phòng chạy lại | | | | **$254** | |

**$254 trên 28 ngày = $9/ngày trung bình**, đỉnh ~$28 vào ngày E3b. So với trần
$210/ngày: dùng **~4%**.

### 7.0 ♻️ Tái sử dụng data cũ — kiểm kê 10-09-2026

Người dùng yêu cầu kiểm `Legacy_Results/results/` xem có gì dùng lại được. **Kết quả: thí
nghiệm B gần như đã xong sẵn, và tốt hơn cả kế hoạch.**

`Legacy_Results/results/frontier/dense_grid/` chứa **lưới risk 11 điểm (0.0 → 1.0, bước
0.1), tiếng Anh, đúng config baseline** (`framing=0`, `memory=full_history`,
`persona=personas_default`) cho **cả 5 model trong panel**. Lưới 11 điểm này là **tập cha**
của lưới 7 điểm mà §7 định chạy.

| Model | Rep sạch ở CẢ 11 mức | Dùng được? |
|---|---|---|
| `google-gemini-3.5-flash-lite` | **44** | ✅ dùng thẳng (dư 34) |
| `xai-grok-4.20-0309-non-reasoning` | **31** | ✅ dùng thẳng (dư 21) |
| `openai-gpt-5.6-luna` | **27** | ✅ dùng thẳng (dư 17) |
| `anthropic-claude-haiku-4-5-20251001` | **24** | ✅ dùng thẳng (dư 14) |
| `qwen-qwen3-235b-a22b-instruct-2507` | **0** | ❌ **phải chạy lại** — xem dưới |

**Kết luận:** ở **n = 10** (chốt 10-09-2026), cả 4 model đều **thừa rep** — model ít nhất
(haiku, 24) vẫn dư 14. → **11 risk × 10 rep × 5 model = 550 ván**, trong đó **440 ván đã
có sẵn miễn phí**, chỉ phải chạy lại **110 ván qwen ≈ $2**.

Vì n=10 nằm xa dưới trần của cả 4 model, **không model nào ghim thiết kế** và data cũ còn
dư nhiều để bù nếu sau này có ván trượt cổng QA. Nếu muốn nâng n về sau: 24 là mức cao
nhất dùng được data cũ mà không phải chạy thêm gì (trừ qwen).

#### 🚨 Vì sao qwen phải chạy lại — và vì sao cổng QA của §9.5 KHÔNG bắt được

`qwen3-235b` bình thường trả lời cực ngắn (~15 ký tự, `CONTRIBUTION: 4`), trung bình **8
token/quyết định** trên cap 512. Nhìn số trung bình thì tuyệt đối an toàn. **Nhưng đuôi
phân bố thì không:** ở **0,88% số lượt**, model đột nhiên tính nhẩm dài 1.100–2.200 ký tự,
**vượt cap và bị cắt trước khi kịp viết dòng `CONTRIBUTION:`**. Bằng chứng — các lượt đó
đứt giữa câu:

> `...al failure if others don't compensate.

But you are the last to decide`
> `...ntribute at least 2, then 5×2 = 10 → target met.

Is it safe to assume`

Lúc đó parser rơi xuống nhánh quét chữ số và **nhặt một con số ra từ chính phép tính trong
đoạn suy luận** — rồi trả `parse_failed=False`. Phân bố đóng góp bịa ra được: 2 (252 lượt),
0 (154), 4 (114). Nhìn hoàn toàn hợp lý.

**Mức lây lan không phải 0,88% mà là 39,5%:** một ván có 60 quyết định, nên chỉ cần một
lượt hỏng là cả quỹ đạo ván đó sai. **391/990 ván dính.** Và vì lỗi rải đều khắp 11 mức
risk, **không còn một rep nào sạch ở cả 11 mức** — nên không cứu được bằng cách lọc.

> ⚠️ **Sửa cổng QA — hai cổng ở §9.5 và §5 đều thủng.**
> `usage_output_tokens / n_decisions < 0.6 × cap` là **trung bình**, mà qwen có trung bình
> 8/512 = 1,6% — xanh rực trong khi 39,5% số ván đã hỏng. Cổng đúng phải là **kiểm TỪNG
> LƯỢT**: mọi `raw_response` phải chứa `CONTRIBUTION:`. Đây là cổng bắt buộc, không thể
> thay bằng thống kê tổng hợp.
> ```python
> assert all(re.search(r"CONTRIBUTION\s*:", t["raw_response"], re.I) for t in turns)
> ```
> Cũng vì lý do này mà `--max-out 3000` (§5) phải đặt cho **mọi** model, kể cả model có
> trung bình token bé xíu như qwen — cap phải phủ **đuôi**, không phủ trung bình.

#### Cái gì KHÔNG tái sử dụng được

- **E1, E2, E3a, E3b, E6, E5: không có một ván nào.** `Legacy_Results/` chỉ có
  `exp_baseline`, `exp_persona` và `scripted_reference` — không có `exp_nohint`,
  `exp_evprobe`, hay bất cứ thí nghiệm dị thể nào. Đây là thí nghiệm **mới hoàn toàn**,
  chiếm $388/$393 của ngân sách.
- **7 model open-weight và `exp_persona` (gpt-5-nano):** ngoài panel → không dùng.
- **Toàn bộ data tiếng Việt:** ngoài phạm vi (§5.1).
- **`scripted_reference`** (1.680 ván) có sẵn nhưng lưới risk là {0, 0.01, 0.05, 0.1, 0.5,
  0.9, 1.0}, lệch với lưới mới. E7 chạy offline nên sinh lại còn rẻ hơn là đi khớp.

#### Liên quan tới quyết định mở panel (§15)

Nếu duyệt thêm model, một phần lưới B của chúng **đã có sẵn** (tiếng Anh, 5 mức risk
{0.1, 0.3, 0.5, 0.7, 0.9}, 10 rep): `gemini-3.1-pro-preview` 50 ván · `claude-opus-5` 50 ván ·
`grok-4.20-reasoning` 50 ván · `gpt-5.6-sol` 50 ván. Không đủ n=24 và không phủ 11 mức,
nhưng đủ để **giảm chi phí mục 1 của §15** và để pilot trước khi cam kết.

### 7.1 Bảng kiểm cân bằng — số đã verify bằng script, không phải ước lượng

Mỗi ô dưới đây là **số ván của MỘT model**. Trong mỗi hàng, cả 5 cột phải giống hệt nhau.

| Thí nghiệm | haiku | luna | flash-lite | grok-nr | qwen3-235b | Cân? |
|---|---|---|---|---|---|---|
| **B** — lưới risk 11 điểm | 110 | 110 | 110 | 110 | 110 | ✅ |
| **E1** — nohint | 30 | 30 | 30 | 30 | 30 | ✅ |
| **E2** — EV probe | 30 | 30 | 30 | 30 | 30 | ✅ |
| **E3a** — best-response (ghế LLM) | 200 | 200 | 200 | 200 | 200 | ✅ |
| **E3b** — ván có mặt ≥1 ghế | 600 | 600 | 600 | 600 | 600 | ✅ |
| **E3b** — ghế-ván (agent-games) | 1.800 | 1.800 | 1.800 | 1.800 | 1.800 | ✅ |
| **E6** — robustness | 60 | 60 | 60 | 60 | 60 | ✅ |
| **E5** — thể chế *(stretch)* | 90 | 90 | 90 | 90 | 90 | ✅ |
| **Tổng ván có mặt** | **1.120** | **1.120** | **1.120** | **1.120** | **1.120** | ✅ |
| **Chi phí thực tế** | $70 | $41 | $19 | $13 | $10 | ⬅ chênh 6,6× |

**Hàng cuối là điểm mấu chốt:** `claude-haiku-4-5` tốn gấp **6,6 lần** `qwen3-235b` cho
**đúng cùng 1.120 ván**. Đó là kết quả đúng — chênh lệch nằm hết ở cột tiền, **không có
một ván nào chênh ở cột dữ liệu**. Nếu một ngày nào đó bảng này lệch, nghĩa là có shard
model đắt chết mà chưa chạy lại, chứ không phải "thiết kế cho phép".

Với E3b, cân bằng đến từ **đối xứng của thiết kế chứ không phải canh tay**: đồ thị đầy đủ
K₅ cho mỗi model đúng 4 cặp, và tổng k trên lưới k = 1…5 bằng tổng (6−k) = 15, nên trong
mỗi cặp hai model chiếm đúng cùng số ghế. Không có cách nào lệch mà không phải do shard hỏng.

**Ba chỗ đã sửa để tuân luật cân bằng** (so với bản đầu tiên viết sáng 10/09):

| Chỗ | Trước — lệch | Sau — cân |
|---|---|---|
| **E3b** | chỉ 3 cặp → 2 model xuất hiện nhiều, 3 model xuất hiện ít hoặc không có | **round-robin đủ 10 cặp**, mỗi model có mặt ở đúng 4 cặp → 1.200 ván/model như nhau |
| **E5** | chỉ 2 model (chọn theo giá rẻ) | **cả 5 model**, 180 ván/model |
| **E2** | 10 rep, trong khi mọi exp khác 20 rep | **10 rep** — n toàn chương trình nay thống nhất ở 10 |

Tăng thêm $146 — và đó chính là chỗ nên tiêu phần credit đang bỏ phí (§6.3).

### 7.2 Vì sao B thay thế E4 (staircase) và E-ctrl

Kế hoạch cũ đề xuất staircase thích nghi để định vị điểm bản lề `p*`. Với credit dồi dào,
**quét thẳng lưới 7 điểm rẻ hơn công sức code staircase và cho kết quả sạch hơn**: bạn có
cả đường cong chứ không chỉ một điểm, và không phải bảo vệ tính đúng đắn của thủ tục thích
nghi trước reviewer. `p*` và chỉ số e ngại rủi ro (CRRA) vẫn suy ra được từ lưới bằng nội
suy — chỉ là hậu xử lý offline, $0.

Lưới 7 điểm đã bao luôn **E-ctrl** (p = 0 và p = 1.0) của kế hoạch cũ → hai thí nghiệm gộp
làm một.

⚠️ **Bẫy đã vấp ở Q8:** thêm mức risk mới làm **chết cả loạt shard** ở pha `run` (KeyError
trên mức chưa đăng ký), mà pha `push` KHÔNG bắt được lỗi này. → **Chạy 1 shard 1 ván ở mỗi
mức p mới trước khi phóng cả wave.** Đã đưa vào lịch ngày 12/09.

### 7.3 E3a — thí nghiệm quan trọng nhất, và rẻ nhất

Đặt **1 agent LLM giữa 5 đối thủ scripted**. Chỉ **1/6 ghế gọi API** → 10 lượt/ván thay vì
60 → rẻ và nhanh gấp 6 lần.

| Profile | Chính sách 5 ghế scripted | Best response của LLM nếu duy lý |
|---|---|---|
| `all_defect` | luôn 0 | không thể một mình đạt target → **bỏ mặc** ở mọi p |
| `all_coop` | luôn 2 (nhóm đạt 100 mà không cần mình) | góp đúng 20 ở p cao, **free-ride** ở p thấp |
| `carry` | luôn 4 (nhóm đạt 200 không cần mình) | **luôn góp 0** — target đã chắc chắn đạt |
| `conditional` | khớp trung bình vòng trước | có ảnh hưởng, đáng đầu tư |

Nó biến câu "LLM có duy lý không" thành câu hỏi **kiểm chứng được từng ô**: ta biết chính
xác best response ở mỗi ô, nên đo được **khoảng cách tới best response** thành một con số.

Profile `carry` là bẫy sắc nhất trong cả thiết kế: nhóm đã chắc chắn đạt target,
**góp thêm một xu nào cũng là lỗ thuần**. Model nào vẫn góp 2 mỗi vòng ở đây **không hề
đang chơi game** — nó đang tuân theo hướng dẫn trong prompt. Đây là bằng chứng cho câu hỏi
"hợp tác hay chỉ tuân lệnh?" mạnh hơn cả ablation E1, và nó **tách hẳn hai thứ đó ra**.

E3a không dính rủi ro kỹ thuật multi-slug của E3b → **phải chạy trước**.

### 7.4 E3b — round-robin đủ 10 cặp, không chọn cặp theo giá

Thiết kế: nhóm 6 ghế gồm **k agent model A + (6−k) agent model B**, quét k = 1…5
(hai đầu mút k = 0 và k = 6 là nhóm đồng nhất, lấy sẵn từ lưới B — xem bên dưới).

Bản đầu chỉ chạy **3 cặp** "chọn sau khi có kết quả E3a" — nghe hợp lý nhưng **vi phạm
luật cân bằng**: model nào lọt vào cặp thì có mấy nghìn ván, model không lọt thì có 0 ván,
và tiêu chí chọn cặp gần như chắc chắn sẽ trượt về phía model rẻ. Đã đổi thành
**round-robin đầy đủ**:

| | Số cặp | Mỗi model có mặt ở | Ván/model | Ghế-ván/model | Tổng ván |
|---|---|---|---|---|---|
| C(5,2) = **10 cặp**, k = 1…5 | 10 | **4 cặp** (như nhau cho cả 5) | **600** | **1.800** | 1.500 |

Mỗi model xuất hiện ở đúng 4 trong 10 cặp — tính chất của đồ thị đầy đủ K₅, nên
**cân bằng là tự động, không phải canh bằng tay**.

**Quét k = 1…5, KHÔNG quét k = 0…6.** Hai đầu mút là **nhóm đồng nhất** (k=0 là 6 ghế
model B, k=6 là 6 ghế model A) — chúng không phụ thuộc model đối tác, nên chạy chúng theo
từng cặp là **lặp lại đúng một ô 4 lần cho mỗi model** (20 ô thừa, đã kiểm bằng script).
Tệ hơn: các ô đó **đã có sẵn trong lưới B** ở đúng p ∈ {0.1, 0.5, 0.9}. Nên hai đầu mút
lấy thẳng từ B — **miễn phí**, và đường invasion vẫn đủ 7 điểm khi vẽ.

Bỏ hai đầu mút tiết kiệm **$33** và 600 ván trùng lặp, mà **không mất một điểm dữ liệu
nào** — cân bằng vẫn tuyệt đối (600 ván và 1.800 ghế-ván cho mỗi model, verify ở §7.1).

**Lợi ích ngoài dự tính:** cái ta thu được không còn là 3 đường invasion rời rạc mà là
**ma trận tương tác 5×5 đầy đủ** — *model nào bóc lột model nào*. Đây là kết quả mạnh hơn
hẳn và là thứ chỉ paper MAS mới làm được; nó biến **P-6** từ "ba ca nghiên cứu" thành "một
phép đo có hệ thống".

**Chi phí $82** — gấp 1,9 lần bản 3 cặp, nhưng vẫn chỉ là **nửa ngày credit**. Đây đúng
là chỗ đáng tiêu phần tiền đang bỏ phí ở §6.3.

Chi phí một cặp = 2,5 × ($/ván của A + $/ván của B) cho mỗi (risk, rep), vì tổng k trên
lưới k = 1…5 bằng 15 ghế mỗi loại, chia cho 6 ghế/ván. Cặp đắt nhất
(`haiku` × `luna`) = $0,248/bộ-k; cặp rẻ nhất (`qwen` × `grok`) = $0,053/bộ-k —
chênh 4,7×. **Chênh lệch giá này chỉ dùng để chia shard, KHÔNG dùng để chọn cặp:
cả 10 cặp đều chạy, kể cả cặp đắt nhất.**

### 7.5 E3b — rủi ro kỹ thuật, pilot trong 48h đầu

Task server hiện dùng một model cho cả run (`kaggle b t run -m <slug>`). Nhóm hỗn hợp cần
**mỗi ghế một slug khác nhau trong cùng một run**. Về nguyên tắc làm được (proxy là
OpenAI-compatible, slug nằm trong **body**), nhưng **chưa ai kiểm proxy production có chấp
nhận slug ≠ model đã chọn hay không**.

→ **Pilot ngày 11/09: 1 ván, 6 ghế, 2 slug khác nhau.** Nếu proxy từ chối thì nhảy thẳng
sang phương án C (thay "loại model" bằng "loại persona" — đã có sẵn config), **đừng đốt
thời gian sửa**. Phương án B cũ (local staging proxy) **đã bỏ** theo quy ước
chỉ-chạy-server-side.

⚠️ **Cảnh báo khoa học phải nói trước khi chạy:** cả 5 model trong panel đều ở bậc rẻ, và
bậc rẻ **chưa bao giờ nhạy với risk** trong toàn bộ dữ liệu đã có. E3b cần tương phản giữa
một loại **EV-optimal** và một loại **hợp tác vô điều kiện**; panel này có thể **không có
loại EV-optimal nào** → đường invasion phẳng, không có ngưỡng sụp, mất kết quả headline của
**P-6**. Xem §15 mục 1.

Với **E3a thì ngược lại — null cũng là kết quả tốt**: *"model không best-respond ngay cả khi
best response là hiển nhiên (profile `carry`)"* là một claim sạch và mạnh với reviewer AAMAS.

---

### 7.6 E7 — miễn phí, nhưng làm tăng điểm soundness nhiều nhất

Chạy hoàn toàn offline, không gọi API:

- Cài 5 chính sách scripted (`always_0`, `always_2`, `always_4`, `ev_maximiser`, `conditional`)
  chạy qua **đúng engine đó** → đường tham chiếu cho mọi hình.
- Chính sách "người": lấy phân phối đóng góp từ Milinski 2008 (đã có trong paper) → đường "human-like".
- **P-3**: đặc trưng hoá tập cân bằng của trò chơi ngưỡng 10 vòng có rủi ro `p`.
  Ít nhất phải nói được: (i) mọi profile đạt đúng target là Nash khi `p` đủ lớn,
  (ii) "tất cả bỏ mặc" là Nash với mọi `p` (không ai một mình cứu được nhóm),
  (iii) nghiệm EV không phải cân bằng mà là **mốc chuẩn tắc** — đúng như bản IF đã nói.

---

## 8. Việc engineering (E0) — làm trước, chặn mọi thứ khác

| # | Việc | File | Ước lượng |
|---|---|---|---|
| 1 | **Model theo ghế.** Thêm `modelsPerSeat` vào config; viết `send_batch` định tuyến: phân hoạch danh sách prompt phẳng theo model, gọi từng backend, ghép lại **đúng thứ tự**. | `crsd/runner/batch.py`, `crsd/runner/run_experiment.py`, `crsd/models/factory.py` | 1 ngày |
| 2 | **Agent scripted.** Backend giả trả contribution theo chính sách, dùng chung interface `send_batch` → không phải sửa engine. | `crsd/models/scripted.py` (mới) | 0.5 ngày |
| 3 | **Task server hỗ trợ nhóm hỗn hợp.** Dựng nhiều client, mỗi client một slug, POST thẳng với slug trong body. | `kaggle/benchmarks/crg_task_server.py` | 0.5 ngày |
| 4 | **Pledge round (chỉ nếu làm E5).** Cài `agentsCommunicate`: mỗi vòng thêm 1 lượt gọi sinh 1 câu cam kết công khai, chèn vào prompt vòng sau. | `crsd/engine/round.py`, `crsd/engine/prompt.py` | 1 ngày |
| 5 | **Script phân tích cho E1/E2.** Ghi chú vòng revision trước đã nêu rõ: *"Chưa có script cho hai việc đó — phải viết."* | `paper/revision/` hoặc `analysis/` | 0.5 ngày |
| 6 | Unit test cho 1–4 | `crsd/tests/` | 0.5 ngày |

**Tổng ~4 ngày công.** Đây là đường găng — bắt đầu ngay hôm nay.

⚠️ **Ràng buộc bắt buộc:** đừng đổi tên ba game config cũ (`crsd_milinski_{low,medium,high}_risk`) —
chúng là khoá join với nhánh open-weight và `results/` đã có dữ liệu mang tên đó
(bẫy đã vấp một lần ở Q8).

---

## 9. Định dạng CSV mới — học theo `data_fairgame_frontier_llm`

Học cách lưu của corpus prisoner's-dilemma (`agent1_strategies`, `agent1_scores`, …) nhưng
**fit với CRSD 6 agent**. Mục đích: dùng lại được code phân tích đã viết cho corpus PD, và
có một data card tự mô tả để bỏ vào supplementary.

### 9.1 Cây thư mục — CHỐT 10-09-2026

```
results/
├── DATA_CARD.md                     <- tài liệu tự mô tả + loader chạy được
├── PROVENANCE.json                  <- ván nào từ đâu ra
└── <experiment>/                    <- exp_baseline, exp_nohint, exp_bestresponse, …
    └── <p>/                         <- 0, 0.1, 0.2, … 1   (tên thư mục = con số)
        └── <model_tag>/
            └── p<p>_<lang>_<model_tag>.csv
```

Đường dẫn thật:

```
results/exp_baseline/0.9/anthropic-claude-haiku-4-5-20251001/p0.9_en_anthropic-claude-haiku-4-5-20251001.csv
results/exp_bestresponse/0.5/openai-gpt-5.6-luna/p0.5_en_openai-gpt-5.6-luna.csv
```

**Một định dạng duy nhất: wide CSV.** Bản đầu của mục này có thêm `results/raw/` (chép
long-format `games.csv` + `turns.jsonl`) và một tầng `results/wide/`; **cả hai đã bỏ**.

> ⚠️ **Đánh đổi phải biết: `results/` KHÔNG chứa reasoning và prompt.** Chúng chỉ nằm
> trong `turns.jsonl` của thư mục shard tải về (`plan/runs/…`), và `results/` **không dựng
> lại được** chúng. Muốn giữ corpus reasoning cho phân tích XAI về sau thì phải **backup
> `plan/runs/` ra ngoài git**. Đổi lại: `results/` chỉ ~1,5 KB/ván nên **track trọn vào
> git được** — 440 ván hiện tại chỉ 640 KB, so với 84 MB của bản có `raw/`.

Sinh và kiểm:

```bash
python plan/scripts/to_wide_csv.py --src plan/runs       # shard -> results/
python plan/scripts/verify_wide.py --expect-reps 10      # exit 1 neu hong
```

**Quy ước bắt buộc (chép từ bài học của corpus PD):**

- Dưới `results/<experiment>/` **chỉ được có thư mục tên là số**. Loader sắp xếp bằng
  `float(p.name)`; một file `README.md` lạc vào đó làm **vỡ cả ingest** chứ không bị bỏ
  qua. Đó là lý do `DATA_CARD.md` và `PROVENANCE.json` nằm ở gốc `results/`.
- `<p>` trong tên thư mục và trong tên file là **cùng một chuỗi literal** — `0.9` chứ không
  phải `0.90`, `1` chứ không phải `1.0`, `0` chứ không phải `0.0`.
- `<model_tag>` **lặp lại nguyên văn** trong tên file, và với thí nghiệm đồng nhất thì
  **bằng đúng giá trị trong ô `agent1_llm`**. `verify_wide.py` kiểm bất biến này.
- Thí nghiệm **dị thể** (E3a, E3b) không có một model duy nhất → `<model_tag>` thành
  `mix__<tagA>__<tagB>__k<k>` (E3b) hoặc chính là model đang được đo (E3a — các ghế
  scripted ghi rõ trong `agent{i}_llm`, vd `scripted:always_4`).

### 9.2 Schema — 82 cột

**Khối A — định danh ván & thiết kế (12 cột)**

| # | cột | dtype | miền | nghĩa |
|---|---|---|---|---|
| 1 | `game_id` | str | duy nhất trong file | định danh ván; ở data nhập lại nó mã hoá cả game config/model/lang/rep |
| 2 | `experiment` | str | `exp_baseline`, `exp_nohint`, `exp_bestresponse`, `exp_mixed`, … | tên thí nghiệm |
| 3 | `language` | str | `en` | bằng token `<lang>` trong tên file |
| 4 | `rep` | int | 0 … 19 | lần lặp — **khoá join với ô đối chứng baseline** |
| 5 | `seed` | int | | seed tái lập |
| 6 | `persona_set` | str | `personas_default`, … | file persona đã dùng |
| 7 | `persona_seats` | str | 6 ký tự, vd `NNNNNN`, `SSCCCC` | tính cách theo **ghế thực tế** sau khi hoán vị |
| 8 | `memory_mode` | str | `full_history` | |
| 9 | `opponent_profile` | str | `all_defect`/`all_coop`/`carry`/`conditional`/`""` | chỉ E3a |
| 10 | `framing` | 0/1 | | có framing khí hậu không |
| 11 | `risk_framing` | str | `lottery` / `plain` | cách nêu rủi ro |
| 12 | `show_computed_totals` | 0/1 | | prompt có đưa sẵn tổng tính trước không |

**Khối B — luật chơi (9 cột).** Giữ nguyên tên slot của FAIRGAME để schema tương thích.

| # | cột | dtype | miền | nghĩa |
|---|---|---|---|---|
| 13 | `n_players` | int | 6 | |
| 14 | `endowment` | int | 40 | |
| 15 | `contribution_options` | str | `"[0, 2, 4]"` | |
| 16 | `target` | int | 120 | |
| 17 | `risk_probability` | float | 0 … 1 | bằng `<p>` trong đường dẫn |
| 18 | `n_rounds_is_known` | bool | `True` | prompt có nói trước số vòng |
| 19 | `max_rounds` | int | 10 | |
| 20 | `played_rounds` | int | 10 | phải bằng `max_rounds`; khác đi = ván đứt |
| 21 | `agents_communicate` | bool | `False` (`True` ở E5) | có vòng pledge không |

**Khối C — kết cục nhóm (7 cột).** Phần này **không có trong corpus PD** — đặc thù CRSD.

| # | cột | dtype | miền | nghĩa |
|---|---|---|---|---|
| 22 | `group_contributions` | str→list | dài đúng 10 | tổng đóng góp cả nhóm **từng vòng** |
| 23 | `pot_cumulative` | str→list | dài đúng 10, không giảm | quỹ chung tích luỹ sau mỗi vòng |
| 24 | `group_total` | float | | `pot_cumulative[-1]` |
| 25 | `target_reached` | 0/1 | | `group_total >= target` |
| 26 | `catastrophe` | 0/1 | | kết quả xổ số cấp nhóm (chỉ xổ khi trượt target) |
| 27 | `mean_payoff` | float | | trung bình payoff 6 ghế |
| 28 | `n_parse_failures` | int | | tổng số lượt parse hỏng cả ván — **cổng QA** |

**Khối D — mỗi agent i = 1…6, 9 cột × 6 = 54 cột**

| cột | dtype | miền | nghĩa |
|---|---|---|---|
| `agent{i}_name` | str | `Player_1` … `Player_6` | định danh trong prompt |
| `agent{i}_llm` | str | slug model, hoặc `scripted:always_4` | **model/chính sách thật cầm ghế này** |
| `agent{i}_personality` | str | `neutral` / `cooperative` / `selfish` | tính cách của ghế (lấy từ `disposition`) |
| `agent{i}_knows_opponent_with_prob` | int | 0 | slot FAIRGAME, giữ để tương thích |
| `agent{i}_strategies` | str→list | dài đúng 10, phần tử ∈ {0,2,4} | **đóng góp từng vòng** ← tương ứng `agent1_strategies` của PD |
| `agent{i}_scores` | str→list | dài đúng 10, không tăng | **tài khoản riêng còn lại sau mỗi vòng** = `endowment − cumsum(strategies)` |
| `agent{i}_messages` | str→list | `[]` (câu pledge ở E5) | |
| `agent{i}_payoff` | float | | payoff cuối **sau xổ số**: `0` nếu `catastrophe`, ngược lại `scores[-1]` |
| `agent{i}_parse_failures` | int | | số vòng parse hỏng của riêng ghế này |

### 9.3 Ghi chú quan trọng về `agent{i}_scores`

Trong corpus PD, `agent1_scores[t]` là **penalty vòng t**, và nó phụ thuộc nước đi của đối
thủ nên **không** suy ra được từ `agent1_strategies`. Trong CRSD **không tồn tại payoff
theo vòng**: tiền chỉ kết toán một lần ở cuối, sau xổ số cấp nhóm.

Nên `agent{i}_scores` ở đây được định nghĩa là **tài khoản riêng còn lại sau mỗi vòng**
(`endowment − cumsum(contributions)`). Nó **là hàm tất định của `strategies`** — cố ý như
vậy, để **code loader dùng chung được với corpus PD**: cùng `ast.literal_eval`, cùng ra
list 10 số cùng đơn vị tiền, cùng vẽ được đường quỹ đạo. Phần "phụ thuộc người khác" — thứ
mà cột `scores` của PD mang — ở CRSD nằm ở **cấp nhóm**, trong `pot_cumulative`.

### 9.4 Parse các cột list

Giống PD: **Python literal dấu nháy đơn, KHÔNG phải JSON.**

```python
import ast
contribs = ast.literal_eval(row["agent1_strategies"])   # [4, 2, 0, ...]
account  = ast.literal_eval(row["agent1_scores"])       # [36, 34, 34, ...]
pot      = ast.literal_eval(row["pot_cumulative"])      # [12, 22, ...]
```

### 9.5 Bất biến phải kiểm trong QA (`verify_wide.py`)

- Mọi cột list dài **đúng 10**.
- `sum(agent{i}_strategies for i in 1..6)` từng vòng **bằng** `group_contributions`.
- `pot_cumulative == cumsum(group_contributions)`.
- `group_total == pot_cumulative[-1]`; `target_reached == (group_total >= target)`.
- `catastrophe == 0` bất cứ khi nào `target_reached == 1` (xổ số chỉ diễn ra khi trượt).
- `agent{i}_payoff == 0 if catastrophe else agent{i}_scores[-1]`.
- `n_parse_failures == 0` **và** `usage_output_tokens / n_decisions < 0.6 × max_out`
  — cổng thứ hai bắt được lỗi cắt-output mà cổng thứ nhất bỏ lọt (xem §5).
- `model_tag` trong đường dẫn khớp `agent1_llm` (chỉ với thí nghiệm đồng nhất).
- Phủ đủ cell: mọi (p, model, rep) trong thiết kế đều có đúng 1 dòng.
- 🚨 **CỔNG CẮT-OUTPUT (§7.0) — kiểm TỪNG LƯỢT, không phải trung bình:** mọi
  `raw_response` trong `turns.jsonl` phải chứa `CONTRIBUTION:`. Thiếu = quyết định
  bịa do output bị cắt, và `parse_failed` KHÔNG bắt được. Đã làm hỏng 39,5% số ván
  qwen trong data cũ. Chỉ số trung bình `usage_output_tokens / n_decisions` là cổng
  **phụ**, không thay thế được cổng này.
- 🚨 **CỔNG NGÔN NGỮ (§5.1):** `set(df.language) == {"en"}`. Một dòng khác `en` là
  exit 1 — bắt trường hợp quên `--langs` khi phóng shard.
- 🚨 **CỔNG CÂN BẰNG (§7):** trong mỗi experiment, `groupby(model).size()` phải cho ra
  **đúng một giá trị duy nhất** cho cả 5 model. Với E3b thì đếm theo số ván model đó có
  mặt (`agent{i}_llm` chứa model đó ở ít nhất một ghế) — cũng phải bằng nhau cả 5.
  Lệch một ván cũng exit 1: đây là cổng bắt việc "shard model đắt chết mà quên chạy lại",
  loại lỗi âm thầm biến chênh lệch ngân sách thành chênh lệch kết quả.

### 9.6 Việc phải code (thuộc §8)

| File | Việc |
|---|---|
| ✅ `crsd/dataio/wide_csv.py` | `game_to_wide_row()` → dict 82 cột. **Xong 10-09-2026** |
| ✅ `plan/scripts/to_wide_csv.py` | shard (`--src plan/runs`) → thẳng `results/<exp>/<p>/<model>/`. **Xong**, gộp nhiều shard, báo lỗi nếu hai run tranh cùng khoá `rep` |
| ✅ `plan/scripts/verify_wide.py` | Kiểm bất biến §9.5, exit 1 nếu hỏng. **Xong** — đã test âm tính (gài 5 lỗi, bắt cả 5) |
| ✅ `results/DATA_CARD.md` | Data card tự mô tả + loader chạy được. **Xong** |
| ✅ **Bẫy parse cắt-output** | `crg_task_server.py`: `_hit_output_cap()` + retry khi bị cắt + nâng cap ×4 (trần 8000) + ép `parse_failed` nếu không cứu được. **Xong 10-09-2026**, 5 test hồi quy. Đây là lỗi đã huỷ 39,5% ván qwen (§7.0) |
| ✅ `plan/scripts/import_legacy_b.py` | Nhập lưới risk B từ `Legacy_Results/` (§7.0). **Xong** — 440 ván (640 KB) đã vào `results/`, qua hết cổng kiểm |
| ⚠️ `plan/scripts/merge_shards.py` | **Đã bị thay thế** bởi `to_wide_csv.py` — nó ghi layout CŨ (`results/frontier/<model>/<exp>/games.csv`). Đừng dùng cho vòng chạy này |

**Không sửa** `crsd/dataio/recorder.py`, không đổi schema `games.csv` / `turns.jsonl` —
engine vẫn ghi long-format như cũ vào thư mục shard. `results/` là **phép chiếu** của
chúng, sinh lại được bất cứ lúc nào miễn là còn giữ thư mục shard.

---

## 10. Hình dạng shard chuẩn

**1 shard = 1 model × 1 cell × N ván**, luôn ≤ $5.

> ⚠️ **Bảng dưới đây KHÔNG phải số ván của model.** Nó là **kích thước gói**: model đắt
> đóng gói nhỏ hơn để mỗi shard vẫn ≤ $5. Tổng số ván thì **y hệt nhau cho cả 5 model**
> (§7) — `claude-haiku-4-5` chỉ đơn giản là cần **nhiều shard hơn** để chạy hết đúng
> chừng ấy ván. Đừng đọc "30" ở hàng haiku thành "haiku chạy ít hơn".

| Model | N ván / shard | $/shard | Số shard cho 140 ván của lưới B | Shard/account/ngày |
|---|---|---|---|---|
| `claude-haiku-4-5` | 30 | 3,75 | **5** | 2 |
| `gpt-5.6-luna` | 40 | 2,92 | **4** | 3 |
| `gemini-3.5-flash-lite` | 40 | 1,36 | **4** | 5+ |
| `grok-4.20-non-reasoning` | 40 | 0,92 | **4** | 5+ |
| `qwen3-235b` | 40 | 0,76 | **4** | 5+ |
| | | | **cùng 140 ván** | |

Cờ bắt buộc mỗi lần phóng:

```bash
python plan/scripts/launch_shard.py \
  --account <tên account> --model <slug> \
  --risk 0.9 --lang en --reps 20 \
  --max-out 3000 --concurrency 4
```

- `--concurrency 4` là **đòn bẩy wall-clock miễn phí**: song song hoá 6 ghế trong một
  vòng, output **byte-identical** với đường tuần tự, **không đổi chi phí**. Đo thật:
  626,5s → 207,5s (3,0×).
- `--max-out 3000` cho mọi model không có "reasoning hint" — xem §5.

---

## 11. Lịch theo ngày

Nhịp mỗi ngày: **sáng phóng (có người trông, vì push hay hỏng im lặng) → ngày chạy →
tối tải + merge + QA → đêm phân tích/viết.**

### Tuần 0 — Engineering (10–12/09) · ~$4

| Ngày | Chạy | $ | Viết / phân tích | Đầu ra |
|---|---|---|---|---|
| **10/09** | ✅ Probe 23 account (`probe_accounts.py`) → **19 sống**. ✅ Sửa bẫy parse cắt-output (§8). ✅ Nhập lưới B 440 ván. ✅ Phóng 4 shard qwen. | 2 | — | 19 account sống; `--max-out 3000` + retry-khi-bị-cắt đã vào code |
| **11/09** | **Pilot multi-slug: 1 ván, 6 ghế, 2 slug.** Đây là go/no-go của E3b. | 0,5 | — | Biết E3b khả thi hay phải sang phương án C |
| **12/09** | **Wave B-qwen**: chạy lại `qwen3-235b` trên **cả 11 mức risk × 10 rep** = 110 ván, ~3 shard, **`--max-out 3000`**. Bốn model kia lấy thẳng từ data cũ (§7.0) | 2 | **E7 offline**: 5 chính sách scripted + đặc trưng hoá cân bằng → **viết luôn §7 của paper** | `wide_csv.py`, `to_wide_csv.py`, `verify_wide.py`, `DATA_CARD.md`; §7 xong |

> E0 phần còn lại (`modelsPerSeat`, `crsd/models/scripted.py`, unit test) chạy song song cả
> 3 ngày. Đây là **đường găng** — mọi thứ khác chờ nó.

### Tuần 1 — Đo (13–19/09) · ~$44

| Ngày | Chạy | $ | Viết / phân tích | Đầu ra |
|---|---|---|---|---|
| **13/09** | *(trống — B đã xong)* Dùng ngày này chạy sớm **Wave E1** = 3 risk × 5 model × 10 rep | 8 | Gom 110 ván qwen mới vào `results/` (440 ván kia đã nhập 10/09), chạy `verify_wide.py` | Lưới risk đủ **550 ván** |
| **14/09** | **Wave E2** (EV probe) = 3 risk × 5 model × 10 rep | 11 | Phân tích B → **Fig 1: đường phản ứng rủi ro 11 điểm** cho 5 model | Fig 1 |
| **15/09** | Fill cell thiếu + đệm | 3 | Phân tích E1 → mỏ neo equal-split có thật là mỏ neo không | Bảng ablation |
| **16/09** | **Wave E3a-1**: profile `all_defect` + `all_coop`, 10 shard × 100 ván | 5 | Viết **P-4** (methods) | |
| **17/09** | ⚠️ **ĐĂNG KÝ TÁC GIẢ — HẠN HÔM NAY.** **Wave E3a-2**: `carry` + `conditional`, 10 shard × 100 ván | 4 | | Đã đăng ký (không ràng buộc phải nộp) |
| **18/09** | Fill cell thiếu | 3 | **Phân tích E3a → Fig 2 heatmap best-response, Fig 3 khoảng cách tới best response** | Fig 2, 3 |
| **19/09** | **Wave E3b-pilot**: 1 cặp × 1 risk × k ∈ {1…5} × 5 rep — kiểm engine trộn model chạy đúng ở mọi k | 4 | Chốt thứ tự chạy 10 cặp (chỉ là thứ tự — **cả 10 cặp đều chạy**, không chọn lọc) | Pilot xanh |

> ⚠️ **Điểm quyết định 18/09:** kết quả E3a cho biết **P-5** mạnh tới đâu, và do đó **P-6** có thật
> sự cần model đối cực EV-optimal hay không. Đây là lúc trả lời §15 mục 1.

### Tuần 2 — Quần thể hỗn hợp (20–26/09) · ~$110

E3b round-robin **đủ 10 cặp** (§7.4), mỗi cặp 5 k × 3 risk × 10 rep = 150 ván.
Chia 3 ngày, ~$28/ngày ≈ $2/account — ngày tiêu nhiều nhất của cả kế hoạch.
**Chạy đủ cả 10 cặp** — không cắt cặp đắt để tiết kiệm, đó chính là bias theo giá.

| Ngày | Chạy | $ | Viết / phân tích | Đầu ra |
|---|---|---|---|---|
| **20/09** | **Wave E3b-1**: cặp 1–4 (600 ván) — chia shard theo giá cặp, ≤$5/shard | 28 | Viết **P-5** (best-response) | P-5 nháp |
| **21/09** | **Wave E3b-2**: cặp 5–7 (450 ván) | 28 | Viết P-5 tiếp; QA wave 1 | |
| **22/09** | **Wave E3b-3**: cặp 8–10 (450 ván) | 26 | Merge + QA wave 2 | |
| **23/09** | Fill cell thiếu E3b — **chạy tới khi cổng cân bằng §9.5 xanh**, không dừng sớm vì tiếc tiền | 12 | Viết **P-3**, **P-4** hoàn chỉnh | Ma trận 5×5 đủ ô; P-3, P-4 xong |
| **24/09** | — | 0 | **Phân tích E3b → Fig 4 ma trận bóc lột 5×5, Fig 5 đường invasion + ngưỡng sụp + welfare nhóm** | Fig 4, 5 |
| **25/09** | — | 0 | Viết **P-6**. **Chốt title.** | P-6 nháp |
| **26/09** | ⚠️ **GO/NO-GO:** nếu E3b không cho kết quả dùng được → **cắt P-6**, dồn vào P-5 + B, ghi E3b vào future work. **Wave E6**: 2 risk × 3 điều kiện × 10 rep | 16 | | Quyết định ghi vào plan |

### Tuần 3 — Viết (27/09–03/10) · ~$60

| Ngày | Chạy | $ | Viết / phân tích | Đầu ra |
|---|---|---|---|---|
| **27/09** | — | 0 | Phân tích E6 → bảng robustness. Viết **P-1**, **P-2** | P-1, P-2 nháp |
| **28/09** | **Wave E5 (stretch)** — cả 5 model, 90 ván/model. Chỉ chạy nếu **P-6** đã chắc và còn thời gian; nếu không thì **bỏ HẲN cả thí nghiệm** — không chạy phiên bản rút gọn 2 model | 49 | Viết **P-7**, **P-8** | |
| **29/09** | — | 0 | **Ráp full draft 8 trang.** Kiểm tràn trang | Draft v1 |
| **30/09** | — | 0 | Viết abstract (100–300 từ). Đọc soát toàn văn | Abstract |
| **01/10** | ⚠️ **NỘP ABSTRACT** | 0 | | Đã nộp |
| **02/10** | Fill mọi cell còn thiếu, rerun shard hỏng | 8 | Siết bảng/hình | |
| **03/10** | Dự phòng chạy | 3 | Sinh lại toàn bộ bảng bằng script `\input` | |

### Tuần 4 — Nộp (04–08/10) · $0

| Ngày | Việc |
|---|---|
| **04/10** | Supplementary zip ≤ 25MB: cả cây `results/` (640 KB, thừa sức) + prompt + config + seed. Repo ẩn danh |
| **05/10** | Soát **ẩn danh**: không tên tác giả, không tên account Kaggle, không link lộ danh tính; trích bản Interface Focus ở **ngôi thứ ba** |
| **06/10** | Soát reference; **kiểm mọi con số trong text khớp bảng** (sinh bảng bằng script, không gõ tay) |
| **07/10** | Dự phòng — giả định sẽ cần |
| **08/10** | ⚠️ **NỘP PAPER.** Nộp sớm ≥ 12 tiếng, đừng chờ AoE |

**Tổng chi tiêu dự kiến: ~$210** trên 28 ngày — bằng $181 của bảng §7 cộng ~$29
đã cấp sẵn cho các ngày fill/rerun (18/09, 19/09, 23/09, 02–03/10).
Trần cấp phát trong cùng kỳ: ~$4.200. **Dùng ~12–15%.**

Ngày tiêu nhiều nhất là 28/09 (E5, $49) và 20–22/09 (E3b, ~$28/ngày ≈ $2/account) — xa trần
$10/account. **Không ngày nào bị ngân sách chặn, nên không ngày nào có cớ cắt bớt ván
của model đắt.**

---

## 12. Luật orchestration — chép ra dán lên tường

1. **Quét tiến trình mồ côi TRƯỚC mỗi lần phóng.** `TaskStop`/Ctrl-C chỉ giết shell cha;
   `launch_shard.py` con vẫn sống và vẫn push → xung đột version.
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
     Where-Object { $_.CommandLine -match 'launch_shard|launch_day|stage_day' } |
     ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
2. **Push tối đa 3 shard đồng thời, và phải chờ `status` idle.** `kaggle b t push` bị
   **từ chối im lặng** (rc=1, output RỖNG, ~3 giây) nếu version trước còn validate. Không
   có thông báo lỗi nào — rất dễ chẩn đoán nhầm thành 429/quota. Dấu hiệu phân biệt:
   **fail sau đúng ~3 giây** = bị từ chối ngay (validate thật mất vài phút).
   Bước `run` thì phóng song song thoải mái.
3. **Trần TỔNG số request đồng thời vào MỘT model: ~8.** Đo thật 10-09-2026 trên
   `qwen3-235b-a22b-instruct-2507`: 4 shard × `--concurrency 4` = **16 request đồng thời
   → bão 429 "model is currently experiencing heavy load"**, 2/4 shard chết sau 72 giây
   (6 lần backoff 2/4/8/16/30s đều 429). Ngay khi 2 shard chết, 2 shard còn lại (8 đồng
   thời) chạy sạch **0 lần 429**. Con số cần canh là **shard song song × concurrency**,
   không phải riêng từng cái. Thiệt hại **$0** — 429 xảy ra trước khi tính tiền, nên đây
   là lỗi rẻ, chỉ tốn wall-clock.
4. **1 shard / account / lần.** Tiền cọc **cộng dồn** khi chạy song song trên cùng account
   → 403 dù thực tế chưa tiêu gì.
5. **"Còn quota" ≠ "đủ cho shard của bạn".** Probe cap-6000 chỉ đặt cọc $0,015 nên account
   còn $0,02 vẫn báo xanh — đã mất 3 shard vì tin nó. **Cách đúng: cộng
   `usage_total_cost_usd` của các shard đã chạy trên account đó rồi lấy $10 trừ đi.**
6. **503 là lỗi phía Kaggle, không phải hết quota** — đã kiểm bằng 3 account cho ra đúng
   cùng tập 503. **Đổi account vô ích**, chờ rồi thử lại.
7. **Đường dẫn Windows 260 ký tự làm hỏng download** — run vẫn thành công, tiền đã tốn,
   data vẫn nằm trên server. Dùng `redownload_all.py`, **đừng chạy lại run**.
8. **Artifact `.task.json` / `.run.json`**: `cd kaggle/benchmarks/artifacts` rồi mới chạy —
   kbench ghi ra CWD chứ không ghi cạnh file task.
9. **Mọi ván phải chạy server-side.** Local chỉ để probe, và kết quả probe **không bao giờ**
   được ghi vào `results/`.

---

---

# PHẦN III — TRƯỚC KHI NỘP

## 13. Sổ rủi ro + cổng kiểm

| Rủi ro | Cổng bắt nó | Xử lý |
|---|---|---|
| **Output haiku bị cắt → dữ liệu bịa mà `parse_failed=0`** | `usage_output_tokens / n_decisions < 0.6 × cap`, kiểm sau **mỗi** run | Nâng `--max-out 3000`, gần như miễn phí |
| **Proxy từ chối slug ≠ model đã chọn → E3b bất khả thi** | Pilot 11/09 | Phương án C (loại persona thay loại model). **P-5** vẫn đứng nhờ E3a |
| **Mức risk mới giết cả loạt shard ở pha `run`** (đã xảy ra ở Q8; pha `push` KHÔNG bắt được) | 1 shard 1 ván ở mỗi p mới, 12/09 | Sửa mapping rồi mới phóng wave |
| **Panel toàn bậc rẻ → trục risk null sạch, E3b mất headline** | Kết quả B ngày 14/09 + E3a ngày 18/09 | §15 mục 1 — cần bạn duyệt |
| **Model chết giữa chừng** (3 lab Trung Quốc đã 503 sạch một lần) | Probe đầu mỗi ngày chạy lớn | **Chốt panel trước 20/09**, sau đó không đổi |
| **Sức khoẻ account trôi** (mất 2/17 trong 4 tuần) | Probe đầu ngày | Bỏ `trnnguynchis`, `chiboiz`, `chinguyentran` |
| **Bị nghi trùng nộp với bản Interface Focus** | Checklist trước khi nộp | ≥70% kết quả mới; khai báo overlap trong Related Work; **trục ngôn ngữ ở lại hẳn bên bản IF** |
| **Không kịp 8 trang** | Ráp draft 29/09 | Cắt **P-7** (E5) trước, luôn luôn |

---

## 14. Checklist chống reviewer

Trước khi nộp, mỗi dòng phải trả lời được bằng một chỗ cụ thể trong paper:

- [ ] *"Đây có phải multiagent system không, hay chỉ là một model tự nói chuyện với chính nó?"* → **P-5**, **P-6**
- [ ] *"Cân bằng của trò chơi là gì?"* → **P-3**
- [ ] *"So với baseline nào?"* → E7, 5 chính sách scripted trên mọi hình
- [ ] *"Hợp tác hay chỉ là tuân theo focal point prompt đã cho?"* → E1 + profile `carry` của E3a
- [ ] *"Model có thật sự tính EV không?"* → E2
- [ ] *"Có phải artifact của prompt/decoding không?"* → E6
- [ ] *"n = 10 ván có đủ không?"* → **n = 10 là lựa chọn đã chốt**; trả lời bằng permutation/exact test, khai báo cluster theo ván, CI bootstrap — **không** bằng cỡ mẫu
- [ ] *"Có tái lập được không?"* → repo ẩn danh + prompt + seed + config trong supplementary. ⚠️ **Nói cho đúng:** seed tái lập được RNG cấp game (xổ số, hoán vị), **KHÔNG** tái lập được văn bản model — đo thật 57% ô cho kết quả khác khi chạy lại (CLAUDE.md). Đừng hứa quá.
- [ ] *"Khác gì paper [ref IF]?"* → một đoạn tường minh trong Related Work
- [ ] Kiểm ẩn danh: không tên tác giả, không tên account Kaggle, không link repo lộ danh tính,
      trích `2512.07462` và bản IF ở **ngôi thứ ba**
- [ ] Mọi con số trong text khớp bảng (sinh bảng bằng script `\input`, như `tab_effects.tex` đang làm)

---

## 15. Cần bạn quyết — ba cách dùng phần credit đang bỏ phí

Chương trình ở §7 dùng ~7% credit được cấp. Ba cách tiêu phần còn lại, xếp theo **giá trị
khoa học trên mỗi đô**. **Tôi không chạy cái nào cho tới khi bạn duyệt.**

| # | Đề xuất | $ thêm | Được gì | Rủi ro nếu KHÔNG làm |
|---|---|---|---|---|
| **1** | **Thêm `gemini-3.1-pro-preview` làm đối cực EV-optimal** ($0,61/ván). Chạy B + E3a + 1 cặp E3b trên nó | **+273** | Đây là model EV-optimal **duy nhất còn lại** trong catalog sau khi `gpt-5.6-sol` bị gỡ. Không có nó, E3b không có tương phản "duy lý vs hợp tác vô điều kiện" → **đường invasion phẳng, §11 mất kết quả headline** | Paper phải dựa hoàn toàn vào §10 (best-response). Vẫn hợp lệ, nhưng yếu hơn hẳn |
| **2** | **Thang năng lực cùng nhà Anthropic**: thêm `claude-sonnet-5-default` ($0,359) + `claude-opus-5` ($0,682), chạy lưới B | **+146** | Trả lời "độ nhạy rủi ro có tăng theo năng lực không, trong cùng một họ model" — câu reviewer hay hỏi. Đây là thang 3 nấc **sạch nhất** còn lại | Không có trục capability; §13 chỉ nói được "chúng tôi chưa kiểm" |
| **3** | **Nâng n từ 10 lên 24** ở lưới B và E3b | **+95** | Khoảng tin cậy hẹp ~35%; B thì **miễn phí** vì data cũ đã có sẵn tới 24 rep (§7.0) | Ở n=10 câu "cỡ mẫu có đủ không" phải trả lời hoàn toàn bằng permutation test |

> ⚖️ **Mọi mở rộng ở đây đều phải tuân luật cân bằng (§7).** Model thêm vào chạy
> **đúng cùng lưới, cùng n** với 5 model hiện có — không có chuyện "chạy ít ván hơn
> vì nó đắt". Con số $ trong bảng đã tính theo n đầy đủ. Nếu ngân sách không kham
> nổi n đầy đủ cho một model, thì **không thêm model đó**, chứ không hạ n của nó.
>
> Riêng mục 1: thêm `gemini-3.1-pro-preview` làm model thứ 6 thì E3b thành
> C(6,2) = **15 cặp**, mỗi model có mặt ở 5 cặp — vẫn tự động cân bằng, nhưng chi phí
> E3b nhảy lên ~$663 (+$499). Con số +$273 trong bảng là phương án gọn hơn: chạy nó ở B, E3a,
> và **4 cặp E3b có mặt của nó**, ghi rõ trong paper rằng ma trận E3b đầy đủ 5×5 còn
> model thứ 6 chỉ có hàng/cột của riêng nó.

**Khuyến nghị: mục 1, quyết vào 18/09** — đúng lúc có kết quả E3a, vì lúc đó mới biết **P-5**
mạnh tới đâu và **P-6** có thật sự cần thiết không. Mục 2 đáng làm nếu sau 26/09 còn dư thời
gian viết. Mục 3 làm sau cùng, nếu vẫn còn ngày.

**Ba câu hỏi khác cần bạn:**

4. **Q8 (lưới risk dày ở bản Interface Focus) để bên nào?** Chuyển sang AAMAS thì **P-4** mạnh
   hơn nhưng bản IF mỏng đi. Hạn chốt **20/09**.
5. **E5 (pledge / thể chế) có làm không?** Thêm ~1 ngày code + $40. Tôi khuyên **để
   stretch**, quyết lại 28/09.
6. **Ai viết draft?** Nếu tôi viết thì cần bạn chốt **title + abstract trước 25/09** để kịp
   nộp abstract 01/10.

---

## 16. Việc làm ngay hôm nay (10/09)

```bash
# 1) Quét tiến trình mồ côi TRƯỚC mọi thứ (lệnh PowerShell ở §12 mục 1)

# 2) Account nào còn sống hôm nay
python plan/scripts/probe_all_models.py

# 3) Sửa cap output — P0, chặn mọi dữ liệu sinh ra từ nay
#    kaggle/benchmarks/crg_task_server.py: MAX_OUT theo model, bỏ số chung 512

# 4) Smoke server-side 1 ván/model, kiểm usage_output_tokens / n_decisions
cd kaggle/benchmarks/artifacts   # để artifact rơi đúng chỗ
```

Sau đó bắt đầu E0: `crsd/models/scripted.py`, `modelsPerSeat`, `crsd/dataio/wide_csv.py`.
