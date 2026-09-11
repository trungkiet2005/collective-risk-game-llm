# Data card — `results/` (vòng chạy AAMAS 2027)

Kho kết quả của nhánh `aamas2027-e0`. Tài liệu tự mô tả cho bất cứ ai (người hay model)
viết code phân tích trên bộ này: đường dẫn, ý nghĩa từng cột, bất biến đã kiểm, loader
chạy được ngay.

Kế hoạch sinh ra bộ dữ liệu này: [`plan/aamas2027-plan.md`](../plan/aamas2027-plan.md).

> ⚠️ `Legacy_Results/` là kho **khác** và đã **đóng băng** — data cũ tới 10-09-2026, trải
> nhiều panel/prompt/vòng chạy khác nhau. Đừng trộn nó vào bảng của bộ này.

---

## 1. Tổng quan

| Thuộc tính | Giá trị |
|---|---|
| Trò chơi | Collective-risk social dilemma (Milinski et al., 2008) |
| Nhóm | 6 người chơi, vốn mỗi người 40, đóng góp mỗi vòng ∈ {0, 2, 4} |
| Mục tiêu | tổng đóng góp ≥ 120 sau 10 vòng |
| Nếu trượt | xổ số **cấp nhóm** một lần: với xác suất `p` mọi người mất hết |
| Số vòng | 10, cố định, **có nói trước cho agent** |
| Ngôn ngữ | `en` — chỉ tiếng Anh |
| Ván | **550** = 5 model × 11 mức risk × 10 rep |
| Lượt quyết định | 33.000 (mỗi ván 6 ghế × 10 vòng) |
| Parse hỏng | **0** |
| Thảm hoạ | 96 ván |
| Dung lượng | ~850 KB (chỉ wide CSV) |

**Đã xong: thí nghiệm B (lưới risk).** Chưa có ván nào cho E1, E2, E3a, E3b, E6, E5 —
xem `plan/aamas2027-plan.md` §7.

---

## 2. Cây thư mục

```
results/
├── DATA_CARD.md                <- file này
├── PROVENANCE.json             <- ván nào từ đâu ra
├── exp_evprobe_probes.jsonl    <- câu trả lời probe của E2 (xem dưới)
├── exp_evprobe_probes.csv      <- cùng nội dung, dạng bảng phẳng
└── <experiment>/         <- exp_baseline, exp_nohint, exp_evprobe, …
    └── <p>/              <- 0, 0.1, 0.2, … 1   (tên thư mục = con số)
        └── <model_tag>/
            └── p<p>_<lang>_<model_tag>.csv
```

### ⚠️ `exp_evprobe`: kết quả nằm NGOÀI wide CSV

Với mọi experiment khác, wide CSV là toàn bộ dữ liệu. **E2 thì không.** Wide CSV mô tả
ván chơi, còn phép đo của E2 là *model có hiểu luật và so sánh được kỳ vọng không* — thứ
đó nằm ở **`exp_evprobe_probes.jsonl`** (4.500 bản ghi: 150 ván × 30 câu), một dòng một
câu hỏi, kèm `question_text`, `raw_response`, `parsed_answer`, `ground_truth`, `correct`.

Hai file đó nằm ở **gốc `results/`** chứ không nằm dưới `results/exp_evprobe/`, vì luật
đường dẫn chỉ cho phép thư mục **tên là số** dưới `<experiment>/` — một file lạc vào đó
làm `float(p.name)` ném `ValueError` và giết cả lần đọc. Cùng lý do với `DATA_CARD.md`.

Đọc nhanh:

```python
import pandas as pd
pr = pd.read_json("results/exp_evprobe_probes.jsonl", lines=True)
pr.groupby("category").correct.mean()   # rules 1.000 · value 0.772
pr.groupby("model").correct.mean()
```

Câu hỏi probe là **lệnh gọi riêng, không chèn vào lịch sử ván**, nên ván trong
`exp_evprobe/` vẫn đúng điều kiện baseline; chênh lệch so với `exp_baseline` là nhiễu lấy
mẫu chứ không phải hiệu ứng của probe.

Ví dụ: `results/exp_baseline/0.9/openai-gpt-5.6-luna/p0.9_en_openai-gpt-5.6-luna.csv`

**Chỉ một định dạng: wide CSV.** Không có `results/raw/`, không có tầng `wide/`.

> ⚠️ **`results/` KHÔNG chứa reasoning và prompt.** Chúng chỉ nằm trong `turns.jsonl` của
> thư mục shard tải về (`plan/runs/`, `D:/tmp/crgdl/` — đều gitignore), và `results/`
> **không dựng lại được** chúng. Muốn giữ corpus reasoning thì phải backup thư mục shard.
> Đổi lại: `results/` gọn ~1,5 KB/ván nên track trọn vào git được.

