# plan/ — kế hoạch đang chạy của CRSD-LLM

Thư mục này giữ kế hoạch **đang thực thi**, để một session/chat sau mở ra là biết
đang ở đâu và làm gì tiếp. Khác với [PROJECT.md](../PROJECT.md) (lộ trình tổng, hiện
đã lạc hậu so với thực tế) và [CLAUDE.md](../CLAUDE.md) (quy ước code + credential).

## Đang làm gì: mở rộng nhánh frontier từ 1 model lên panel nhiều model

Đọc theo thứ tự này:

| File | Nội dung |
|---|---|
| [aamas2027-plan.md](aamas2027-plan.md) | **⚡ FILE KẾ HOẠCH DUY NHẤT của nhánh AAMAS (gộp 10-09-2026).** Phần I = paper (venue, ràng buộc trùng nộp với Interface Focus, câu chuyện, bố cục 8 trang) · Phần II = chạy (panel, luật cân bằng, chỉ tiếng Anh, 8 thí nghiệm, **schema CSV wide 82 cột**, lịch từng ngày tới 08/10) · Phần III = checklist trước khi nộp. **Đọc trước khi phóng bất cứ shard nào.** |
| [model-availability.md](model-availability.md) | 38 slug trên Kaggle Model Proxy: cái nào sống, sống ở đâu, giá bao nhiêu |
| [scripts/](scripts/) | xem bảng script dưới |

### Script

| Script | Việc |
|---|---|
| `launch_day_a.py` | phóng cả 12 shard Ngày A song song (`--dry-run` để xem trước) |
| `launch_shard.py` | chạy 1 shard trên 1 account: auth → sinh file shard → push → run → download |
| `launch_wave_e12.py` | **wave E1 (`--template nohint`) + E2 (`--probe rules,value`)**, 2 pha push/run, có cổng cân bằng ở `--dry-run` |
| `fill_wave_e12.py` | đọc data đã tải, tính ĐÚNG (risk, rep) còn thiếu của E1/E2 rồi sinh lệnh chạy bù |
| `probe_quota.py` | đo quota CÒN LẠI của từng account (dò nhị phân trên `max_output_tokens`) — `probe_accounts.py` chỉ nói còn/hết |
| `run_fill.py` | chạy bù theo ĐỢT trên account còn quota; account 403 lúc push bị loại, shard quay lại hàng đợi |
| `launch_e3a.py` | E3a best-response: 4 profile × 5 model, ghế scripted; `--smoke` chạy 1 ván kiểm thiết bị trước |
| `collect_probes.py` | gom `probes.jsonl` của E2 vào `results/` — không chạy thì kết quả E2 mất theo thư mục gitignore |
| `write_provenance.py` | dựng lại `results/PROVENANCE.json` (`to_wide_csv.py` KHÔNG ghi file này) |
| `check_runs.py` | xem trạng thái mọi shard (đọc log, không gọi API), `--watch` để tự làm mới |
| `merge_shards.py` | gom shard thành dataset, kiểm phủ đủ 60 cell + `parse_failed=0` |
| `probe_all_models.py` | probe liveness song song ở local (staging proxy) — **chỉ probe, không sinh data** |
| `probe_crg_prompt.py` | kiểm model trả lời được 1 lượt CRG thật và parse được |

Kết quả + log của mỗi shard nằm ở `plan/runs/<label>/` (đã gitignore, không commit).

**Người dùng đã chọn chạy bậc đỉnh (top tier) TRƯỚC**, không screen trước — 4 model
`claude-opus-5` · `gemini-3.1-pro-preview` · `gpt-5.6-sol` · `grok-4.20-reasoning`, ~$88.
Rủi ro (cả 4 có thể cán trần) đã được nêu và người dùng vẫn chọn. **Đừng tự ý đổi sang
screen-trước**; muốn đổi thì hỏi.

## ✅ Trạng thái 11-09-2026 — B, E1, E2, E3a XONG

`verify_wide.py --expect-reps 10` **xanh trên 1.850 ván / 185 file**, cân bằng OK cả bảy
experiment. Bộ test: **284 pass** (trừ 2 file Interface Focus cố ý để hỏng).

