# Phản hồi review — Interface Focus, nộp 13-08-2026

**Trạng thái:** `Accept with revisions`. Không phải reject, không phải major revision mù mịt —
reviewer đã liệt kê chính xác cái gì phải sửa. Đây là file điều phối vòng revision.

**Paper:** [paper/main.tex](../paper/main.tex) — *"Large language model agents in a collective-risk
social dilemma: capability enables risk sensitivity but does not confer it"*.
**Venue:** Interface Focus, số đặc biệt *Machine behaviour in the age of large language models*.

> **Đọc file này trước khi đụng vào `paper/main.tex`.** Toàn văn review nằm ở [§6](#6-toàn-văn-review-nguyên-bản).
> Bảng công việc ở [§2](#2-bảng-công-việc) là nguồn đúng cho câu "còn gì chưa làm".

---

## 0. ĐANG Ở ĐÂU — cập nhật 14-08-2026, 21:10

### 0.1 ✅ Q8 XONG TOÀN BỘ — và nó cho một phát hiện MẠNH HƠN dự đoán

8/8 shard chạy xong (push 26 phút, run 105 phút), gộp sạch: **4 model bậc đỉnh × 5 mức
risk × 10 ván, tiếng Anh, `parse_failed=0`**, mỗi model 80 ván / 4.800 lượt.

| Model (EN) | p=0.1 | **p=0.3** | p=0.5 | **p=0.7** | p=0.9 | bản lề |
|---|---|---|---|---|---|---|
| `gemini-3.1-pro` | 0.0 / 0% | **4.2 / 0%** | 120.0 / 100% | 120.0 / 100% | 120.0 / 100% | **(0.3, 0.5]** ✅ đúng EV |
| `gpt-5.6-sol` | 1.6 / 0% | **118.4 / 70%** | 120.0 / 100% | 120.0 / 100% | 119.8 / 90% | **(0.1, 0.3]** ⚠️ SỚM hơn EV |
| `claude-opus-5` | 120.0 / 100% | 120.6 / 100% | 126.8 / 100% | 128.0 / 100% | 128.0 / 100% | không có |
| `grok-4.20-reasoning` | 120.0 / 100% | 120.0 / 100% | 120.0 / 100% | 120.0 / 100% | 120.2 / 100% | không có |

**Phát hiện: lưới 3 điểm đã GỘP hai model vốn khác nhau.**

- `gemini-3.1-pro` nhảy đúng chỗ trung tính rủi ro đòi hỏi → **risk-neutral thật**.
- `gpt-5.6-sol` đã nhảy **trước** một nấc: ở p=0.3 nó bỏ 28 kỳ vọng để lấy 20 chắc chắn,
  tức nhường ≥ **28.6%** giá trị kỳ vọng → **e ngại rủi ro**, CRRA ≈ **0.485**.
- Cell `gpt-5.6-sol` @ p=0.3 là **cell trung gian DUY NHẤT** của cả bảng bậc đỉnh
  (reach 70%, tổng trải 114/120/122) — 20/44 cell còn lại có SD **đúng bằng 0**.
- `claude-opus-5`: reach 100% ở cả 5 mức nhưng lượng góp **tăng đơn điệu** 120.0 → 128.0.
  Hiệu ứng risk +8.0 của nó là **biên an toàn nới rộng**, không phải quyết định.
- `grok-4.20-reasoning`: đúng 120.0 ở 4/5 mức, SD=0 → **null còn chắc hơn** trên lưới mịn.

Đây là dạng sắc nhất của luận điểm trung tâm paper: hai model **không phân biệt được trên
3 điểm** của thiết kế, tách ra ngay khi làm mịn lưới.

### 0.2 Đã sửa gì trong paper (commit này)

| Chỗ | Sửa |
|---|---|
| abstract | "step function at the EV threshold" → "within a single grid step"; thêm câu lưới 5 mức đặt hai bậc ở hai chỗ khác nhau |
| intro finding 4 | viết lại: hai bậc không cùng chỗ, Gemini đúng EV, GPT sớm hơn một nấc |
| §methods (2 chỗ) | khai báo lưới 5 mức: risk levels + số ván/lượt của 4 config bậc đỉnh |
| §methods account check | 11 → **12 cell**, thêm cell 0.3 **chia cố ý** 5+5 account (F=0.40, P=1.00) |
| §toptier | bỏ "at the expected-value threshold", trỏ tới §pivot |
| caption fig10 | như trên + trỏ hình mới |
| **§results MỚI** | `\subsection{Where the step falls...}` `\label{sec:pivot}` — 3 đoạn + **hình 12** (in ra là *Figure 9*) |
| §discussion | viết lại: trên 3 điểm thì trùng EV, trên 5 điểm thì không → "trùng khớp với nghiệm chuẩn tắc là **hiện vật của độ phân giải lưới**" |
| §limitations | 16/36 → **20/44** cell SD=0; thêm giới hạn lưới mịn (chỉ EN, chỉ bậc đỉnh) |
| §next steps | bỏ mục "quét mức trung gian" (đã làm), thay bằng mở rộng sang VN + bậc rẻ |
| §conclusion | thêm câu hai model KHÁC NHAU về vị trí bậc |
| `esm.tex` | **§mới `sec:pivot-cells`** + bảng 7 (toàn bộ 20 cell); cập nhật execution-batch 11→12 |

### 0.3 ⚠️ Bẫy đã gài chốt: `CORE_RISKS`

Thêm 2 mức risk làm **lệch mọi số trung bình gộp theo cell** (cột "Pooled" ở tab_axes,
"Gemini-3.1 từ 120.8 xuống 80.1"...) vì 2 mức mới chỉ có ở **4/14 config và chỉ tiếng Anh**.

Đã chốt trong [`paper/revision/_data.py`](../paper/revision/_data.py):
`CORE_RISKS = (0.1, 0.5, 0.9)`, và `frontier_games()` / `all_turns()` **lọc mặc định**.
Chỉ `r7` truyền `all_risks=True`. Đã chạy lại cả r1–r7: **`tab_axes.tex` và
`tab_effects.tex` không đổi một ký tự** → mọi số cũ trong paper vẫn đúng.

`r1` có đổi (nó đọc thẳng `plan/runs/`, không qua `_data`): 300 → 380 ván, account check
11 → 12 cell, vẫn **0 cell có hiệu ứng account**. Đây là cải thiện, đã đưa vào paper.

### 0.4 Còn lại — chỉ chờ NGƯỜI DÙNG

| Việc | Trạng thái | Cần ai |
|---|---|---|
| Q8 | ✅ **XONG**, đã vào paper | — |
| 9 mục vòng 1 | ✅ xong, đã vào paper | — |
| Q1 ablation mỏ neo | ⛔ chạy tay trên UI Kaggle — [§2e](#2e-chạy-tay-trên-ui--đường-chắc-ăn-cho-q1--q3); script phân tích `r8` đã có | **người dùng** |
| Q3 probe EV | ⛔ chạy tay trên UI Kaggle; script chấm `r9` đã có | **người dùng** |

Khi người dùng đưa về `nohint_results.zip` / `evprobe_results.zip`: giải nén vào
`results/raw/` rồi chạy **hai script đã viết sẵn** (không cần sửa gì thêm):

```bash
python paper/revision/r8_nohint_ablation.py   # exp_nohint vs exp_baseline
python paper/revision/r9_ev_probe.py          # chấm trục `value` + đối chiếu hành vi
```

- `r8` ghép cặp theo `(model, language, risk, rep)` — CRN nên ghép được từng ván, kiểm
  luôn `seed` hai bên có khớp không; báo Δtổng đóng góp (t + Wilcoxon), Δreach (McNemar),
  phân phối hành động 0/2/4 theo vòng, và **hiệu ứng risk trong TỪNG nhánh + hiệu số** —
  đây mới là số trả lời "mỏ neo có phải nguyên nhân của null không". Chỉ so những model
  có mặt ở CẢ HAI nhánh; model lẻ được liệt kê rõ chứ không bị bỏ im.
- `r9` tính lại ground truth từ config game rồi **đối chiếu với `ground_truth` trong log**,
  chấm accuracy theo model × risk × ngôn ngữ, in luôn **phân phối câu trả lời** (model trả
  lời y hệt ở mọi p thì 33% accuracy là ăn may, không phải biết tính), rồi **chéo accuracy
  với hành vi EV-optimal** theo từng ô (model × risk).
- Cả hai chạy được NGAY khi chưa có data: chúng in phần đối chứng (baseline + MDE cho `r8`,
  bảng đáp án đúng + nửa hành vi của bảng chéo cho `r9`) rồi báo "awaiting data".
- ⚠️ `r9` cũng kiểm hộ cái bẫy ở [§2b](#q3--probe-so-sánh-kỳ-vọng): trục `value` là
  category MỚI. Mục `category_inventory` trong output nói rõ file tổng hợp cũ
  (`crsd_comprehension_all_models.csv`, thứ hình 4 và `r5` đọc) đã có thêm nhóm thứ tư
  hay chưa.

### 0.5 Trạng thái paper

`main.pdf` **24 trang**, `esm.pdf` **7 trang**, build sạch, **0 undefined ref, 0 undefined
citation**, không có overfull hbox mới (2 cái còn lại là của `\maketitle` và bảng decoding,
có từ trước).

Lệnh build lại:
```bash
python paper/revision/r6_summary_tables.py && python paper/revision/r7_intermediate_risk.py
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main && pdflatex esm && pdflatex esm
```

---

## 1. Reviewer muốn gì (rút gọn)

Ba việc được nêu tường minh trong đoạn kết:

1. **Làm rõ QA bản dịch tiếng Việt** (back-translation, bằng chứng số/mệnh đề điều kiện không bị méo).
2. **Bàn thêm — hoặc probe nhẹ — về mỏ neo equal-split** ("an average of 2 per player per round").
3. **Nếu khả thi:** thêm probe comprehension so sánh EV, và một ablation nhỏ bỏ mỏ neo.

Ngoài ra 10 câu hỏi + 4 nhóm điểm yếu. Điểm mấu chốt: reviewer **không** đòi lật kết luận nào.
Ba claim trung tâm (null cho 11 model, capability cần-nhưng-không-đủ, reasoning mua tiết kiệm chứ
không mua độ nhạy risk) đều được khen là "empirically well-supported". Việc của vòng này là **bịt lỗ
phương pháp**, không phải viết lại.

## 2. Bảng công việc

Ký hiệu: **W** = weakness reviewer nêu, **Q** = câu hỏi cho tác giả.
Cột "Cần gì": `TEXT` = chỉ sửa chữ · `OFFLINE` = phân tích lại data đã có, không tốn tiền ·
`RUN` = phải chạy model thật.

| ID | Nội dung | Cần gì | Ước lượng | Trạng thái |
|---|---|---|---|---|
| **Q6** | Tham số decode của model hosted + độ ổn định giữa các ngày | OFFLINE + TEXT | 0đ | ✅ **XONG** — §4.1, `r1` |
| **Q7** | Xổ số dùng chung → có gây "học" qua các rep không? | OFFLINE | 0đ | ✅ **XONG** — `r2` |
| **Q5** | Quỹ đạo từng vòng, nhất là gần ngưỡng | OFFLINE | 0đ | ✅ **XONG** — `r3`, hình 11 + mục kết quả mới |
| **W1** | Mỏ neo equal-split có gây ra null không? | OFFLINE | 0đ | ✅ **XONG** — `r4`, bác bỏ được |
| **Q2** | QA bản dịch tiếng Việt (back-translation) | OFFLINE | 0đ | ✅ **XONG** — `r5` + ESM §1 |
| **W7** | Bảng tóm tắt gọn độ lớn hiệu ứng giữa các manipulation | TEXT | 0đ | ✅ **XONG** — Bảng 2 (`tab:effects`) |
| **W8** | Tóm tắt "tiết kiệm" vs "nhạy risk" theo họ model | TEXT | 0đ | ✅ **XONG** — Bảng 3 (`tab:axes`) |
| **W9** | Bổ sung related work reviewer chỉ tên | TEXT + tra cứu | 0đ | ✅ **XONG** — 9 ref đã xác minh |
| **W5** | Gán ghế persona không ngẫu nhiên hoàn toàn | TEXT | 0đ | ✅ paper đã có kiểm định χ² + ΔR² |
| **Q1** | Ablation bỏ mỏ neo equal-split (chạy thật) | RUN | GPU miễn phí / ~$20 proxy | 🟡 **artifact đã sẵn**, chưa phóng |
| **Q3** | Probe so sánh EV | RUN | GPU miễn phí / ~$5 proxy | 🟡 **artifact đã sẵn**, chưa phóng |
| **Q8** | Thêm mức risk trung gian p=0.3, 0.7 | RUN | ~$18 thực tế | ✅ **XONG** — `r7`, hình 12, mục §pivot, ESM bảng 7. Xem [§0.1](#01--q8-xong-toàn-bộ--và-nó-cho-một-phát-hiện-mạnh-hơn-dự-đoán) |
| **Q4** | Persona có đổi lời biện minh trong game không? | RUN | ~$10 hoặc GPU | ⬜ ⚠️ xem §4.2 |
| **Q10** | Salience một phần / nhiễu (chỉ hiện vòng trước) | RUN (GPU) | 0đ, chậm | ⬜ dùng `memoryMode`/`memoryWindow` sẵn có |
| **Q9** | Nhóm trộn nhiều model | RUN + sửa engine | ~$10 | ⬜ chờ duyệt ngân sách |

### Đã làm gì trong vòng 1 (13-08-2026)

Toàn bộ script nằm ở [`paper/revision/`](../paper/revision/), mỗi script ghi JSON vào
`paper/revision/out/`. Chúng **tính lại từ raw log**, kể cả những con số paper đã in — và
mọi con số cũ đều tái tạo khớp (uncensored `+0.97`, CI `[-2.2,+4.1]`, `P=0.538`, MDE80
`4.4`; salience `-95.3/-26.6/-8.2/-2.9/-2.9`; composition `-100.4/-94.0/-31.8`; language
`146.8`, n=15, `P=1e-16`).

| Script | Trả lời | Kết quả đắt giá nhất |
|---|---|---|
| `r1_decoding_stability.py` | Q6 | temperature **0.7 đặt tường minh** (paper nói sai); 6 ván bị chạy trùng trên account khác nhau → 5/6 y hệt, 1 lệch 4/240; 11 cell của Opus gom từ 2–4 lượt chạy → **không cell nào có hiệu ứng batch** (mọi P>0.22) |
| `r2_lottery_no_learning.py` | Q7 | Không trôi theo rep (P=0.75 / 0.88), không phản ứng với thảm hoạ ván trước (P=0.99 / 0.32). Rút lại xổ số độc lập 10.000 lần: **hai model EV thắng ĐẬM HƠN** — 36.0 và 35.7 so với 20.0, tức +79% thay vì +60% |
| `r3_round_trajectories.py` | Q5 | Ba đường risk chồng khít mọi vòng, nhưng **3 model có cú tăng tốc cuối game** → chúng theo dõi *hạn chót*, không theo dõi *giá của việc trượt*. Tương tác `need × risk` ns ở cả 4 model (P=0.16–0.53). 548 ván đang trượt ở vòng 8: push âm ở cả 3 mức risk |
| `r4_anchor_strength.py` | W1 | P(góp 2) trải từ **0.054 (Qwen-7B) đến 1.000 (Grok-reasoning)**; tương quan với |Δrisk| = **−0.06**. Mỏ neo nhường 15 điểm cho persona, 10 cho ngôn ngữ, nhưng chỉ 3.6 cho risk → **mỏ neo không thể là nguyên nhân của null** |
| `r5_translation_qa.py` | Q2 | Rules EN 99.40% vs VN 98.74% (gap 0.66pp trên 20.160 probe); câu hỏi xác suất thảm hoạ **VN còn tốt hơn EN**. Gap `rules_target` là **của riêng Llama-3.1-8B** (100%→37.2%), sáu model kia 100%/100%. Prompt VN dài hơn 1.203× token |
| `r6_summary_tables.py` | W7+W8 | Sinh `tab_effects.tex` + `tab_axes.tex`, `\input` thẳng vào paper nên không thể lệch với text |

### Vòng 2 — trạng thái

| Việc | Trạng thái |
|---|---|
| **Q1** ablation bỏ mỏ neo | 🟢 chạy lại trên **T4×2** — [`trungkiet/crsd-nohint`](https://www.kaggle.com/code/trungkiet/crsd-nohint) v3. Lần 1 hỏng, xem §2d |
| **Q3** probe so sánh EV | 🟡 chờ slot GPU rồi tự đẩy — [`trungkiet/crsd-evprobe`](https://www.kaggle.com/code/trungkiet/crsd-evprobe) |
| **Q8** mức risk trung gian p=0.3, 0.7 | ✅ **XONG 14-08-2026** — 8/8 shard, 80 ván mới, ~$18. Kết quả ở [§0.1](#01--q8-xong-toàn-bộ--và-nó-cho-một-phát-hiện-mạnh-hơn-dự-đoán) |
| **Q10** salience một phần | ⬜ dùng `memoryMode`/`memoryWindow` sẵn có, chưa chạy |
| **Q9** nhóm trộn model | ⬜ cần sửa engine cho phép mỗi ghế một model |
| **Q4** lời biện minh dưới persona | ⬜ cần prompt có scratchpad giữ full-history |

### 2c. Q8 — chờ duyệt ngân sách 14-08-2026

Reviewer hỏi: *"Have you tested additional intermediate risk levels (e.g. p = 0.3, 0.7) to
probe whether the two step-function models truly pivot at EV = 0.5 or if small
hysteresis/noise exists around the threshold?"*

Điểm bản lề EV nằm ở p=0.5 (chắc chắn 20 so với kỳ vọng 0.5×40=20). Ba mức hiện có không
nói được hai model EV **xoay đúng ở 0.5** hay ở đâu đó lân cận. Thêm p=0.3 và p=0.7 là đủ
kẹp: ở p=0.3 EV vẫn nghiêng về bỏ mặc (28 > 20), ở p=0.7 đã nghiêng về hợp tác (12 < 20).

**Việc phải làm khi được duyệt:**

1. Tạo game config cho hai mức mới — copy `crsd_milinski_low_risk.json`, đổi
   `riskProbability` thành 0.3 / 0.7 và `name` tương ứng. Nhánh frontier không đọc file
   này mà lấy risk từ biến môi trường `CRG_RISKS`, nên với proxy chỉ cần:

   ```bash
   CRG_RISKS=0.3,0.7 CRG_LANGS=en CRG_REPS=10   # 2 risk × 1 lang × 10 rep = 20 ván/model
   ```

2. Model cần chạy: `gemini-3.1-pro-preview` và `gpt-5.6-sol` (hai model EV) là **bắt buộc**;
   `claude-opus-5-default` và `grok-4.20-0309-reasoning` làm đối chứng nếu còn tiền.
3. Dùng `plan/scripts/launch_shard.py` như Ngày A. Nhớ ba sự thật đắt tiền ở
   [README.md](README.md) — nhất là cap `max_output_tokens`.
4. Chi phí thật đo được: gemini-pro ~$0.61/ván, gpt-5.6-sol ~$0.35/ván, opus ~$0.68/ván,
   grok-reasoning ~$0.13/ván. **Cell risk thấp đắt hơn ~1.7×** nên p=0.3 sẽ đắt hơn p=0.7.
   Hai model EV, EN, 20 ván mỗi model ≈ **$19**; thêm hai đối chứng ≈ **$16** nữa.

**Đọc kết quả:** nếu reach nhảy 0%→100% giữa 0.3 và 0.7 mà không có mức trung gian nào ở
0.5, đó là hàm bậc thang đúng ngưỡng EV — củng cố claim hiện tại. Nếu có ván lưng chừng ở
0.3 hoặc 0.7 thì ngưỡng bị nhoè, và câu "step function at the expected-value threshold"
trong paper phải nới lại. **Bảy chỗ phải sửa nếu vậy:** abstract (dòng 30), intro finding 4
(dòng 51), §toptier (dòng 189), caption fig10 (dòng 196), §discussion (dòng 293), §next
steps (dòng 314), conclusion (dòng 318).

**Đã chạy 14-08-2026.** Lệnh:
```bash
python plan/scripts/launch_q8.py --phase push     # 26 phut, 8/8 OK
python plan/scripts/launch_q8.py --phase run
python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --out results/frontier \
    --expect-risks 0.1,0.3,0.5,0.7,0.9 --expect-langs en
python paper/revision/r7_intermediate_risk.py     # so + fig12
```

⚠️ **Hai cái bẫy đã vấp, đã sửa — đừng vấp lại khi quét ra ngoài lưới risk cũ:**

1. **`crg_task_server.py` có `GAME_NAME` chỉ ánh xạ 0.9/0.5/0.1.** Mức nào khác →
   `KeyError` ngay ván đầu, **cả 8 shard chết sau 1 phút**. Đã thêm `game_name()` sinh tên
   cho mức tuỳ ý (`crsd_milinski_p030_risk`). **Tên ba mức cũ KHÔNG được đổi** — chúng là
   khoá join với nhánh open-weight và `results/` đã có dữ liệu mang tên đó.
2. **`merge_shards.py` hard-code lưới 3×2×10.** Gộp sweep lưới khác sẽ báo thiếu hàng chục
   cell chưa bao giờ định chạy rồi trả exit 1. Đã thêm `--expect-risks` / `--expect-langs`.

Bài học chung: **pha push KHÔNG bắt được lỗi này** — push chỉ validate 1 ván trên model mặc
định của server với lưới mặc định. Muốn bắt sớm thì chạy một shard 1 ván ở mức risk mới
trước khi phóng cả loạt.

### 2d. ⚠️ Chạy notebook GPU qua API ≠ chạy qua UI — sự thật đắt tiền

**API Kaggle KHÔNG cho chọn RTX PRO 6000.** `kaggle kernels push --accelerator` chỉ nhận
ba giá trị: `NvidiaTeslaT4`, `NvidiaTeslaP100`, `Tpu1VmV38`. Con RTX PRO 6000 Blackwell
96GB mà cả project dựa vào là **tuỳ chọn chỉ có trên giao diện web**. Không có cờ nào lấy
được nó từ CLI.

Hệ quả, đo thật ngày 13-08-2026:

- Mặc định (`enable_gpu: true`, không truyền accelerator) → Kaggle cấp **Tesla P100 (sm_60)**.
  Wheels vLLM trong `trungkiet/vllm-wheels` build cho sm_120, torch trong đó chỉ hỗ trợ
  sm_75/80/86/90/100/120. EngineCore chết ngay khi khởi tạo. **Cả hai kernel chạy 15 phút
  rồi báo COMPLETE với 0 ván** — `COMPLETE` chỉ nghĩa là script chạy hết, KHÔNG nghĩa là
  thành công. Luôn phải đọc log, đừng tin status.
- Lỗi hiện ra dưới dạng `FileNotFoundError` ở `os.getcwd()` trong `multiprocessing.spawn`.
  **Đó là triệu chứng, không phải nguyên nhân** — cwd biến mất vì tiến trình EngineCore
  chết, chứ không phải vì `os.chdir` sai. Đừng đi sửa CELL 3.
- T4 = sm_75 → torch chạy được. Nhưng **một** T4 chỉ 16GB, không đủ cho gemma-2-9b
  (~18.5GB fp16) hay llama-3.1-8b (~16.1GB) cộng KV cache. Kaggle cấp T4 **×2** nên phải
  `TP_SIZE=2`. Notebook sinh ra đã đặt sẵn — **chạy trên UI với RTX PRO 6000 thì đổi về 1**.
- **Tối đa 2 phiên GPU đồng thời/account.** Đẩy cái thứ ba báo
  `Maximum batch GPU session count of 2 reached`.
- `kaggle kernels push` đọc file code bằng codepage hệ thống → **tiếng Việt trong docstring
  làm nó chết** với `'charmap' codec can't decode`. Phải đặt `PYTHONUTF8=1`.
- `--accelerator ?` **không bị validate** — nó nhận luôn làm giá trị và đẩy một version mới,
  tức là tốn một lượt chạy. Đừng dò giá trị bằng cách thử.

**Mọi thứ còn lại đã kiểm và chạy đúng:** dataset `trungkiet/crsd-code` được tự dò ra,
ba model mount đủ (`exists=True`), wheels vLLM cài offline OK, config + template nohint
đầy đủ, kế hoạch in ra đúng "60 games/model, 3 model × 60 = 180 games". Chỉ kẹt ở GPU.

**BỐN lần thử qua API đều hỏng. ĐÃ DỪNG ĐƯỜNG API.** (13-08-2026)

| Lần | GPU | Chết ở đâu | Nguyên nhân |
|---|---|---|---|
| 1 | P100 (sm_60) | khởi tạo EngineCore | torch trong wheels không hỗ trợ sm_60 |
| 2 | T4×2 (sm_75) | warmup attention | không có FA2 → rơi về FlashInfer → JIT ninja **link lỗi** |
| 3 | T4×2 | import module backend | ép `TRITON_ATTN` → `ImportError: cannot import name 'is_opaque_value' from torch._library.opaque_object` |
| 4 | T4×2 | import vLLM | vẫn `is_opaque_value` — **kể cả khi KHÔNG ép backend nào** |

Lần 4 chốt được gốc rễ: **wheel vLLM 0.22.1 trong `trungkiet/vllm-wheels` không tương thích
với bản torch đang có trên image Kaggle**. Notebook chỉ cài thêm `vllm`, torch lấy từ image
(2.11.0+cu130). Wheels build 09-06-2026, giờ 13-08 — image đã trôi hai tháng. Đây **không
phải chuyện chọn backend**: lần 4 không ép gì cả mà vẫn cùng lỗi.

(Lần 4 còn lộ một lỗi của chính tôi: đoạn dò backend đặt **trước** bước cài vLLM nên báo
`No module named 'vllm'` và không đặt được gì. Đã gỡ bỏ hẳn — xem dưới.)

**Notebook đã dọn về trạng thái tốt nhất cho đường UI:** gỡ đoạn dò backend chưa kiểm chứng,
`TP_SIZE` về 1. `diff` xác nhận `nohint.py` khác `baseline.py` **chỉ ở phần cấu hình**
(danh sách model, `EXPERIMENTS`, `_need`, tên zip) — không đụng một dòng code hành vi nào.

**Muốn cứu đường API thì phải build lại wheels** bằng `kaggle/setup/build_quant_wheels.py`
trên image Kaggle HIỆN TẠI (Internet ON), rồi thay dataset `trungkiet/vllm-wheels`. Chưa làm
vì đường UI nhanh hơn và không cần gì thêm.

### 2e. Chạy tay trên UI — đường chắc ăn cho Q1 + Q3

Nếu lần 4 vẫn hỏng thì **đừng thử tiếp qua API**. Mỗi lần thử tốn ~30 phút và một suất
GPU quota, mà vấn đề nằm ở chỗ không sửa được từ xa (wheels lệch torch của image).

Làm thế này, ~5 phút thao tác:

1. Kaggle → **Create → Notebook**. Settings: **Accelerator = RTX PRO 6000**, **Internet OFF**.
2. **+ Add Input** ba thứ:
   - dataset [`trungkiet/crsd-code`](https://www.kaggle.com/datasets/trungkiet/crsd-code) —
     đã có sẵn `crsd/` + `FAIRGAME/`, **bao gồm cả template nohint và hai config mới**;
   - dataset wheels vLLM (`trungkiet/vllm-wheels`) — hoặc bỏ qua nếu image đã có vLLM;
   - ba model: `qwen-lm/qwen2.5/transformers/7b-instruct`,
     `google/gemma-2/transformers/gemma-2-9b-it`,
     `metaresearch/llama-3.1/transformers/8b-instruct`.
3. Dán [`kaggle/experiments/nohint.py`](../kaggle/experiments/nohint.py) vào, chia cell theo
   dòng `# CELL N`.
4. **Sửa đúng một dòng: `TP_SIZE = 2` → `TP_SIZE = 1`** (RTX PRO 6000 là một card 96GB).
   Đoạn dò backend tự bỏ qua vì sm_120 ≥ sm_80.
5. Run hết. Tải `nohint_results.zip` về bỏ vào `results/raw/`.
6. Lặp lại với [`evprobe.py`](../kaggle/experiments/evprobe.py) → `evprobe_results.zip`.

**Kiểm nhanh xem có thật sự chạy không:** cuối log phải thấy `Hoàn tất 3 lượt` chứ không
phải `Hoàn tất 0 lượt`, và zip phải > 0.00 MB. `COMPLETE` không nói lên điều gì.

### ⚠️ Ẩn danh và tự trích dẫn

`2512.07462` (Huynh et al.) là **paper trước của chính nhóm tác giả**. Bản thảo hiện để
`\author{Anonymous author(s)}`, nên nó đang được trích ở **ngôi thứ ba** — đúng chuẩn cho
bản nộp ẩn danh, và có nói rõ "built on the same framework and by an overlapping group"
để không giấu quan hệ. **Khi lên bản camera-ready (hết ẩn danh): đổi thành ngôi thứ nhất**
("in earlier work we ...") ở hai chỗ: §Material and methods đoạn game loop, và §Discussion
đoạn "Three lines of recent work".

## 2b. Artifact cho vòng 2 — đã dựng xong, chỉ việc phóng

Hai thứ reviewer đòi đích danh đã có đủ config, **chưa chạy**. Cả hai chạy trên GPU Kaggle
(miễn phí) với 3 model nhỏ: `qwen25-7b-instruct`, `llama-3-1-8b`, `gemma2-9b-it`.

### Q1 — ablation bỏ mỏ neo equal-split

| Thành phần | Đường dẫn |
|---|---|
| Template EN/VN đã bỏ gợi ý | `crsd/prompts/crsd_nohint_{en,vn}.txt` |
| Game config | `crsd/configs/game/crsd_milinski_{low,medium,high}_risk_nohint.json` |
| Experiment config | `crsd/configs/experiment/exp_nohint.json` |

Đã kiểm bằng `diff`: hai template **chỉ khác đúng 2 dòng** so với bản gốc — bỏ
`(an average of 2 per player per round)` và `(for example, contributing 2 every round
leaves you 20 at the end)`, cùng hai câu tương ứng bên tiếng Việt. Mọi thứ khác giống
từng byte, nên hiệu ứng đo được là **tác dụng của mỏ neo**, không lẫn thứ gì khác.
Đã smoke-test dựng prompt thật, ra đúng như mong đợi.

Quy mô: 3 risk × 2 lang × 10 rep = **60 ván/model**, đối chiếu trực tiếp với `exp_baseline`
cùng model cùng seed (CRN nên ghép cặp được).

### Q3 — probe so sánh kỳ vọng

Thêm trục câu hỏi thứ tư `value` vào bộ probe (`crsd/engine/comprehension.py`):

| Câu | Nội dung | Đáp án đúng (p=0.1 / 0.5 / 0.9) |
|---|---|---|
| `value_defect_ev` | "Bỏ mặc cả ván và nhóm trượt mục tiêu thì trung bình bạn còn bao nhiêu?" | 36 / 20 / 4 |
| `value_compare` | "Hợp tác hay bỏ mặc cho tiền trung bình cao hơn? 1=hợp tác, 2=bỏ mặc, 0=bằng nhau" | **2 / 0 / 1** |

Hai câu này **không đọc được từ prompt** — agent phải tự nhân xác suất với tiền. Đây là
phép đo trực tiếp cho câu "model có làm nổi phép so sánh mà hành vi EV-optimal trùng khớp".
Ground truth đóng, không phụ thuộc lịch sử. Hỏi ở `rulesCheckpoints` (vòng 1/5/10) chứ
không mọi vòng, vì đáp án tĩnh trong một ván.

Experiment config: `crsd/configs/experiment/exp_evprobe.json`. Test suite đã cập nhật và
pass hết (`test_iter_questions_has_all_categories`).

**Cảnh báo khi phân tích:** trục `value` là category mới, script phân tích nào gộp theo
`category` sẽ thấy thêm một nhóm — kiểm trước khi vẽ lại hình 4.

### Q10 — salience một phần

Không cần code mới: `memoryMode` + `memoryWindow` đã hỗ trợ "chỉ hiện vòng gần nhất"
(xem `exp_memory_ablation` trong `crsd/configs/experiment/archive/`). Chéo nó với
`showCumulative` on/off là ra lưới 2×2 mà reviewer hỏi.

## 3. Cái gì trả lời được mà KHÔNG tốn tiền

### Q7 — xổ số dùng chung có gây học qua các rep không? **Không, theo cấu trúc.**

Không cần chạy lại. Ba lý lẽ, xếp từ mạnh xuống:

1. **Theo thiết kế, không có đường phản hồi.** `crsd/engine/scoring.py:73` rút thảm hoạ **một lần
   duy nhất sau vòng 10** (`compute_outcome`). Không agent nào từng nhìn thấy kết quả xổ số:
   nó xảy ra sau lượt quyết định cuối cùng. Các ván độc lập nhau, agent không mang trí nhớ
   qua ván. Nên "học từ thảm hoạ đã xảy ra" là **bất khả thi về mặt cơ học**, không phải là
   chuyện chưa quan sát thấy.
2. **Kiểm thực nghiệm:** hồi quy đóng góp theo chỉ số rep. Nếu có bất kỳ dạng trôi nào thì hệ số
   phải khác 0. → *phải chạy phân tích này và ghi số vào paper.*
3. **Kiểm bằng mô phỏng:** rút lại xổ số độc lập từng ván 10.000 lần trên **đúng** vector đóng góp
   đã quan sát; báo khoảng payoff. Chứng minh mọi con số payoff trong paper chỉ là hàm của
   lịch rút thăm, và đưa ra ước lượng payoff không phụ thuộc lịch đó.

Lý lẽ 1 nên vào Methods; 2 và 3 vào supplementary.

### Q5 — quỹ đạo từng vòng: dữ liệu đã có sẵn

`turns.jsonl` có đủ `round`, `contribution`, `player`, mọi ván, mọi model. Dựng được:
- đóng góp trung bình theo vòng × mức risk, cho từng model;
- các cell "uncensored" từ nghiên cứu persona — đây là chỗ reviewer thực sự hỏi: nhóm sắp trượt
  ngưỡng ở vòng 7–8 có tăng đóng góp không?
- **Kiểm quyết định:** trong nhóm cuối cùng trượt, đóng góp vòng cuối có cao hơn không, và mức
  tăng đó có tỉ lệ với `p` không? Đây chính là "thích ứng có tương tác với risk không".

Đây là **hình mới**, không phải phụ lục. Nếu quỹ đạo phẳng ở mọi mức risk thì nó là bằng chứng
độc lập, mạnh hơn hẳn, cho claim trung tâm.

### Q2 — QA bản dịch: đã có sẵn hai bằng chứng, chỉ cần trình bày

- **Bằng chứng đã có, chưa dùng:** probe comprehension **trục Rules chênh dưới 1 điểm phần trăm
  giữa hai ngôn ngữ**, và xác suất thảm hoạ được đọc đúng ở cả hai. Đây là kiểm nghiệm bản dịch
  *hành vi*: nếu bản tiếng Việt làm hỏng luật hay con số, Rules accuracy đã phải sập. Paper hiện
  chôn ý này trong đoạn language; phải **nâng lên thành lập luận QA tường minh**.
- **Cần làm thêm:** bảng back-translation từng dòng cho `crsd/prompts/crsd_vn.txt` (31 dòng),
  đối chiếu với `crsd_en.txt`, đánh dấu mọi con số và mệnh đề điều kiện. Vào supplementary.
- Có thể thêm: đếm token EN vs VN (đối chứng độ dài prompt).

### Q6 — tham số decode: xem §4.1, paper đang nói SAI

### W7 — bảng tóm tắt độ lớn

Reviewer muốn một bảng đọc-là-hiểu. Có sẵn hết số:

| Manipulation | Kênh truyền | Δ đóng góp (trên 240) | Model |
|---|---|---|---|
| Risk 0.1→0.9 (11 model) | incentive | +0.97 *(ns)* | pooled uncensored |
| Risk 0.1→0.9 (2 model EV) | incentive | +118.2 … +120.0 | gemini-3.1-pro, gpt-5.6-sol |
| In tổng quỹ đang chạy | prompt | −2.9 … −95.3 | 5 open-weight |
| Thành phần persona 0→6 selfish | prompt | −31.8 … −112.4 | 3 open-weight + nano |
| Đổi ngôn ngữ EN→VN | prompt | tới 146.8 | gpt-5.4-nano |
| Bật/tắt reasoning | model | 105.1 (tiết kiệm), +0.2 (risk) | grok-4.20 |

## 4. Ba điều phát hiện khi soát code — đọc kỹ

### 4.1 ⚠️ Paper đang mô tả SAI cấu hình decode của nhánh thương mại

`paper/main.tex:74` viết:

> *"The models are served by third parties at provider-default temperature, their decoding
> parameters are not under our control, and per-turn sampling seeds are not honoured."*

Nhưng `kaggle/benchmarks/crg_task_server.py:70` đặt `TEMPERATURE = 0.7` và dòng 361–362 gửi
**tường minh** `temperature=TEMPERATURE, seed=seed` cùng `max_completion_tokens=MAX_OUT` cho proxy.
Tức là:

- temperature **KHÔNG** phải mặc định nhà cung cấp — đặt bằng 0.7, **khớp đúng nhánh open-weight**.
  Đây là điểm mạnh của thiết kế mà paper đang tự khai là điểm yếu.
- seed từng lượt **có gửi**; cái không kiểm soát được là nhà cung cấp có tôn trọng nó hay không
  (OpenAI: best-effort; Anthropic/Google: không có tham số seed) — phải phát biểu đúng như vậy.
- `max_completion_tokens` = 6000 cho model reasoning, 512 cho phần còn lại (`crg_task_server.py:109`).
  Con số này phải vào Methods: nó là lý do vì sao model reasoning không bị cắt giữa chừng.

**Việc phải làm:** viết lại đoạn đó cho đúng, và bổ sung bảng tham số decode. Đây vừa là sửa lỗi
vừa là câu trả lời trực tiếp cho Q6. Kiểm tra thêm: `gpt-5.4-nano` chạy qua **OpenAI API trực tiếp**
chứ không qua Kaggle proxy (xem [README.md](README.md) mục "Data đã có") — tham số của nó nằm ở
đường khác, phải soát riêng và khai riêng.

**Độ ổn định giữa các lần chạy** (phần sau của Q6): `gemini-3.1-flash-lite` có dữ liệu chạy ở hai
thời điểm khác nhau (`results/frontier/archive/` và bản chính) — so hai lần đó cho ra một phép kiểm
ổn định thật, miễn phí. Kiểm tra xem có trùng cell không trước khi hứa.

### 4.2 ⚠️ Log KHÔNG chứa lời biện minh — Q4 cần chạy mới

Đã kiểm cả nhánh frontier lẫn open-weight: `raw_response` chỉ có đúng `CONTRIBUTION: n`,
trường `reasoning` rỗng toàn bộ. Prompt bảo *"Output only your decision as a final line"* và model
tuân thủ. Nên **không có phân tích định tính nào làm được trên data hiện có.**

Cần chạy mới với `crsd/prompts/crsd_scratchpad_en.txt` (đã tồn tại, có biến thể VN/FR/ZH/AR).
Cảnh báo: prompt scratchpad **đổi cả memory mode** (chỉ hiện vòng gần nhất), nên nó không phải
ablation sạch cho câu hỏi này — cần một biến thể chỉ thêm "giải thích ngắn gọn rồi mới ra quyết định"
mà giữ nguyên full-history.

### 4.3 ⚠️ Không được trích dẫn arXiv ID reviewer đưa nếu chưa xác minh

Reviewer nêu: `2604.15267` (CoopEval), `2512.07462` (FAIRGAME), `2502.17720` (reasoning giảm hợp tác),
`2508.00032`, `2510.05748`, `2503.07320`, `2505.19212`, `2412.03920` (survey), `2604.00487`,
cùng "MORAL SIM". **Phải tra và xác minh từng cái** (tiêu đề, tác giả, năm) trước khi đưa vào
`refs.bib`. `paper/README.md` ghi rõ quy ước: mọi reference đều đã web-verify DOI/arXiv id — giữ
đúng quy ước đó. Trích sai tên/tiêu đề là lỗi nặng hơn thiếu trích dẫn.

## 5. Khung thư phản hồi

Cấu trúc chuẩn: một đoạn cảm ơn, rồi từng comment → trả lời → chỉ đích danh chỗ sửa trong bản mới.
Đánh số **Qn** theo đúng "Questions for Authors" ở [§6](#questions-for-authors).
✅ = viết được ngay, số đã có. ⛔ = còn chờ chạy.

```
Q1  (bỏ mỏ neo equal-split) ⛔ CHỜ CHẠY
    Trả lời tạm bằng bằng chứng gián tiếp đã có: P(góp 2) trải 0.054–1.000 khắp panel và
    tương quan với |Δrisk| chỉ −0.06 → mỏ neo KHÔNG giải thích được null. ESM §5, bảng 6.
    Khi có data nohint: thêm §Results mới + ghép cặp với exp_baseline.

Q2  (QA bản dịch tiếng Việt) ✅
    Bổ sung ESM §1: back-translation TỪNG DÒNG của prompt VN, cộng bằng chứng hành vi —
    Rules accuracy EN 99.40% vs VN 98.74% trên 20.160 probe (chênh 0.66pp), và câu hỏi
    xác suất thảm hoạ VN còn ĐÚNG HƠN EN. Khoảng cách rules_target là của riêng
    Llama-3.1-8B (100%→37.2%); sáu model kia 100%/100%.

Q3  (probe so sánh EV) ⛔ CHỜ CHẠY
    Đã dựng trục câu hỏi `value` thứ tư trong engine (`crsd/engine/comprehension.py`),
    ground truth do engine tính. Chưa có data.

Q4  (persona → lời biện minh trong game) ⛔ KHÔNG TRẢ LỜI ĐƯỢC TỪ DATA CŨ
    Nói thẳng: `turns.jsonl` chỉ lưu dòng `CONTRIBUTION: n`, không lưu lập luận. Cần
    prompt có scratchpad. Đã ghi vào §next steps. Xem §4.2.

Q5  (quỹ đạo từng vòng) ✅
    §Results mới "Inside the game: the agents track the deadline, not what missing it
    costs" + hình 11. Ba đường risk chồng khít mọi vòng; NHƯNG 3 config có cú tăng tốc
    cuối game xảy ra ở CÙNG vòng và CÙNG độ cao ở mọi mức risk. Tương tác need×risk ns
    ở cả 4 model (P=0.16–0.53). Đây là câu trả lời mạnh hơn reviewer hỏi.

Q6  (tham số decode + độ ổn định) ✅ + ĐÍNH CHÍNH
    Paper cũ nói sai ("provider-default temperature"). Thực tế temperature = 0.7 đặt
    tường minh, KHỚP nhánh open-weight; seed có truyền; top_p để mặc định. ESM §2 bảng 5.
    Độ ổn định: 6 ván bị chạy trùng → 5/6 y hệt, 1 lệch 4/240; permutation ANOVA trên
    12 cell nhiều batch → 0 cell có hiệu ứng batch (mọi P>0.22).

Q7  (xổ số độc lập từng ván) ✅ + KẾT QUẢ MẠNH HƠN
    Hai lớp: (a) cấu trúc — xổ số quay SAU quyết định cuối và KHÔNG hiện cho agent nào,
    nên không có đường phản hồi; (b) thực nghiệm — không trôi theo rep (P=0.75/0.88),
    không phản ứng với thảm hoạ ván trước (P=0.99/0.32). Mô phỏng rút lại xổ số độc lập
    10.000 lần: hai model EV kiếm 36.0 và 35.7 thay vì 32.0/31.8 → lợi thế so với
    cooperator tốt nhất TĂNG từ +60% lên +79%. Xổ số dùng chung đã LÀM HẠI họ.

Q8  (mức risk trung gian 0.3, 0.7) ✅ ĐÃ CHẠY — và nó đổi một câu của paper
    Chạy 4 config bậc đỉnh ở p=0.3 và 0.7 (EN, 10 ván/cell): 80 ván, 4.800 lượt,
    parse_failed=0. Kết quả: HAI BẬC KHÔNG CÙNG CHỖ. Gemini-3.1-Pro nhảy giữa 0.3 và 0.5
    — đúng chỗ trung tính rủi ro. GPT-5.6-sol đã nhảy TRƯỚC p=0.3 (góp 118.4, reach 70%)
    ở mức mà bỏ mặc còn đáng 28 kỳ vọng so với 20 chắc chắn → e ngại rủi ro, CRRA≈0.5.
    Trả lời trực tiếp vế "small hysteresis/noise around the threshold": CÓ, và nó nằm
    gọn trong đúng một cell rộng một nấc lưới. Chỗ sửa: §Results §pivot mới + hình 12,
    ESM §6 bảng 7, và bỏ cụm "step function at the expected-value threshold" ở 7 chỗ.

Q9  (nhóm trộn nhiều model) ⛔ CHƯA CHẠY — cần sửa engine cho mỗi ghế một model.
    Đã có trong §next steps như "the configuration most deployments will actually have".

Q10 (salience một phần/nhiễu) ⛔ CHƯA CHẠY — engine đã có sẵn `memoryMode`/`memoryWindow`.

W1  (mỏ neo gây null?) ✅ BÁC BỎ ĐƯỢC — xem Q1.
W5  (gán ghế persona không ngẫu nhiên) ✅ paper đã có χ²=23.0, P=0.0003 + ΔR²=0.005–0.029.
W7  (bảng độ lớn hiệu ứng) ✅ Bảng 2 `tab:effects`, sinh từ script nên không lệch với text.
W8  (thrift vs risk theo họ model) ✅ Bảng 3 `tab:axes`.
W9  (related work) ✅ 9 reference mới, đã xác minh tác giả thật (KHÔNG đoán).
```

## 6. Toàn văn review (nguyên bản)

<details>
<summary>Bấm để mở — giữ nguyên tiếng Anh, không dịch, để đối chiếu chính xác</summary>

**Venue:** Machine behaviour in the age of large language models: social, cognitive and evolutionary
perspectives' issue of Interface Focus. **Submitted:** August 13, 2026.

### Summary

This paper evaluates whether large language model (LLM) agents display human-like risk sensitivity
in a canonical collective-risk social dilemma inspired by climate change. Using six-agent groups
across three catastrophe probabilities (p = 0.1, 0.5, 0.9), two languages (English, Vietnamese),
and a broad model panel (seven open-weight models and six commercial models, including cheap and
top tiers), the authors find that 11/13 configurations exhibit no consequential response to risk,
whereas prompt-side manipulations (printing the running pool total, persona composition, language)
drive orders-of-magnitude larger behavioral shifts. Two top-tier models, however, implement the
expected-value solution almost exactly, contributing 0 at p = 0.1 and exactly the threshold at
p ≥ 0.5. Comprehension probes show high rule literacy but size-dependent deficits in cumulative
arithmetic; nevertheless, risk insensitivity persists even where arithmetic is near ceiling.

### Strengths

**Technical novelty and innovation**
- Introduces a rigorous, climate-relevant collective-risk threshold game for LLM agents that
  directly parallels foundational human experiments, enabling a clean human benchmark.
- Decomposes "comprehension vs disposition" via an in-situ probe battery adapted from prior
  two-player settings to an N-player threshold game, including a salient A/B manipulation
  (hidden vs printed pool totals).
- Broad, model-diverse evaluation: seven open-weight models (7–72B) plus six commercial
  configurations spanning providers and tiers, enabling within-family and cross-provider contrasts,
  including a rare within-model reasoning toggle.
- Identifies a striking split: capability appears necessary but not sufficient for risk sensitivity;
  two top-tier models approximate the expected-value step function while others remain flat.

**Experimental rigor and validation**
- Careful treatment of ceiling censoring using a second study that varies persona composition to
  create genuinely uncertain outcomes; multiple robustness checks (paired design, alternative cell
  selection, full regression with interaction) converge on the same null for risk effects.
- Quantifies and compares effect sizes on a common scale (points of 240), enabling transparent
  magnitude comparisons between incentive-driven and prompt-side manipulations.
- Comprehensive error analysis on comprehension probes, with explicit reporting of parse failures,
  Wilson CIs, and caution about anti-conservative intervals due to clustering.

**Clarity of presentation**
- Clear articulation of methodological threats (anchoring via equal-split exemplar; shared lottery
  draws; hosted API constraints) and which inferences are or are not affected.
- Effective figures and narrative that separate "economy of play" from "risk sensitivity," and
  connect linear persona effects to threshold crossing.
- Distinctly presented language effects, showing heterogeneous, model-specific directions rather
  than overgeneralized claims.

**Significance of contributions**
- Advances the behavioral science of LLMs by demonstrating: (i) large prompt-side salience effects
  that can overwhelm incentive structure; (ii) that risk sensitivity is not a universal property of
  current LLMs; and (iii) that even risk-responsive models deviate from humans (step function vs
  graded response).
- Offers concrete methodological guidance: include prompt-side controls and evaluate panels of
  models before attributing preferences to "LLMs."

### Weaknesses

**Technical limitations or concerns**
- The decision prompt explicitly names the equal-split strategy (2 per round), creating a strong,
  risk-independent focal action that may confound interpretation of "just-enough" contributions.
- Commercial model runs lack controlled decoding parameters and seeding; behavior might be partly
  attributable to provider-side defaults rather than agent preferences.
- End-of-game catastrophe resolution reuses a small set of shared random draws across many
  conditions, forcing the authors to disregard realized catastrophe outcomes as evidence.

**Experimental gaps or methodological issues**
- Comprehension probes are not available for the commercial/top-tier models (including the two
  risk-sensitive ones), limiting mechanistic conclusions about how they achieve expected-value play.
- Seat assignment in mixed-persona groups is not fully randomized; although authors test for seat
  effects, residual confounds cannot be fully excluded.
- Vietnamese prompts may interact with translation quality and tokenization in ways not fully
  audited; extreme language effects (e.g., GPT-5.4-nano) warrant additional QA.

**Clarity or presentation issues**
- Some central numerical claims (e.g., effect-size comparisons across manipulations) could be
  further distilled into a compact summary table to help readers synthesize magnitudes at a glance.
- The separation between "economy/thrift" and "risk sensitivity" is well made but occasionally
  buried in dense text; brief schematic summaries per model family would aid digestion.

**Missing related work or comparisons**
- The paper could better connect to recent benchmarks and findings on reasoning modes reducing
  prosociality, mechanism design effects on cooperation, and payoff sensitivity in PD/PGG settings,
  situating its results within these broader trends (e.g., MORAL SIM; CoopEval; reasoning-induced
  "calculated greed"; FAIRGAME results on incentive magnitude and language).

### Detailed Comments

**Technical soundness evaluation**
- The core design—replicating Milinski et al.'s six-player, ten-round threshold game across three
  risks—is technically sound and policy-relevant. The persona manipulation is a strong
  methodological innovation to break ceiling effects while holding incentives constant.
- The explicit anchoring to the equal-split solution in the prompt is a significant confound; it
  likely induces "just-enough" play independent of risk, and should ideally be removed or
  counterbalanced in a follow-up. The authors forthrightly acknowledge this limitation.
- The shared lottery draw schedule is suboptimal but transparently handled; the authors
  appropriately base causal claims on contributions/reach rather than realized catastrophes.
- The comprehension battery convincingly shows rule literacy and a size-dependent arithmetic
  deficit; the A/B salience manipulation (printing the pool) elegantly links comprehension and
  behavioral shifts. However, without probes for commercial models, the cognitive route to
  expected-value behavior remains unclear.

**Experimental evaluation assessment**
- Statistical treatment is careful: open-weight analyses are paired (shared seeds), uncensored-cell
  selection is validated via multiple pre-registered-style checks, and effect sizes are
  contextualized by detection limits (≈4 points with 80% power).
- Hosted models are nearly deterministic; the choice to emphasize cross-model contrasts over
  within-model regression is sensible. Still, reporting provider variability in temperatures/top_p
  (if available) would improve interpretability.
- The language manipulation reveals substantial, model-specific effects and aligns with
  comprehension findings (Vietnamese selectively harming cumulative arithmetic). Yet, extreme
  language failures (0% reach) call for additional translation QA or back-translation checks.
- The reasoning toggle in Grok-4.20 is an excellent within-model control: it shows that explicit
  reasoning improves thrift but not risk sensitivity—mirroring recent results that "deliberation"
  can reduce prosociality while not necessarily improving incentive-aligned responsiveness.

**Comparison with related work (using the summaries provided)**
- Consistent with CoopEval (2604.15267) and FAIRGAME-based studies (2512.07462), this paper
  underscores that changes to incentives/mechanisms can matter but that LLM responses are highly
  model- and prompt-dependent. Here, in contrast to PGGs where increased returns (r) often raise
  cooperation, risk changes in a threshold setting largely fail to move most models—emphasizing that
  not all incentive levers transfer across game families.
- The finding that explicit reasoning improves thrift but not risk sensitivity dovetails with recent
  evidence (2502.17720) that "reasoning" can reduce cooperation and norm enforcement; the present
  study extends this by showing reasoning's limited impact on the higher-order decision "whether to
  cooperate at all" when EV favors defection.
- The large language and salience effects align with emerging results that communication/framing
  powerfully modulate LLM behavior (2508.00032, 2510.05748) and that moral framing or opponent
  identity shifts strategies in social dilemmas (2503.07320, 2505.19212). The present work uniquely
  quantifies that prompt-side factors can dominate incentive structure in a threshold-risk
  environment.
- The call for multi-model panels echoes concerns in the survey (2412.03920) and experimental papers
  limited to single models (e.g., 2604.00487): here, two top-tier models contradict the modal null,
  showing that generalizations from one system can be dangerously misleading.

**Discussion of broader impact and significance**
- The results challenge the validity of using LLMs as human surrogates in risk-structured collective
  dilemmas: most models ignore risk, while the few that attend to it behave non-humanly (a step at
  the EV threshold vs graded human curves).
- Methodologically, the paper offers a blueprint for behavior-vs-comprehension disentanglement and
  stresses the necessity of prompt-side controls and model panels before making preference
  claims—valuable norms for the field.
- Practically, the strong language and salience dependencies underscore deployment risks in
  multilingual, multi-agent settings and suggest that interface design could inadvertently dominate
  substantive incentives.
- The work highlights a potentially general phenomenon: capability upgrades alone may deliver thrift
  without aligning agent behavior to incentive-relevant risk, complicating expectations that "more
  reasoning" will produce more human-like or normatively appropriate decisions.

### Questions for Authors

1. How sensitive are the main results to removing the equal-split "2 per round" exemplar from the
   decision prompt? Could you report a small ablation (even on a subset of models) to assess
   anchoring effects on "just-enough" play and risk responsiveness?
2. For Vietnamese, what translation/validation procedures were used? Can you provide back-translated
   examples and/or minimal QA evidence that numerical cues and key conditionals were faithfully
   preserved?
3. Could you add a simple probe for expected-value comparison (e.g., "Which action has higher
   expected value for you at the current p?") to the comprehension battery for open-weight models,
   and—if feasible—run a limited probe set for at least one top-tier commercial model to triangulate
   mechanisms behind EV-consistent play?
4. The persona composition effect is linear and large. Do single-agent persona prompts influence
   subsequent in-game rationales (e.g., stated goals, fairness language)? Any qualitative analysis
   linking persona framing to decision justifications would be informative.
5. Can you report round-by-round trajectories (especially near the threshold) to see whether models
   adapt contributions with accumulating evidence of (not) reaching the target, and whether this
   adaptation interacts with risk?
6. Given the deterministic tendencies of hosted models, what were the provider-default decoding
   settings (temperature, top_p) when available? Any observed instability across runs/days?
7. Could you include an alternative lottery implementation (per-game independent draws) in a small
   follow-up to confirm that realized-catastrophe feedback does not, in fact, induce learning-like
   adjustments over repetitions?
8. Have you tested additional intermediate risk levels (e.g., p = 0.3, 0.7) to probe whether the two
   step-function models truly pivot at EV = 0.5 or if small hysteresis/noise exists around the
   threshold?
9. Would a group-heterogeneity test (mixed-model groups) replicate the step vs flat patterns at the
   collective level, or would cross-influences produce intermediate behaviors?
10. How robust are the salience effects (visible running total) if visibility is partial or noisy
    (e.g., only last round's contributions shown), and does this interact with model size/arithmetic
    ability?

### Overall Assessment

This is an important and timely contribution to the machine behaviour of LLMs under collective-risk
dilemmas. The paper's central insights—that most models are largely insensitive to catastrophic risk
while prompt-side salience, personas, and language can dominate; that two top-tier systems implement
near–expected-value behavior but in a sharply non-human, step-like way; and that capability appears
necessary but not sufficient—are both empirically well-supported and conceptually significant. The
methodological care (ceiling-aware design via persona composition, in-situ comprehension probes with
a salient A/B control, and cross-model/cross-language coverage) positions this work as a touchstone
for future evaluations. Key limitations remain: the equal-split prompt anchor and lack of
comprehension probes for commercial models restrict mechanistic inferences, and hosted API
constraints blur causal attribution for frontier systems. Nonetheless, the study's findings are
consequential for both scientific understanding and practical deployment of LLM agents in
high-stakes, risk-structured environments. I recommend acceptance with revisions focused on
clarifying translation QA, further discussing (or lightly probing) the equal-split anchoring, and,
if feasible, adding a minimal expected-value comprehension probe and a small ablation to strengthen
mechanistic claims.

</details>

---

## 7. Nhật ký

| Ngày | Việc | Kết quả |
|---|---|---|
| 13-08-2026 | Nhận review, dựng file này, soát code tìm việc làm được offline | Phát hiện §4.1 (paper sai về temperature), §4.2 (không có log lời biện minh) |
| 13-08-2026 | Vòng 1 trọn vẹn: 6 script phân tích, sửa `main.tex`, dựng ESM | 9/15 mục XONG. `main.pdf` 23 trang, `esm.pdf` 6 trang, build sạch, 0 citation undefined |
| 13-08-2026 | Dựng artifact vòng 2 cho Q1 + Q3 | Template no-hint, 3 game config, 2 experiment config, 2 probe EV mới; test suite pass |
| 14-08-2026 | 4 lần thử chạy notebook GPU qua API | Thất bại có nguyên nhân rõ, xem §2d. Chuyển Q1+Q3 sang chạy tay trên UI |
| 14-08-2026 | **Q8 trọn vẹn**: 8 shard × 2 pha (push 26', run 105'), gộp, phân tích, vào paper | **Bậc của hai model KHÔNG cùng chỗ** — Gemini đúng EV, GPT sớm hơn một nấc (e ngại rủi ro, CRRA≈0.5). `main.pdf` 24 trang, `esm.pdf` 7 trang |

### Đã đụng vào file nào

**Paper:** `main.tex` (8 chỗ vòng 1 + 11 chỗ vòng 2), `refs.bib` (+9 ref), `esm.tex` (mới,
+§6 bảng 7), `figures/fig11_*` + `figures/fig12_pivot.*` (mới),
`revision/*.py` (7 script) + `revision/out/*` (JSON + 2 bảng `.tex` được `\input`).

**Code:** `crsd/prompts/crsd_nohint_{en,vn}.txt` (mới), `crsd/configs/game/*_nohint.json`
(3 mới), `crsd/configs/experiment/exp_{nohint,evprobe}.json` (2 mới),
`crsd/engine/comprehension.py` (thêm trục `value`), `crsd/tests/test_comprehension.py`
(đổi tên + nới assert cho category mới).

**Không đụng:** mọi file trong `results/` — không có data cũ nào bị ghi đè.

### Bẫy đã gặp, đừng gặp lại

1. **`results/frontier/crsd_all_models.csv` LẠC HẬU** — chỉ còn `flash-lite`, thiếu toàn bộ
   bậc đỉnh. Ai join vào file đó sẽ âm thầm mất hai model mà kết luận trung tâm dựa vào.
   Dùng `paper/revision/_data.py` (đọc glob từng model) hoặc glob như `make_figures_toptier.py`.
2. **Tên model của `gpt-5.4-nano` trong `games.csv` là `OpenAIGPT5Nano`**, không phải
   `openai-gpt-5.4-nano` — nano chạy trước khi có task frontier nên tự ghi tên khác.
3. **Ghi file bằng Python trên Windows ra CRLF**, trong khi repo ép LF (`.gitattributes`).
   Ghi xong phải `.replace(b'\r\n', b'\n')` nếu không `diff` sẽ báo đổi cả file.
4. **ESM cần font T5 (vntex) cho dấu tiếng Việt.** T1 không có `ơ ư ă â`. Đã xử lý bằng
   `\newcolumntype{V}` + macro `\vn{}`; đừng đổi `\usepackage[T5,T1]{fontenc}` thành T1 đơn.
5. **Thêm mức risk mới làm LỆCH mọi trung bình gộp theo cell.** p=0.3/0.7 chỉ tồn tại ở
   4/14 config và chỉ tiếng Anh, nên cột "Pooled" trong `tab_axes` và mọi số dạng "trung
   bình khắp cell" sẽ âm thầm đổi. Đã chốt `CORE_RISKS = (0.1, 0.5, 0.9)` trong
   `paper/revision/_data.py`, lọc MẶC ĐỊNH ở `frontier_games()` và `all_turns()`; muốn lấy
   đủ 5 mức phải truyền `all_risks=True` (chỉ `r7` làm thế). Sau khi chốt, chạy lại r1–r7
   thì `tab_axes.tex` và `tab_effects.tex` không đổi một ký tự.
6. **Số trong TÊN FILE hình ≠ số hình in ra.** `fig12_pivot.pdf` in ra là *Figure 9*,
   `fig10_toptier.pdf` là *Figure 7*. LaTeX đánh số theo thứ tự float được ĐẶT. Tên file
   chỉ là nhãn thứ tự tạo ra. Đừng "sửa cho khớp" — thứ tự in hiện tại đã đúng và liên tục.