Sinh và kiểm:

```bash
python plan/scripts/to_wide_csv.py --src <thu-muc-shard> --only-model <model_tag>
python plan/scripts/verify_wide.py --expect-reps 10
```

**Quy tắc đường dẫn (không có ngoại lệ):**

- Dưới `<experiment>/` **chỉ được có thư mục tên là số**. Loader sắp xếp bằng
  `float(p.name)`; một file `README.md` lạc vào đó làm **vỡ cả ingest** chứ không bị bỏ
  qua. Đó là lý do file này nằm ở gốc `results/`.
- `<p>` trong tên thư mục và tên file là **cùng một chuỗi literal**: `0.9` không phải
  `0.90`, `1` không phải `1.0`, `0` không phải `0.0`.
- `<model_tag>` lặp nguyên văn trong tên file và **bằng ô `agent1_llm`** (bàn đồng nhất).
  Bàn dị thể dùng tiền tố `mix__`.

Glob dùng được:

```python
root.glob("*/*/*/*.csv")                                # tất cả
root.glob("exp_baseline/0.9/*/*.csv")                   # mọi model ở p = 0.9
root.glob("exp_baseline/*/openai-gpt-5.6-luna/*.csv")   # một model, mọi mức risk
```

---

## 3. Hiện có gì

Cả 5 model đều **11 mức risk (0.0 → 1.0, bước 0.1) × rep 0–9 = 110 ván**.

| model_tag | Nguồn |
|---|---|
| `anthropic-claude-haiku-4-5-20251001` | nhập lại từ `Legacy_Results/` (§6) |
| `google-gemini-3.5-flash-lite` | nhập lại từ `Legacy_Results/` |
| `openai-gpt-5.6-luna` | nhập lại từ `Legacy_Results/` |
| `xai-grok-4.20-0309-non-reasoning` | nhập lại từ `Legacy_Results/` |
| `qwen-qwen3-235b-a22b-instruct-2507` | **chạy mới 10-09-2026**, $0,97 |

Lưới **cân bằng tuyệt đối**: số ván của một model do **thiết kế** quyết định, không bao
giờ do **giá** model quyết định — dù `claude-haiku-4-5` đắt gấp 6,6 lần `qwen3-235b`.

**Rep là khoá ghép giữa các mức risk.** Xổ số thảm hoạ chỉ phụ thuộc `rep`, nên cùng `rep`
ở hai mức risk khác nhau dùng **chung một số ngẫu nhiên** (common random numbers) — kỹ
thuật giảm phương sai khi so risk theo cặp. Đừng phá tính chất này bằng cách lọc rep khác
nhau cho từng mức.

### Tỉ lệ đạt mục tiêu (%), 10 ván mỗi ô

| model | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `claude-haiku-4-5` | 80 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| `gemini-3.5-flash-lite` | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| `gpt-5.6-luna` | 0 | 80 | 90 | 90 | 70 | 80 | 90 | 50 | 90 | 70 | 60 |
| `qwen3-235b` | 0 | 0 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `grok-4.20-non-reasoning` | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |

**Số thô, chưa kiểm định — đừng trích thẳng vào paper.** n = 10/ô nên phải dùng
permutation/exact test, không dùng t-test.

Ba kiểu hành vi tách bạch rõ: (a) **mù rủi ro** — haiku, gemini, grok đạt 100% ở *mọi* mức
kể cả `p = 0`, nơi không có thảm hoạ nào để tránh, nên đó không phải hợp tác có tính toán;
(b) **phản ứng có điều kiện** — `gpt-5.6-luna`, model duy nhất phản ứng với `p = 0`;
(c) **gần như bỏ mặc** — `qwen3-235b`, gần như không bao giờ đạt target kể cả ở `p = 1.0`
(thảm hoạ chắc chắn xảy ra nếu trượt).

---

## 4. Schema — 82 cột

### Khối A — định danh ván & thiết kế (12)

| cột | dtype | miền | nghĩa |
|---|---|---|---|
| `game_id` | str | duy nhất trong file | định danh ván, mã hoá cả game config/model/lang/rep |
| `experiment` | str | `exp_baseline`, … | tên thí nghiệm |
| `language` | str | `en` | bằng token `<lang>` trong tên file |
| `rep` | int | 0–9 | lần lặp — **khoá ghép giữa các mức risk** |
| `seed` | int | | seed tái lập (xem cảnh báo §6) |
| `persona_set` | str | `personas_default` | file persona đã dùng |
| `persona_seats` | str | `NNNNNN` | tính cách theo ghế thực tế (N/C/S) sau khi hoán vị |
| `memory_mode` | str | `full_history` | |
| `opponent_profile` | str | `""` | chỉ dùng ở E3a |
| `framing` | 0/1 | 0 | có framing khí hậu không |
| `risk_framing` | str | `lottery` | cách nêu rủi ro |
| `show_computed_totals` | 0/1 | 0 | prompt có đưa sẵn tổng tính trước không |