| Experiment | Ván | Ghi chú |
|---|---|---|
| `exp_baseline` (lưới B) | 550 = 5 × 110 | 11 mức risk × 10 rep |
| `exp_nohint` (E1) | 150 = 5 × 30 | bỏ mỏ neo equal-split |
| `exp_evprobe` (E2) | 150 = 5 × 30 | + 4.500 câu probe |
| `exp_bestresponse_{defect,coop,carry,cond}` (E3a) | 4 × 250 = **1.000** | 1 ghế LLM + 5 ghế scripted |

### Kết quả đọc được ngay

**E2 — hiểu luật ≠ tính được kỳ vọng.** `rules` **100,0%** (3600/3600) · `value` **77,2%**
(695/900). Theo model: flash-lite 99,9% · haiku 97,2% · luna 96,8% · grok 93,3% · qwen 90,0%.

**E3a — KHÔNG model nào chơi best response, một ván cũng không.** Hai profile có best
response hằng số (góp 0 mọi vòng) cho kết quả phẳng lì:

| Model | `carry` tổng góp TB/ván | `defect` tổng góp TB/ván | % ván đúng BR |
|---|---|---|---|
| luna | 4,5 | 8,5 | **0%** |
| flash-lite | 10,9 | 13,9 | **0%** |
| haiku | 15,3 | 7,8 | **0%** |
| qwen | 20,4 | 29,9 | **0%** |
| grok-nr | 32,9 | 30,7 | **0%** |

Ở `carry` nhóm đã chắc chắn đạt target mà không cần ghế LLM, ở `defect` ghế LLM một mình
không thể đạt target — **cả hai trường hợp góp thêm một xu nào cũng là lỗ thuần**. Cả 5
model vẫn góp. Đây là bằng chứng cho "hợp tác hay chỉ tuân lệnh?" mạnh hơn ablation E1, và
nó tách hẳn hai thứ đó ra (§7.3).

### 📄 Paper AAMAS — MAJOR REVISION 16-09-2026 (template chính thức, dùng đủ B + E1..E4 + E6)

**Title:** *Cooperation by Default: LLM Agents in the Collective-Risk Dilemma*.
`paper/AAMAS/main.tex` dựng bằng **`aamas.cls` chính thức** (từ `aamas_2027_template.zip`,
không sửa style). Bản dựng: **8 trang thân bài, references từ trang 9, 0 lỗi, 0 undefined,
0 Overfull, 0 font Type 3.** Abstract dạng text để dán lên OpenReview:
`paper/AAMAS/OPENREVIEW_ABSTRACT.txt` (281 từ, không có số kết quả; phải khớp từng chữ với `main.tex`).

Toàn bộ bài nằm trong **một file** `paper/AAMAS/main.tex` (gộp 17-09-2026, thư mục
`sections/` đã xoá). Cột "Label" để nhảy tới mục trong file.

| Mục | Label trong `main.tex` | Dữ liệu |
|---|---|---|
| 1 Introduction | `sec:intro` | — |
| 2 Related work (có đoạn khai overlap với bản IF) | `sec:related` | — |
| 3 Game, Mệnh đề 1–2, thiết kế, prompt nguyên văn | `sec:game` | — |
| 4 Incentives: 4.1 self-play grid · 4.2 prompt controls · 4.3 value question | `sec:risk`, `sec:grid`, `sec:controls`, `sec:knowing` | baseline, nohint, evprobe, para1/2, temp0, wording, neutral |
| 5 Partners: 5.1 fixed partners · 5.2 mixed tables | `sec:partners`, `sec:scripted`, `sec:groups` | bestresponse ×4, mixed |
| 6 Selection (Fermi, rare mutation, N = 6 vs 30) | `sec:selection` | mixed |
| 7 Discussion and conclusion (threats, limitations, ethics gộp một đoạn) | `sec:discussion` | — |

Cấu trúc 7 mục ở trên có từ 19-09-2026 (trước đó 8 mục); supplement tham chiếu các mục này bằng `\ref{main-sec:…}` nên đánh số lại không làm lệch.

**Câu chuyện:** 5 model giá rẻ trả tiền theo **thói quen** (habit = hành vi vẫn tiếp tục khi
trả tiền đã vô ích: p = 0 hoặc sau khi kết quả đã định), không theo risk; câu trả lời khi được
hỏi thì theo risk nhưng hành vi không; phản ứng với đối thủ chỉ ở dạng đơn giản; chia đều khít
không có độ dư; và **quy tắc chấm điểm quyết định ai được chọn** (so với bạn cùng bàn ⇒ người
trả ít nhất thắng, nhóm sụp; so giữa các bàn ⇒ Flash-Lite thắng ở p ≥ 0,5).

