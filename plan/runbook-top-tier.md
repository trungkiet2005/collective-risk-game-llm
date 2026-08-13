# RUNBOOK — chạy bậc đỉnh (top tier) trước

Đây là **hướng dẫn thực thi**, viết để một Claude session sau mở ra là chạy được ngay
không cần hỏi lại. Đọc [README.md](README.md) và [frontier-run-plan.md](frontier-run-plan.md)
trước để biết ngữ cảnh; file này chỉ nói **làm thế nào**.

Quyết định của người dùng (13-08-2026): chạy **bậc đỉnh trước**, không screen trước.

> **Rủi ro đã được nêu và người dùng vẫn chọn:** cả 4 model có thể cán trần 100% như
> `gemini-3.1-flash-lite`, tức tiêu ~$88 để thu 4 hàng không dùng được cho phép kiểm risk.
> Lý do vẫn hợp lý: "kể cả model frontier mạnh nhất cũng không phản ứng với risk" là claim
> mạnh hơn, và nếu chúng cán trần thì bản thân đó cũng là kết quả đăng được.
> **Đừng tự ý đổi sang screen-trước.** Nếu muốn đổi, hỏi người dùng.

---

## 1 · Bốn model cần chạy

| Model (slug dùng cho `-m`) | Nhà cung cấp | $/ván (ước) | $/60 ván (ước) |
|---|---|---|---|
| `claude-opus-5-default` | Anthropic | 0.6512 | 39.07 |
| `gemini-3.1-pro-preview` | Google | 0.5110 | 30.66 |
| `gpt-5.6-sol` | OpenAI | 0.2422 | 14.53 |
| `grok-4.20-0309-reasoning` | xAI | 0.0578 | 3.47 |