### Khối B — luật chơi (9)

`n_players` (6) · `endowment` (40.0) · `contribution_options` (`"[0, 2, 4]"`) · `target`
(120.0) · `risk_probability` (float, = `<p>` trong đường dẫn) · `n_rounds_is_known` (True) ·
`max_rounds` (10) · `played_rounds` (10) · `agents_communicate` (False)

Giữ nguyên tên slot của FAIRGAME để tương thích với corpus prisoner's-dilemma; chúng không
đổi trong bộ hiện tại nên **đừng dùng làm biến phân tích**.

### Khối C — kết cục nhóm (7)

| cột | dtype | nghĩa |
|---|---|---|
| `group_contributions` | str→list, dài 10 | tổng đóng góp cả nhóm **từng vòng** |
| `pot_cumulative` | str→list, dài 10, không giảm | quỹ chung tích luỹ sau mỗi vòng |
| `group_total` | float | `pot_cumulative[-1]` |
| `target_reached` | 0/1 | `group_total >= target` |
| `catastrophe` | 0/1 | kết quả xổ số — **chỉ xổ khi trượt target** |
| `mean_payoff` | float | trung bình payoff 6 ghế |
| `n_parse_failures` | int | tổng lượt hỏng cả ván — **cổng QA, phải bằng 0** |

Khối này **không có trong corpus prisoner's-dilemma** — đặc thù CRSD, nơi kết cục thuộc về
cả nhóm chứ không phải từng cặp.

### Khối D — mỗi agent i = 1…6 (9 cột × 6 = 54)

| cột | dtype | nghĩa |
|---|---|---|
| `agent{i}_name` | str | `Player_1` … `Player_6` |
| `agent{i}_llm` | str | model/chính sách **thật** cầm ghế này (`scripted:always_4` ở E3a) |
| `agent{i}_personality` | str | `neutral` / `cooperative` / `selfish` |
| `agent{i}_knows_opponent_with_prob` | int | 0 — slot FAIRGAME, giữ để tương thích |
| `agent{i}_strategies` | str→list, dài 10 | **đóng góp từng vòng**, ∈ {0,2,4} |
| `agent{i}_scores` | str→list, dài 10, không tăng | **tài khoản riêng còn lại sau mỗi vòng** |
| `agent{i}_messages` | str→list | `[]` (câu pledge ở E5) |
| `agent{i}_payoff` | float | payoff cuối **sau xổ số**: 0 nếu `catastrophe`, ngược lại `scores[-1]` |
| `agent{i}_parse_failures` | int | số vòng hỏng/bị cắt của riêng ghế này |

#### ⚠️ `agent{i}_scores` khác `agent1_scores` của corpus PD

Ở corpus prisoner's-dilemma, `agent1_scores[t]` là **penalty vòng t** và phụ thuộc nước đi
của đối thủ. Ở CRSD **không tồn tại payoff theo vòng**: tiền chỉ kết toán một lần ở cuối,
sau xổ số cấp nhóm.

Nên ở đây `agent{i}_scores` = **tài khoản riêng còn lại sau mỗi vòng**
(`endowment − cumsum(strategies)`). Nó **là hàm tất định của `agent{i}_strategies`** — cố ý
như vậy để code loader dùng chung được với corpus PD: cùng `ast.literal_eval`, cùng ra list
10 số cùng đơn vị tiền. Phần "phụ thuộc người khác" mà cột `scores` của PD mang, ở CRSD nằm
ở **cấp nhóm**, trong `pot_cumulative`.

---

## 5. Loader

Các cột list là **Python literal dấu nháy đơn, KHÔNG phải JSON** — dùng `ast.literal_eval`.

```python
import ast, pathlib
import pandas as pd

ROOT = pathlib.Path("results")
LIST_COLS = (["group_contributions", "pot_cumulative"]
             + [f"agent{i}_{k}" for i in range(1, 7) for k in ("strategies", "scores", "messages")])

def load(experiment="exp_baseline") -> pd.DataFrame:
    frames = []
    for f in sorted((ROOT / experiment).glob("*/*/*.csv"),
                    key=lambda p: float(p.parent.parent.name)):
        df = pd.read_csv(f)
        for c in LIST_COLS:
            df[c] = df[c].map(ast.literal_eval)
        df["model_tag"] = f.parent.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

df = load()
print(df.groupby(["model_tag", "risk_probability"])["target_reached"].mean().unstack())
```