⚠️ **Welfare dùng payoff KỲ VỌNG, không dùng `mean_payoff`.** Xổ số được khoá theo `rep`, nên
cả kho dữ liệu chỉ có 10 lần rút, dùng lại ở mọi ô, cả 10 đều < 0,47 → mọi ván trượt ở
p ≥ 0,5 đều dính thảm hoạ. Hành vi không bị ảnh hưởng.

**Sinh lại số + figure + bảng, rồi dựng bài** (từ gốc repo):

```bash
python paper/AAMAS/analysis/selfplay.py    # \Cnt \Lot \Grid \NoCue \Rob, fig_selfplay, tab_models, tab_robust
python paper/AAMAS/analysis/probes.py      # \Probe, fig_knowdo
python paper/AAMAS/analysis/scripted.py    # \Scr, fig_scripted, tab_settled
python paper/AAMAS/analysis/mixed.py       # \Mix, fig_mixed
python paper/AAMAS/analysis/advantage.py   # \Adv, fig_advantage
python paper/AAMAS/analysis/selection.py   # \Sel, fig_selection (~3 phut)
cd paper/AAMAS && latexmk -pdf main.tex
python -m pytest crsd/tests/test_paper_equilibrium.py   # cong chan Menh de 1
```

**Supplement** (`paper/AAMAS/supplement/supplement.tex`, 40 trang, dựng lại 17-09-2026). Nó
`\input` chính `tables/num_*.tex` của bài nên không thể lệch số với bài; mỗi script `supp_*.py`
có cổng `RuntimeError` so từng giá trị trùng với macro/tabular của bài. Chạy SAU các script ở
trên (chúng đọc `tables/`):

```bash
python paper/AAMAS/supplement/make_prompts.py      # prompts.tex (prompt nguyen van)
python paper/AAMAS/supplement/make_questions.py    # questions.tex (10 cau hoi nguyen van)
python paper/AAMAS/analysis/supp_selfplay.py       # S5-S7: so van, xo so, luoi risk, prompt controls
python paper/AAMAS/analysis/supp_probes.py         # S8: cau hoi trong van
python paper/AAMAS/analysis/supp_scripted.py       # S9: doi thu scripted
python paper/AAMAS/analysis/supp_groups.py         # S10-S11: ban hai model, chon loc (~2 phut)
cd paper/AAMAS/supplement && latexmk -pdf supplement.tex
```

**Luật của thư mục paper:**

1. **Không gõ tay số đo được vào `main.tex`.** Mọi con số là macro do script sinh. Script
   có guard `RuntimeError` khi dữ liệu không còn khớp câu chữ.
2. **Một file, mỗi đoạn một dòng.** Không tách lại `sections/*.tex` rồi `\input`; không ngắt
   dòng giữa câu ở cột ~90 (viết mỗi đoạn văn, `\caption`, `\Description`, `\item` trên một
   dòng). Chỉ nội dung **do script sinh** được ở file riêng: `tables/num_*.tex` (macro) và
   `tables/tab_*.tex` (tabular) — gộp chúng vào `main.tex` thì chạy lại script sẽ không cập
   nhật bài mà không báo lỗi.
3. **Một nguồn dữ liệu và tên model**: `analysis/crsd_data.py` (`MODELS`, `SLUG`, payoff kỳ
   vọng). **Một theme figure**: `analysis/crsd_style.py` (Libertine, bảng màu an toàn mù màu,
   cổng kiểm cỡ chữ ≥ 7 pt, chồng chữ, bề rộng cột).
4. Không en/em dash, không mã nội bộ (E1..E7, tên file) trong phần người đọc thấy.
5. **Đoạn văn gần như không có số (17-09-2026, người dùng yêu cầu).** Chỉ giữ luật chơi và
   tham số thiết kế (6 người, 10 vòng, 40, 120, p* = 1/2). Kết quả đo được nói bằng chữ
   ("gần như mọi ghế", "ít hơn nhiều") và giá trị nằm ở bảng/figure của bài hoặc ở bảng
   "Numbers behind the main text" đầu mỗi mục kết quả của supplement. Abstract không có số kết
   quả. Đổi một chữ định tính thì kiểm lại giá trị trong bảng supplement tương ứng.

**Còn phải làm trước khi nộp:**