Tổng ước tính **~$88**. Mọi giá đều là **ước tính sai số ±3×** — xem
[model-availability.md](model-availability.md#phương-pháp-tính-giá). Vì vậy Bước 3
(đo giá thật) là **bắt buộc**, không được bỏ.

Sweep mỗi model = `exp_baseline`: **3 risk × 2 lang × 10 rep = 60 ván**, khớp chính xác
nhánh open-weight để data ghép chung được.

---

## 2 · 16 account và cách nạp credential

Kho credential **ngoài repo**: `D:\AI_PhD\GameTheory\kaggle_for_research\`
(đừng bao giờ dán key thật vào repo).

| Nguồn | Account | Kiểu nạp |
|---|---|---|
| `kaggle-api\*.txt` | `chiboiz`, `chinguyentran`, `chisboiz`, `chunaiu`, `trunkdabest`, `vinhdinhthien` | token — cả file là 1 dòng `KGAT_...` |
| `kaggle-api-2\*.md` | `acc1`…`acc5` | token — dòng bắt đầu bằng `KGAT_` trong file .md |
| `kaggle*.json` | `trungkiet`, `foundnotkiet`, `kit567`, `hunhtrungkit`, `tnkiet` | cặp `username`/`key` kiểu cũ |

> ❌ **BỎ QUA `trnnguynchis`** — login được nhưng xin Model Proxy key bị 403 thiếu xác
> minh SĐT. Còn đúng **16 account dùng được**.

**Mỗi account PHẢI có `KAGGLE_CONFIG_DIR` riêng**, nếu không credential đè lẫn nhau:

```bash
# --- kiểu token (kaggle-api/, kaggle-api-2/) ---
export KAGGLE_CONFIG_DIR="$HOME/.kaggle-runs/chiboiz"     # thư mục riêng cho account này
mkdir -p "$KAGGLE_CONFIG_DIR"
export KAGGLE_API_TOKEN="$(tr -d '\r\n' < 'D:/AI_PhD/GameTheory/kaggle_for_research/kaggle-api/chiboiz.txt')"
export PYTHONIOENCODING=utf-8        # SDK in emoji, cp1252 trên Windows sẽ crash

# --- kiểu .md (acc1..acc5): lấy dòng KGAT_ ---
export KAGGLE_API_TOKEN="$(grep -o 'KGAT_[A-Za-z0-9_-]*' 'D:/AI_PhD/GameTheory/kaggle_for_research/kaggle-api-2/acc1.md' | head -1)"

# --- kiểu json: copy file vào config dir, KHÔNG set KAGGLE_API_TOKEN ---
export KAGGLE_CONFIG_DIR="$HOME/.kaggle-runs/trungkiet"
mkdir -p "$KAGGLE_CONFIG_DIR"
cp 'D:/AI_PhD/GameTheory/kaggle_for_research/kaggle.json' "$KAGGLE_CONFIG_DIR/kaggle.json"
unset KAGGLE_API_TOKEN

# kiểm nhanh account sống chưa
kaggle benchmarks auth -y --env-file /tmp/probe.env && head -1 /tmp/probe.env
```

---

## 3 · Đo giá thật trước khi chia shard — BẮT BUỘC

Không được chia shard bằng số ước tính. Lý do cụ thể: nếu `claude-opus-5` thật ra đắt gấp
2× ước tính, một shard 10 ván sẽ **vỡ trần $10 giữa run**, và run server-side đứt giữa
đường là **mất toàn bộ data của shard đó** (`CRG_RESUME` chỉ hoạt động trong nội bộ một
run; mỗi run mới khởi động từ container sạch).

Chạy **1 shard nhỏ nhất (2 ván)** cho mỗi model, đọc chi phí thật, rồi mới tính:

```bash
# Sửa 3 dòng 83-85 của bản copy để thành sweep 2 ván
cp kaggle/benchmarks/crg_task_server.py /tmp/calib.py
#   RISKS -> "0.9"      LANGS -> "en"      REPS -> "2"

kaggle b t push crg-top-calib -f /tmp/calib.py
kaggle b t run  crg-top-calib -m claude-opus-5-default --wait 900
kaggle b t log  crg-top-calib -m claude-opus-5-default | grep -E "cost|usd|games_per"
```

### ĐÃ ĐO XONG — 12-08-2026, smoke 1 ván/model server-side (risk 0.9, en)

Cả 4 model: **COMPLETED, `parse_fail=0`, cap `max_completion_tokens=6000` áp dụng đúng**.

| Model | $/ván ĐO THẬT | Ước tính cũ | Lệch | $/60 ván thật | Ván/shard đã chọn |
|---|---|---|---|---|---|
| `grok-4.20-0309-reasoning` | **0.141571** | 0.0578 | **2.45× đắt hơn** | 8.49 | 20 → $2.83 |
| `gpt-5.6-sol` | **0.32409** | 0.2422 | 1.34× đắt hơn | 19.45 | 10 → $3.24 |
| `gemini-3.1-pro-preview` | **0.433008** | 0.5110 | 0.85× rẻ hơn | 25.98 | 10 → $4.33 |
| `claude-opus-5-default` | **0.58516** | 0.6512 | 0.90× rẻ hơn | 35.11 | 10 → $5.85 (Ngày B) |

Ngày A thật = 180 ván / **$53.92** (không phải $48.66 như ước tính).

**Bài học về estimator:** cột "độ khớp" trong [model-availability.md](model-availability.md)
đoán đúng hướng lệch. `grok` bị gắn nhãn *thiếu* (probe 99.7% input) và thật sự đắt hơn
2.45× — vì model reasoning sinh nhiều output token mỗi quyết định mà probe 1 chữ không
thấy được. Với model reasoning, **luôn đo thật, đừng suy từ probe input-heavy.**

**Nhắm ≤$5/shard chứ không $10.** Chừa gấp đôi để một cú đắt bất ngờ không giết run.
Kịch bản đã tránh được nhờ đo: `gpt-5.6-sol` định chia 3 shard × 20 ván, với giá thật
thành $6.48/shard = 65% trần — quá sát khi prompt tiếng Việt dài hơn. Đã chia 6.

---

## 4 · Chia sweep: chia theo risk và lang, KHÔNG chia theo rep

### Vì sao chia theo risk/lang là an toàn về seed

- `sampling_seed(rep, agent, round)` — không phụ thuộc risk/lang/shard
- Xổ số thảm hoạ: `random.Random(12345 + rep).random() < risk` — **chỉ keyed theo rep**
- `game_id = "{game_name}__{model_tag}__{lang}__rep{rep}"` — duy nhất theo (risk, lang, rep)

Nên chia sweep theo risk/lang cho ra kết quả **byte-identical** với một run không chia, và
các shard ghép lại không đụng game_id. Chia theo rep cũng an toàn về seed **nhưng cần sửa
code** (vòng lặp hiện là `for rep in range(REPS)` ở dòng 539, không có REP_START) — nên
tránh, chỉ dùng khi bắt buộc (xem [mục 8](#8--nếu-shard-vẫn-quá-đắt-chia-theo-rep)).

### Cách chia: sửa đúng 3 dòng, dòng 83-85

`kaggle b t run` **không nhận biến môi trường** — kích thước sweep phải nướng cứng vào file
lúc push. Nên mỗi shard = một lần push với 3 dòng này khác nhau:

```python
# kaggle/benchmarks/crg_task_server.py, dòng 83-85
RISKS = [float(x) for x in os.environ.get("CRG_RISKS", "0.9").split(",")]   # <- shard
LANGS = [s.strip() for s in os.environ.get("CRG_LANGS", "en").split(",")]   # <- shard
REPS = int(os.environ.get("CRG_REPS", "10"))                                # giữ 10
```

Ba cỡ shard có sẵn, chọn theo $/ván thật ở Bước 3:

| Cách chia | Số shard | Ván/shard | Sửa gì |
|---|---|---|---|
| theo risk | 3 | 20 | `RISKS="0.9"` / `"0.5"` / `"0.1"`, `LANGS="en,vn"` |
| theo lang | 2 | 30 | `LANGS="en"` / `"vn"`, `RISKS="0.9,0.5,0.1"` |
| theo risk×lang | 6 | 10 | cả hai đều 1 giá trị |

---

## 5 · Bảng phân công cụ thể — chạy 2 ngày

Dùng cỡ shard theo ước tính hiện tại. **Nếu Bước 3 cho giá khác, tính lại số shard** rồi
cập nhật bảng này.

### Ngày A — ĐÃ PHÓNG 12-08-2026 lúc 01:47 · 15 shard, 15 account, $53.92

Chia lại theo **giá đo thật**, không theo ước tính. Shard đắt nhất $4.33 = 43% trần $10.
Bảng sống nằm trong `plan/scripts/launch_day_a.py`; theo dõi bằng
`python plan/scripts/check_runs.py`.

| Model | Số shard | Chia theo | Ván/shard | $/shard | Account |
|---|---|---|---|---|---|
| `grok-4.20-0309-reasoning` | 3 | risk | 20 | 2.83 | chinguyentran, chisboiz, chunaiu |
| `gpt-5.6-sol` | 6 | risk×lang | 10 | 3.24 | trunkdabest, vinhdinhthien, acc1–acc4 |
| `gemini-3.1-pro-preview` | 6 | risk×lang | 10 | 4.33 | acc5, trungkiet, foundnotkiet, kit567, hunhtrungkit, tnkiet |

Dự phòng: `chiboiz` (đã dùng ~$1.6 cho smoke, còn ~$8.4). Quota nạp lại mỗi ngày nên
shard lỗi chạy lại được hôm sau trên đúng account đó.

<details><summary>Bảng phân công dự kiến ban đầu (theo giá ước tính — đã bị thay)</summary>

| ✓ | Account | Model | RISKS | LANGS | Ván | $ ước | $ thật |
|---|---|---|---|---|---|---|---|
| [ ] | `chiboiz` | `grok-4.20-0309-reasoning` | `0.9,0.5,0.1` | `en,vn` | 60 | 3.47 | |
| [ ] | `chinguyentran` | `gpt-5.6-sol` | `0.9` | `en,vn` | 20 | 4.84 | |
| [ ] | `chisboiz` | `gpt-5.6-sol` | `0.5` | `en,vn` | 20 | 4.84 | |
| [ ] | `chunaiu` | `gpt-5.6-sol` | `0.1` | `en,vn` | 20 | 4.84 | |
| [ ] | `trunkdabest` | `gemini-3.1-pro-preview` | `0.9` | `en` | 10 | 5.11 | |
| [ ] | `vinhdinhthien` | `gemini-3.1-pro-preview` | `0.9` | `vn` | 10 | 5.11 | |
| [ ] | `acc1` | `gemini-3.1-pro-preview` | `0.5` | `en` | 10 | 5.11 | |
| [ ] | `acc2` | `gemini-3.1-pro-preview` | `0.5` | `vn` | 10 | 5.11 | |
| [ ] | `acc3` | `gemini-3.1-pro-preview` | `0.1` | `en` | 10 | 5.11 | |
| [ ] | `acc4` | `gemini-3.1-pro-preview` | `0.1` | `vn` | 10 | 5.11 | |

Còn dư: `acc5`, `trungkiet`, `foundnotkiet`, `kit567`, `hunhtrungkit`, `tnkiet` — **giữ làm
dự phòng chạy lại shard lỗi**, đừng dùng hết trong một ngày.

### Ngày B — `claude-opus-5`, 6 account, ~$39

| ✓ | Account | RISKS | LANGS | Ván | $ ước | $ thật |
|---|---|---|---|---|---|---|
| [ ] | `acc5` | `0.9` | `en` | 10 | 6.51 | |
| [ ] | `trungkiet` | `0.9` | `vn` | 10 | 6.51 | |
| [ ] | `foundnotkiet` | `0.5` | `en` | 10 | 6.51 | |
| [ ] | `kit567` | `0.5` | `vn` | 10 | 6.51 | |
| [ ] | `hunhtrungkit` | `0.1` | `en` | 10 | 6.51 | |
| [ ] | `tnkiet` | `0.1` | `vn` | 10 | 6.51 | |

Giá thật của opus-5 là **$0.58516/ván** → shard 10 ván = **$5.85** (58% trần), chạy được
không cần chia nhỏ thêm. Tổng Ngày B = **$35.11**.

**Quota nạp lại mỗi ngày**, nên Ngày B dùng lại đúng các account của Ngày A được.

</details>

---

## 5b · Script đã có — dùng cái này, đừng làm tay

Toàn bộ mục 2, 4, 6 đã được gói vào script. Đường chạy thật là:

```bash
# 1) Xem sẽ chạy gì (không gọi API)
python plan/scripts/launch_day_a.py --dry-run

# 2) Phóng cả 12 shard song song, mỗi shard 1 account 1 tiến trình
python plan/scripts/launch_day_a.py

# 3) Theo dõi (đọc log, không gọi API) — chạy được ở terminal khác
python plan/scripts/check_runs.py
python plan/scripts/check_runs.py --watch      # tự làm mới 60s

# 4) Shard nào run xong mà chưa có data trên máy thì tải lại (KHÔNG chạy lại run)
python plan/scripts/redownload_all.py --dry-run
python plan/scripts/redownload_all.py

# 5) Gom kết quả — phải truyền CẢ HAI nguồn: plan/runs (bản launcher cũ) và D:/tmp/crgdl
python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --dry-run
python plan/scripts/merge_shards.py --src plan/runs D:/tmp/crgdl --out results/frontier
```

Một shard lẻ (chạy lại shard lỗi bằng account dự phòng):

```bash
python plan/scripts/launch_shard.py --account kit567 \
    --model gemini-3.1-pro-preview --risks 0.9 --langs en --reps 10
```

`launch_shard.py` tự làm: nạp credential đúng kiểu cho account → `kaggle b auth` kiểm
account sống → sinh file shard (thay dòng 83–85, và thay cả `@kbench.task(name=...)`
nếu `--task` khác) → `push` → đợi tới `Completed` → `run --wait` → lấy `status` + `log`
từng model → `download`. Mọi thứ ghi vào `plan/runs/<label>/shard.log`.

**Ba cái bẫy script đã xử lý, đừng làm lại bằng tay:**

- **Không bao giờ pipe output của run qua `head`.** SIGPIPE giết run giữa đường — tui đã
  mắc đúng lỗi này khi test: thư mục output tạo ra nhưng rỗng hoàn toàn.
- **`kaggle b t push <task>` bắt buộc khớp `name=` khai trong file**, nếu không nó báo
  `Task '<task>' not found in <file>`. Script tự đổi tên trong file khi cần.
- **`load_dotenv()` tìm .env từ thư mục của SCRIPT, không phải cwd.** Script ở nơi khác
  phải chỉ đường tường minh tới `.env` của repo.

---

## 6 · Chạy một shard bằng tay: 5 lệnh (chỉ khi cần gỡ lỗi)

Làm **một shard một lần**, xong hẳn mới sang shard kế. Đừng chạy nhiều shard đắt song song
trên **cùng một account** — tiền cọc cộng dồn và shard sau bị 403.

```bash
# (1) Nạp credential cho account của shard này — xem mục 2
export KAGGLE_CONFIG_DIR="$HOME/.kaggle-runs/<account>"
export KAGGLE_API_TOKEN=...          # hoặc copy kaggle.json
export PYTHONIOENCODING=utf-8

# (2) Sửa dòng 83-85 cho đúng shard, lưu thành file riêng để biết đang push cái gì
cp kaggle/benchmarks/crg_task_server.py /tmp/shard.py
#    ví dụ shard (risk 0.9, lang en): RISKS -> "0.9", LANGS -> "en", REPS giữ "10"

# (3) Push. Lệnh này TỰ CHẠY task 1 lần trên model mặc định của server
#     (gemini-3-flash-preview) để validate — guard ở dòng 104-106 tự thu về 1 ván
#     nên chỉ tốn ~$0.12. Chờ status Completed rồi mới run.
kaggle b t push collective-risk-baseline-srv -f /tmp/shard.py
kaggle b t status collective-risk-baseline-srv        # đợi "Status: Completed"

# (4) Chạy thật
kaggle b t run collective-risk-baseline-srv -m <model-slug> --wait 3600

# (5) TẢI VỀ NGAY — chưa tải là chưa có data
kaggle b t download collective-risk-baseline-srv -m <model-slug> \
        -o downloads/<model>-<risk>-<lang>/
```

**Thời gian:** `CRG_CONCURRENCY` mặc định 1 (tuần tự, để tránh 429) → khoảng **2–3 phút/ván**,
tức shard 10 ván ≈ 30 phút, shard 60 ván ≈ 2–3 tiếng. Model reasoning (`opus-5`,
`grok-reasoning`, `gemini-3.1-pro`) chậm hơn — đặt `--wait 3600` trở lên.

### Kiểm shard trước khi tính là xong

```bash
kaggle b t status collective-risk-baseline-srv        # phải Completed, không Errored
kaggle b t log collective-risk-baseline-srv -m <slug> | grep -E "parse_fail|cost|games"
```

`parse_fail` **phải bằng 0**. Nếu > 0, đừng dùng data đó — model trả lời sai định dạng,
phải điều tra trước. Ghi `$ thật` vào bảng ở mục 5.

---

## 7 · Gom shard lại thành dataset hoàn chỉnh

Đã có script sẵn, đã kiểm trên data thật:

```bash
# Xem trước, không ghi gì — kiểm phủ đủ 60 cell chưa
python plan/scripts/merge_shards.py --src downloads/ --dry-run

# Ghi thật vào results/frontier/<model_tag>/exp_baseline/
python plan/scripts/merge_shards.py --src downloads/ --out results/frontier

# Chỉ gom 1 model
python plan/scripts/merge_shards.py --src downloads/ --only claude-opus-5 --dry-run
```

Script tự kiểm và **exit 1** nếu chưa dùng được. Nó báo:

- `van : N / 60` — đủ 60 ván chưa
- `THIEU k cell` — liệt kê cell (risk, lang, rep) còn thiếu → biết phải chạy lại shard nào
- `parse_failed` — phải 0
- `luot` — phải đúng `60 × số ván` (3600 nếu đủ), lệch là shard bị cắt giữa đường
- `=> DAY DU` / `=> CHUA DUNG DUOC`

Ba điều script đã xử lý, đừng sửa lại:

- **Tách theo experiment**, không chỉ theo model. Cùng một model có nhiều experiment
  (`exp_baseline`, `exp_persona`) — gộp chung là trộn 2 thí nghiệm. Mặc định chỉ lấy
  `exp_baseline`, đổi bằng `--experiment`.
- **Lượt chỉ lấy từ shard thực sự đóng góp ván đó.** Lỗi thật đã gặp 12-08: shard smoke
  chạy đúng cell (0.9, en, rep0) nên `game_id` trùng shard thật → ván dedupe nhưng lượt
  thì không, cho ra **1 ván 120 lượt** (40 ván / 2460 lượt thay vì 2400). Sai lệch này
  âm thầm, **chỉ lộ ra ở phép kiểm 60-lượt/ván** — đó là lý do phép kiểm đó tồn tại.
- **Bỏ shard smoke khỏi merge** (`--exclude SMOKE`, mặc định) để dataset cuối không lẫn
  một ván có nguồn gốc khác. `--exclude ""` nếu muốn gộp cả smoke.
- **Trùng `game_id` mà nội dung khác nhau** thì báo động, vì nghĩa là 2 shard chạy trùng
  cell → cách chia sweep sai.

---

## 8 · Nếu shard vẫn quá đắt: chia theo rep

Chỉ làm khi $/ván thật khiến shard 10 ván vượt $7. Cần sửa code (vòng lặp hiện không có
offset rep). Thêm 2 dòng cạnh dòng 85 và sửa mọi chỗ `range(REPS)`:

```python
REP_START = int(os.environ.get("CRG_REP_START", "0"))
REPS      = int(os.environ.get("CRG_REPS", "10"))
# rồi thay range(REPS) -> range(REP_START, REP_START + REPS)
```

Có **2 chỗ** dùng `range(REPS)` — dòng 539 (`_load_game_checkpoints`) và vòng sweep chính
quanh dòng 613. **Phải sửa cả hai**, nếu không checkpoint và sweep lệch nhau.

Chia theo rep vẫn an toàn về seed (seed keyed theo rep, mỗi shard giữ rep riêng biệt) và
`game_id` vẫn duy nhất. Ví dụ 12 shard × 5 ván: `(risk, lang, REP_START=0, REPS=5)` và
`(risk, lang, REP_START=5, REPS=5)`.

---

## 9 · Xong rồi thì làm gì

- [ ] Tick checkbox + điền `$ thật` vào mục 5, và cập nhật bảng giá trong
      [model-availability.md](model-availability.md) bằng số đo được (thay cho số ước ±3×).
- [ ] Chạy `merge_shards.py` cho cả 4 model, đảm bảo đều `DAY DU`.
- [ ] **Kiểm trần ngay** — đây là câu hỏi khiến cả đợt chạy này tồn tại:

```bash
python -c "
import pandas as pd, glob
for p in glob.glob('results/frontier/*/exp_baseline/games.csv'):
    d = pd.read_csv(p)
    t = pd.crosstab(d.risk_probability, d.language, values=d.group_total, aggfunc='mean')
    print(p.split(chr(92))[-3] if chr(92) in p else p)
    print(t.round(1))
    print('reach:', (d.groupby(['risk_probability','language']).target_reached.mean()*100).round(0).to_dict())
    print()
"
```

  Đọc kết quả: mọi cell `group_total` ≥ 200 hoặc reach = 100% khắp nơi → **model dính trần**,
  không dùng được cho phép kiểm risk (nhưng vẫn là kết quả đăng được: "kể cả model frontier
  mạnh nhất cũng cán trần"). Có cell nào `group_total` quanh 120 với reach giữa 0 và 100% →
  **đó là cell uncensored**, chính là thứ cần tìm.

- [ ] Cập nhật [frontier-run-plan.md](frontier-run-plan.md) — panel đã có thêm 4 ô bậc đỉnh,
      quyết định tiếp bậc rẻ/giữa dựa trên kết quả này.

---

## 10 · Sự cố thường gặp

| Hiện tượng | Nguyên nhân | Xử lý |
|---|---|---|
| `403 max estimated cost ... exceeds your available quota (based on max_output_tokens)` | proxy đặt cọc trước = `max_output_tokens × giá output`; hoặc nhiều shard song song trên cùng account làm cọc cộng dồn | set `max_output_tokens` tường minh (512 model thường, 6000 model reasoning); chạy 1 shard/account/lần |
| `503 The requested model is currently unavailable` | model chết phía Kaggle | đổi account **không** cứu được (đã kiểm 3 account cùng kết quả); đợi và probe lại |
| `429 heavy load` | proxy quá tải | thử lại sau; giữ `CRG_CONCURRENCY=1` |
| `push` trả **rc=1 với output RỖNG** sau ~3 giây | **Version trước còn đang validate** (`kaggle b t status` = `Running`). Push trong lúc đó bị từ chối NGAY, KHÔNG có thông báo lỗi nào. Đây là nguyên nhân thật của việc **12/15 shard Ngày B chết**, rất dễ chẩn đoán sai thành 429/quota vì log có 429 lịch sử | `launch_shard.py` giờ gọi `wait_task_idle()` trước mỗi push. Dấu hiệu phân biệt: fail sau **3 giây** = bị từ chối ngay (không thể là lỗi validate, validate mất vài phút) |
| Tiến trình cũ vẫn push dù đã "stop" | `TaskStop` chỉ giết shell cha, **không giết `launch_shard.py` con**. Hai tiến trình push cùng task cùng account → xung đột | Kiểm bằng `Get-CimInstance Win32_Process ... CommandLine -match 'launch_shard'` rồi `Stop-Process -Force` trước khi phóng lại |
| `!! push validate THAT BAI` kèm 429, nhiều shard cùng lúc | **Phóng song song quá dày.** `push` chạy 1 ván validate trên model mặc định của server; N lệnh push đồng thời đập vào CÙNG model đó → 429 → validate Errored → push hủy. Gặp thật: **7/15 shard Ngày B chết** với `--stagger 20` | `launch_shard.py` giờ tự retry push 3 lần (chờ 120s, 240s). Khi phóng >8 shard, dùng `--stagger 150` trở lên. Shard đã chạy được KHÔNG bị ảnh hưởng — chỉ phóng lại đúng shard chết |
| `400 BatchScheduleBenchmarkTaskRuns` | quá 7 `-m` trong một lệnh | chia lệnh, tối đa 7 model |
| Run báo `Completed` nhưng `reply` rỗng | model dồn token vào reasoning channel, content trống | phải fail to tiếng, không được ghi thành ván đóng góp 0 — xem Ngày 1 của [frontier-run-plan.md](frontier-run-plan.md) |
| `KERNEL_WITHOUT_RUN` khi push | `.run()` bị bọc trong `if __name__=="__main__"`, hoặc dict result có key kiểu float | bản `crg_task_server.py` đã sửa cả hai — đừng copy lại từ `crg_task.py` |
| `kaggle b t log` trả rỗng, không báo lỗi | fetch song song > 3 luồng bị rate-limit **im lặng** | giữ concurrency ≤ 3, thử lại |
| Kết quả `charmap codec can't encode` | thiếu `PYTHONIOENCODING=utf-8` | set biến đó |
| Run đứt giữa đường | mỗi run server-side khởi động container sạch, `CRG_RESUME` không cứu được qua run | chạy lại cả shard đó trên account dự phòng |
| `download` báo `[Errno 2] No such file or directory` với đường dẫn rất dài | **giới hạn 260 ký tự của Windows.** Cây Kaggle sinh ra đã 174 ký tự (`<task>/<ver>/<model>/<runid>.download/results/frontier/<model_tag>/exp_baseline/checkpoints/risk-0p9__lang-en__rep-000.json`); để `-o` trong `plan/runs/<label>/` là 273 > 260 | **Data VẪN CÒN trên server — ĐỪNG chạy lại run, chỉ tải lại**: `python plan/scripts/redownload_all.py`. Tải về `D:/tmp/crgdl/<account>` (tổng ~200 ký tự) |

---

## 11 · Bốn nguyên tắc đừng vi phạm

1. **Tải về ngay sau mỗi run.** Chưa `download` là chưa có data, và run đứt là mất sạch.
2. **Một shard đắt một account một lần.** Tiền cọc cộng dồn → shard sau 403.
3. **Đo giá trước khi chia shard.** Số trong plan sai ±3×; chia bằng số ước là cách nhanh
   nhất để mất data giữa run.
4. **`parse_fail` phải bằng 0** trước khi coi shard là xong. Run 1 từng sinh ra "ván giả
   toàn số 0" vì lỗi này bị bỏ qua.