Khoá ghép một ván: `(experiment, model_tag, risk_probability, rep)`.

---

## 6. Nguồn gốc, cảnh báo, bất biến

### 4/5 model nhập lại từ `Legacy_Results/`

440 trong 550 ván **không phải chạy mới** — nhập từ
`Legacy_Results/results/frontier/dense_grid/` bằng
[`plan/scripts/import_legacy_b.py`](../plan/scripts/import_legacy_b.py). Nguồn từng model
ghi trong [`PROVENANCE.json`](PROVENANCE.json). Data cũ chạy đúng config baseline tiếng Anh
trên lưới 11 điểm nên dùng lại được nguyên vẹn.

**`risk_framing` và `show_computed_totals` không tồn tại trong schema cũ** — được điền mặc
định `lottery` / `0`, đúng cấu hình baseline gốc, nhưng là **suy ra** chứ không đọc từ file.
Ván chạy mới có giá trị thật.

### `qwen3-235b` phải chạy lại toàn bộ

Data cũ của nó có 990 ván nhưng **hỏng**: ở 0,88% số lượt model tính nhẩm dài rồi **bị cắt
trước khi kịp viết dòng `CONTRIBUTION:`**; parser rơi xuống nhánh quét-prose, nhặt một chữ
số ra từ chính đoạn suy luận, và vẫn trả `parse_failed=False`. Một ván có 60 quyết định nên
0,88% lượt hỏng làm **39,5% số ván** sai quỹ đạo, rải đều khắp 11 mức risk → không rep nào
sạch ở cả 11 mức.

110 ván hiện tại chạy mới 10-09-2026 với `--max-out 3000` và bản sửa retry-khi-bị-cắt.
Trong lô đó cơ chế mới **nổ 6 lần** — đúng 6 lượt mà code cũ sẽ bịa số.

> 🚨 **Chỉ số trung bình KHÔNG phát hiện được lỗi này.** qwen trung bình 24,5 token/quyết
> định trên cap 3000 = **0,8%** — mọi cổng dựa trên `usage_output_tokens / n_decisions` đều
> xanh rực. Chỉ **đuôi** phân bố vượt trần, nên phải kiểm **từng lượt**.

### ⚠️ `seed` KHÔNG làm văn bản model tái lập được

Chạy lại cùng một ô `(risk, rep)` với cùng `seed` và `temperature=0.7` cho kết quả khác
nhau ở **31/54 ô = 57%** (đo trên qwen, đã loại trừ ảnh hưởng của bản sửa cắt-output).

| Cái gì | Tái lập? |
|---|---|
| RNG cấp game (xổ số thảm hoạ, hoán vị persona) | ✅ có — chỉ phụ thuộc `rep` |
| Văn bản model sinh ra | ❌ không — proxy nhận `seed` nhưng không tái lập |

**Hệ quả cho paper:** không được hứa tái lập theo seed. Nói đúng là: prompt + config + seed
+ code được công bố, các ô độc lập tái lập được về mặt *thiết kế*, còn văn bản model thì
không. Hứa sai chỗ này reviewer kiểm được bằng cách chạy thử.

**Hệ quả khi gom:** chạy lại một ô = một **quan sát mới**, không phải bản sao.
`to_wide_csv.py` mặc định **báo lỗi** khi trùng `rep`; muốn giữ lần mới nhất phải khai báo
`--on-conflict newest`.

### Bất biến — `verify_wide.py` kiểm, exit 1 nếu vi phạm

- Mọi cột list dài đúng `played_rounds`.
- `sum(agent{i}_strategies)` từng vòng == `group_contributions`.
- `pot_cumulative` == cumsum(`group_contributions`); `group_total` == `pot_cumulative[-1]`.
- `target_reached` == (`group_total >= target`).
- `catastrophe` == 0 bất cứ khi nào `target_reached` == 1.
- `agent{i}_scores` không tăng; `agent{i}_payoff` == 0 nếu `catastrophe`, ngược lại `scores[-1]`.
- **Cổng cắt-output:** mọi `agent{i}_parse_failures` == 0 (đếm cả lượt thiếu marker
  `CONTRIBUTION:`, không chỉ cờ `parse_failed`).
- **Cổng ngôn ngữ:** `language` ∈ {`en`}.
- **Cổng cân bằng:** trong mỗi experiment, mọi model có **đúng cùng số ván**.
- `risk_probability` trong file khớp thư mục; `agent1_llm` khớp `model_tag`; không trùng
  `(experiment, model, risk, rep)`.

Trạng thái 10-09-2026: **550/550 ván qua hết, 0 vi phạm.**