- [x] Kiểm từng mục `refs.bib` với nguồn gốc (16-09-2026; kiểm lại 17-09: sửa claim Tavoni/Willis, thêm pages Schmied, bỏ title khỏi `anon-if`).
- [x] 18-09-2026: bộ nộp tái lập được: build 2 PDF (`latexmk -pdf`, supplement cần main.aux) rồi `python paper/AAMAS/make_submission.py` → `paper/AAMAS/submission/{main.pdf, supplementary_material.zip}`. Script từ chối nếu thân bài ≠ 8 trang, có font Type 3, metadata có author/ngày/đường dẫn, text rò rỉ tên/repo/mã nội bộ, dash trong thân bài, hoặc zip > 25 MB (đã thử cho fail cả 3 loại). Clean-room build từ `git archive HEAD` cho PDF trùng khớp text (supplement cần 3 lượt pdflatex để mục lục ổn định).
- [ ] Trước 01-10: đăng ký abstract (dán OPENREVIEW_ABSTRACT.txt), điền `\acmSubmissionID`, build lại, chạy make_submission.py. Nộp full paper trước 08-10.
- [ ] 18-09-2026: wave E8 (350 ván, `plan/scripts/launch_e8.py`): `groupgoal` (goal = tổng tiền cả nhóm, p 0/0.1/0.9), `showpool` (in running pool; self-play p=0 + scripted always_0/always_4 ở p=0.9), `evprobe_p0` (câu hỏi giá trị ở p=0). Smoke server-side 4 arm × 1 ván Qwen sạch (parse_failed=0, câu goal/dòng pool có ở 60/60 prompt, pool cộng đúng, probe p=0 đúng 6/6). Đã phóng full. Gom về bằng lệnh launcher in ra (nhớ `--experiment`); `collect_probes.py` cần thêm `--task/--experiment` cho `exp_evprobe_p0`. Tiêu chí đọc chốt TRƯỚC khi xem số: groupgoal hạ trả tiền ở p=0 so với `wording` ≥ 2 đơn vị và P<0.01; showpool so số trả sau khi đã định với Table 5.
- [x] 17-09-2026: người dùng chốt bản Interface Focus KHÔNG nộp → đã bỏ đoạn "Overlap with concurrent work" và entry `anon-if`; ràng buộc trùng nộp ở aamas2027-plan §2 không còn áp dụng. Đừng thêm lại.
- [x] 17-09-2026: thêm `analysis/strategy.py` (vòng cuối, luật đơn giản, equilibrium, nước mở của Grok) + Figure 3/6 mới; môi trường vẽ hình: venv Python 3.12 (egttools) + font Libertine G.
- [x] Audit nộp bài 17-09-2026: claims↔macro, reviewer giả lập, supplement render + ẩn danh, metadata PDF (không ngày giờ, không đường dẫn). Abstract 247 từ.
- [x] Chuyển sang template AAMAS 2027 chính thức.
- [ ] Mọi tác giả có tài khoản OpenReview trước **17-09** (AoE).
- [ ] Đăng ký abstract **01-10** (dán `OPENREVIEW_ABSTRACT.txt`), nộp full paper **08-10**.
- [ ] Điền `\acmSubmissionID` sau khi đăng ký abstract.
- [ ] Cân nhắc chính sách dùng AI của AAMAS 2027 (khai báo nếu AI góp vào phương pháp).
- [ ] Chốt việc chuyển Q8 sang bản AAMAS hay giữ ở IF (plan §2.1).

### Việc tiếp theo

**E3b — quần thể hỗn hợp round-robin đủ 10 cặp** (§7.4), 600 ván/model, ~$82. Trước đó
**BẮT BUỘC pilot multi-slug** (~$0,5): chưa ai kiểm proxy production có phục vụ slug KHÁC
cái `-m` chọn hay không. E3a không dính rủi ro này nên đã chạy trước, đúng thứ tự §7.3.

```bash
python plan/scripts/launch_shard.py --account <acc> --model <slug>   --seat-models "self,<slug khac>,<slug khac>,self,self,self"   --risks 0.9 --langs en --reps 1 --task crg-e3b-pilot --label e3b_pilot
```

Hỏng thì hiện ra `[CRG_ERROR]` có `seat_model` kèm mã http; phương án lui là giữ đúng 1
ghế LLM + 5 ghế scripted (tức là E3a, không cần client thứ hai).

### Bài học vận hành — đọc trước khi phóng wave tiếp

**Quota là cửa sổ trượt 24h.** Wave E1+E2 phóng 12 shard một lượt thì 9 shard chết 403 ở
mức chi chỉ $0,24–$1,37, vì lưới dense grid đã đốt hết hạn mức của chính những account đó
vài giờ trước. E3a chạy hôm sau, cùng 18 account: **19/19 push OK, 0 lỗi quota**.

Cách đúng, đã dùng cho cả E1, E2 lẫn E3a:

```bash
python plan/scripts/probe_quota.py                        # loai account can (< ~$0,03)
python plan/scripts/run_fill.py --wave <w> --accounts <...>    # E1/E2
python plan/scripts/launch_e3a.py --accounts <...>             # E3a
```

Cả ba launcher chạy **theo đợt, rẻ trước**: account 403 lúc push bị loại khỏi đợt sau,
shard của nó quay lại hàng đợi (push hỏng không tốn tiền). Thứ tự rẻ-trước là thứ tạo khác
biệt — nó đóng xong các model rẻ trước khi quota cạn, để lại đúng model đắt cho đợt sau.

⚠️ **`probe_accounts.py` KHÔNG đủ để lập kế hoạch** — nó chỉ nói còn/hết key, và báo 19/23
xanh ngay trước khi 9/12 shard chết. `probe_quota.py` đo được tiền nhưng **trần đo chỉ
~$0,03** (proxy kẹp `max_output_tokens` xuống trần model trước khi tính cọc), nên chỉ phân
biệt "cạn" với "chưa cạn". Phép đo chính xác duy nhất vẫn là bước `push` (cọc $0,009).

⚠️ **429 "model đang quá tải" KHÁC 403 hết quota.** 429 là lỗi phía Kaggle, đổi account vô
ích — chỉ chạy lại sau. E3a gặp đúng một lần (grok `coop`), chạy lại là xong.

⚠️ **Gom xong PHẢI chạy `write_provenance.py`** — `to_wide_csv.py` không ghi
`PROVENANCE.json`. Với E2 còn phải chạy `collect_probes.py`, nếu không kết quả E2 mất theo
thư mục đã gitignore dù `results/` vẫn xanh cổng.

---

## Trạng thái tính đến 13-08-2026

> ⚠️ **10-09-2026: toàn bộ bảng data dưới đây giờ nằm ở `Legacy_Results/results/`, không
> còn ở `results/`.** Đó là ĐỒ CŨ — đóng băng, chỉ đọc. Vòng chạy mới ghi vào `results/`
> (rỗng lúc bắt đầu). Chỉ đọc/phân tích `Legacy_Results/` và viết vào paper **khi người
> dùng yêu cầu rõ ràng**. Xem [CLAUDE.md](../CLAUDE.md#kết-quả-lagecy_resultsresults-là-đồ-cũ-results-là-đồ-đang-chạy).

**Data cũ đã có (nay ở `Legacy_Results/results/`):**

| Arm | Model | Experiment | Số ván |
|---|---|---|---|
| open_source | 7 model (Qwen2.5 7/32/72B, Llama-3.1 8/70B, Gemma-2 9/27B) | exp_baseline | 60 mỗi model |
| open_source | 5 model | exp_comprehension | 120 mỗi model |
| open_source | 7 model | exp_riskframing | 60 mỗi model |
| open_source | 3 model nhỏ | exp_persona | 420 mỗi model |
| frontier | `gemini-3.1-flash-lite-preview` | exp_baseline | 60 (10 rep) |
| frontier | `gpt-5.4-nano` | exp_baseline | 30 (5 rep) — **chạy qua OpenAI API, không qua Kaggle proxy** |
| frontier | `gpt-5.4-nano` | exp_persona | 210 |
| frontier | `claude-haiku-4-5` | — | 1 ván smoke trong `archive/`, chưa có data thật |

## 🌅 Việc đầu tiên sáng 13-08-2026

Ngày A đã chạy đêm 12→13/08. **14/16 shard xong, $49.54.** Làm đúng 3 lệnh này:

```bash
# 1) Shard nào run xong mà chưa có data trên máy -> tải lại. KHÔNG chạy lại run.
python plan/scripts/redownload_all.py

# 2) Kiểm phủ đủ 60 cell chưa (exit 1 + liệt kê cell thiếu nếu chưa)
python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --dry-run

# 3) Ghi vào results/frontier/
python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --out results/frontier
```

**Mọi shard phóng trước 03:00 ngày 13/08 đều bị lỗi download do đường dẫn Windows 260 ký
tự** — run thành công, đã tốn tiền, nhưng data không xuống máy. Data VẪN CÒN trên server,
`redownload_all.py` lấy về. Đừng chạy lại run.

Kết quả đã có: nhánh bậc đỉnh đã ngừng, không còn tài liệu sống.
`gpt-5.6-sol` và `grok-4.20-reasoning` đã đủ 60 ván và nằm trong `results/frontier/`.
Còn 2 shard `gemini-3.1-pro` risk 0.1 (`hunhtrungkit`, `tnkiet`) — nếu chúng lỗi thì chạy
lại bằng `launch_shard.py` với account dự phòng `chiboiz`.

## Ngày B — PHẢI chạy theo 2 PHA

Ngày B = `claude-opus-5` (12 shard × 5 ván) + `grok-4.20-non-reasoning` (3 shard × 20 ván),
120 ván, ~$56. **Đừng phóng song song kiểu Ngày A** — 12/15 shard sẽ chết ở bước push.

```bash
python plan/scripts/stage_day_b.py --phase push   # tối đa 3 push cùng lúc, có chờ + retry
python plan/scripts/stage_day_b.py --phase run    # rồi mới phóng run song song hết
python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --out results/frontier
```

**Vì sao 2 pha:** `kaggle b t push` bị **từ chối ngay (rc=1, output RỖNG, 3 giây)** nếu
version trước còn đang validate (`status` = `Running`). Không có thông báo lỗi nào — rất dễ
chẩn đoán sai thành 429. Còn `run` thì phóng song song thoải mái vì nó dùng đúng model mình
chọn, không đập vào model mặc định của server như push.

**Trước khi phóng lại bất cứ thứ gì:** kiểm tiến trình mồ côi. `TaskStop`/Ctrl-C chỉ giết
shell cha, `launch_shard.py` con vẫn sống và vẫn push → xung đột.

```powershell
Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
  Where-Object { $_.CommandLine -match 'launch_shard|launch_day|stage_day' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

**Panel đang nhắm tới:** lưới **nhà cung cấp × bậc năng lực** — 13 model / 4 nhà cung cấp
(Anthropic 3, Google 4 gồm 1 open-weight, OpenAI 4, xAI 2). Proxy chỉ còn 4 nhà cung cấp;
ba nhà đã chết sạch đều là lab Trung Quốc (Alibaba/Qwen3, DeepSeek, Zhipu/GLM-5) nên nhánh
frontier hiện không có đại diện lab Trung Quốc — cần probe lại định kỳ.

## Ba sự thật đắt tiền, đừng phát hiện lại

1. **Local và server-side dùng 2 proxy khác nhau.** Local (`.env` → `mp-staging`) chỉ
   phục vụ 6 model. Server-side (`kaggle b t run`) phục vụ 28. Model báo 503 ở local
   hoàn toàn có thể chạy tốt server-side — đừng kết luận nó chết.
   → **Hệ quả đã thành quy ước: mọi ván sinh ra phải chạy SERVER-SIDE.** Không chạy
   `crg_task_server.py` ở local để lấy data, kể cả "chạy thử vài ván". Local chỉ dùng cho
   probe rẻ (`probe_all_models.py`, `probe_crg_prompt.py`) và kết quả probe không được ghi
   vào `results/`.

2. **503 là lỗi phía Kaggle, không phải hết quota.** Đã kiểm chứng bằng 3 account độc
   lập cho ra đúng cùng một tập 503. Đổi account không cứu được.

3. **Proxy đặt cọc tiền trước theo `max_output_tokens`, không theo token thực tiêu.**
   Không set cap tường minh thì model đắt bị 403 dù thực tế chỉ tốn vài xu. Xem chi
   tiết ở `plan/aamas2027-plan.md` §12.

## Quy ước cập nhật thư mục này

- Chạy xong một bước thì **tick checkbox** trong `aamas2027-plan.md` §11 và ghi số THẬT
  (chi phí, số ván, reach) vào cột kết quả — số ước tính sai tới ±3×.
- Availability thay đổi (model sống lại / chết đi) thì cập nhật `model-availability.md`
  kèm ngày probe.
- Kế hoạch đổi hướng thì sửa thẳng file, đừng tạo file `-v2`.
