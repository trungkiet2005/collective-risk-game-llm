# CLAUDE.md — quy ước làm việc trong repo CRSD-LLM

## AAMAS analysis update, 18 September 2026

Read [paper/AAMAS/REPRODUCE.md](paper/AAMAS/REPRODUCE.md) for the current figure and validation commands. Figure 3 shows low-to-high-risk answer and contribution contrasts; Figure 5 shows both comparison intervals and all five Grok compositions. Selection is a rare-mutation Fermi process with population size varied, not an isolated scoring-rule intervention. The Qwen repair changes all of its last-round zeros, not one seat. Do not restore the older interpretations from planning notes. Missing group-goal, printed-pool and zero-risk-probe controls remain untested.

Tài liệu trạng thái/lộ trình nằm ở [PROJECT.md](PROJECT.md). File này chỉ ghi các
quy ước bắt buộc khi sửa code.

## 👉 Việc đang làm: đọc [plan/README.md](plan/README.md) trước

`plan/` giữ kế hoạch **đang thực thi** + trạng thái data hiện có + checkbox tiến độ.
PROJECT.md đã lạc hậu so với thực tế; `plan/` mới là nguồn đúng cho câu "giờ làm gì tiếp".

- [plan/runbook-top-tier.md](plan/runbook-top-tier.md) — **đang chạy**: hướng dẫn thực thi bậc đỉnh (phân account, chia shard, gom result)
- [plan/model-availability.md](plan/model-availability.md) — 38 slug proxy: sống/chết/giá (probe 12-08-2026)

**Ba sự thật đắt tiền, đừng phát hiện lại:** (1) local và server-side dùng 2 proxy KHÁC
NHAU — local chỉ 6/38 model, server-side 28/38, nên 503 ở local KHÔNG có nghĩa model chết;
(2) 503 là lỗi phía Kaggle chứ không phải hết quota (đã kiểm bằng 3 account cho ra cùng tập
503) → đổi account vô ích; (3) proxy đặt cọc tiền trước theo `max_output_tokens` chứ không
theo token thực tiêu, nên không cap thì model đắt bị 403 dù thực tế tốn vài xu.

## ⛔ Kaggle Benchmarks: CHỈ chạy SERVER-SIDE, KHÔNG chạy local

**Quy ước bắt buộc từ 10-09-2026.** Mọi ván CRSD sinh bằng Kaggle Benchmarks phải chạy
server-side, tức là qua `kaggle b t push` rồi `kaggle b t run` (bọc sẵn trong
`plan/scripts/launch_shard.py` và các script `launch_*.py` / `run_dense_grid.py` gọi nó).
**KHÔNG chạy `python kaggle/benchmarks/crg_task_server.py` trên máy để sinh data**, kể cả
khi chỉ định "chạy thử vài ván cho nhanh".

Lý do — chính là sự thật số (1) ở trên: local đọc `.env` → `mp-staging` và chỉ phục vụ
**6/38 model**, server-side phục vụ **28/38**. Chạy local nghĩa là:

- panel bị cắt xuống còn những model nào tình cờ sống ở staging, tức là **không so sánh
  được** với data server-side đã có;
- gặp 503 rồi tưởng model chết, kết luận sai về availability;
- không có log `kaggle b t status` / artifact `.run.json`, nên không truy lại được run
  nào sinh ra file nào.

**Ngoại lệ duy nhất — probe, KHÔNG phải data.** Được phép gọi proxy local cho việc rẻ và
dùng một lần: `plan/scripts/probe_all_models.py` (liveness), `probe_crg_prompt.py` (kiểm
một lượt CRG parse được không), và `crsd/tests/test_kaggle_*.py`. Kết quả của những lệnh
này **không bao giờ** được ghi vào `results/` hay đưa vào paper.

## 🚨 Bẫy parse: `parse_failed=0` KHÔNG có nghĩa dữ liệu sạch

**Sửa 10-09-2026.** `parse_contribution` có hai nhánh: (1) dòng `CONTRIBUTION: n` định
dạng, (2) nếu không có thì **quét mọi chữ số trong văn bản** rồi lấy số cuối thuộc
{0,2,4}. Nhánh (2) là **có chủ ý** (model trả lời "I'll give 2" vẫn đọc được) — nhưng nó
cũng nuốt luôn ca reply **bị CẮT ở trần output trước khi kịp viết dòng CONTRIBUTION**, và
trả `parse_failed=False`. Con số ghi vào data khi đó được nhặt ra từ **phép tính trong
đoạn suy luận**, không phải từ một quyết định.

Vòng `while failed and attempt < MAX_PARSE_RETRIES` canh trên `failed` nên **không bao giờ
chạy** cho ca này. Hậu quả đo được trên `qwen3-235b`: 0,88% số lượt bị cắt → **39,5% số
ván hỏng**, tất cả xanh, và không rep nào sạch ở cả 11 mức risk → phải chạy lại từ đầu.

**Vì sao chỉ số trung bình không cứu được:** qwen trung bình **8 token/quyết định trên cap
512** (1,6%). Mọi cổng dựa trên `usage_output_tokens / n_decisions` đều xanh rực. Chỉ có
**ĐUÔI** phân bố vượt trần → phải kiểm **từng lượt**, không kiểm tổng hợp.

**Đã sửa trong `kaggle/benchmarks/crg_task_server.py`:**

- `_hit_output_cap(usage, cap)` — phát hiện reply chạm trần bằng `usage.output_tokens`.
- Vòng retry đổi thành `while (failed or truncated)`, và **nâng cap ×4 mỗi lần retry**
  (trần `MAX_RETRY_CAP = 8000`) — retry cùng cap thì cắt lại đúng chỗ cũ.
- Cắt hoài không cứu được → **ép `failed=True`**, để assertion cuối sweep từ chối run thay
  vì ship một con số bịa.
- Hồi quy: `crsd/tests/test_kaggle_truncation_retry.py` (5 test).

**Đã kiểm chứng trên data thật 10-09-2026** (50 ván qwen, 3.000 quyết định, cap 3000):
bản sửa nổ **6 lần** — đúng 6 lượt mà code cũ sẽ lặng lẽ bịa số. Sau retry với cap cao
hơn, cả 6 đều lấy được câu trả lời trọn vẹn, `parse_failed=0`.

Con số đóng đinh cho việc **cổng trung bình vô dụng**: cùng lô đó đo được **24,5
token/quyết định trên cap 3000 = 0,8%**. Bất kỳ cổng nào dựa trên trung bình đều xanh
tuyệt đối, trong khi 6 lượt ở đuôi vẫn vượt trần.

**Quy tắc rút ra, áp cho mọi model:** đặt `--max-out` phủ **đuôi** phân bố, đừng phủ trung
bình. Model có trung bình bé xíu vẫn cắt được ở đuôi.

## 🔁 `seed` KHÔNG làm văn bản model tái lập được (đo 10-09-2026)

Chạy lại **cùng một ô** `(risk, rep)` với **cùng `seed`** và `temperature=0.7` cho ra kết
quả khác nhau ở **31/54 ô = 57%** (`qwen3-235b`, so data cũ với data chạy lại; đã loại trừ
khả năng do bản sửa cắt-output — không ô nào trong số đó từng bị cắt).

**Phân biệt cho đúng, vì repo có hai loại seed:**

| Cái gì | Có tái lập không |
|---|---|
| RNG cấp game — xổ số thảm hoạ `Random(BASE+rep)`, hoán vị persona | ✅ **CÓ**. Chỉ phụ thuộc `rep`, nên chia shard theo risk/rep vẫn cho đúng cùng một thiết kế |
| Văn bản model sinh ra (`client.prompt(..., seed=seed)`) | ❌ **KHÔNG**. Proxy nhận `seed` nhưng không tái lập |

Nên câu "chia sweep theo risk/lang cho ra kết quả byte-identical" trong
`plan/scripts/merge_shards.py` **chỉ đúng cho phần RNG**, không đúng cho output LLM.

**Ba hệ quả bắt buộc nhớ:**

1. **Chạy lại một ô = một QUAN SÁT MỚI, không phải bản sao.** Trộn hai lần chạy của cùng
   một ô là trộn hai run. `to_wide_csv.py` mặc định **báo lỗi** khi gặp trùng `rep`; muốn
   giữ lần mới nhất thì phải khai báo rõ `--on-conflict newest`.
2. **Shard chết giữa chừng rồi chạy lại sẽ chơi lại những ô đã xong** — và ra số khác. Đây
   là tình huống thường gặp khi bị 429, không phải hiếm.
3. **Paper không được hứa tái lập theo seed.** Chỗ nói về reproducibility phải viết là:
   prompt + config + seed + code được công bố, và **các ô độc lập** tái lập được về mặt
   *thiết kế*; còn văn bản model thì không tái lập được vì proxy không đảm bảo. Hứa sai chỗ
   này là thứ reviewer kiểm được bằng cách chạy thử.

## Artifact `.task.json` / `.run.json` → `kaggle/benchmarks/artifacts/`

**Mọi file `<task-name>.task.json` và `<task-name>-run_id_*.run.json` phải nằm trong
[`kaggle/benchmarks/artifacts/`](kaggle/benchmarks/artifacts/)** — không để lăn lóc ở root
repo. Đây là nơi duy nhất chứa artifact của Kaggle Benchmarks, và nó được commit vào git
(đó là bản ghi duy nhất truy lại được run nào sinh ra file nào).

**Cái bẫy:** kbench ghi hai file này ra **thư mục đang đứng (CWD)**, chứ không phải cạnh
file task. Tệ hơn: `.task.json` được ghi ngay lúc **IMPORT**, vì `@kbench.task(...)` là
decorator — không cần chạy sweep, chỉ cần `import` module là file đã rơi ra.

**Đã bịt ở gốc 11-09-2026, có test hồi quy. Đừng sửa bằng cách dặn nhau `cd` trước khi
chạy — cách đó đã thất bại hai lần.** Có đúng HAI nguồn sinh ra file lạc, và cả hai đã bịt:

| Nguồn | Bịt bằng |
|---|---|
| `launch_shard.py` gọi `kaggle b t push` / `run`. Các launcher (`run_fill.py`, `launch_e3a.py`, `stage_day_b.py`) đều chạy nó với `cwd=REPO` → artifact rơi ra root | `run_cmd()` ghim `cwd=ARTIFACTS` cho mọi lệnh kbench. An toàn vì mọi đường dẫn truyền cho kbench đều TUYỆT ĐỐI (`-f`, `-o`, `--env-file`) |
| **`pytest` chạy từ root.** Nhiều test `import` `crg_task_server.py` → decorator ghi `.task.json` ra root mỗi lần chạy test | [`crsd/tests/conftest.py`](crsd/tests/conftest.py): fixture autouse `monkeypatch.chdir(tmp_path)`. Tiện thể chặn luôn bẫy `CRG_OUT` mặc định là đường dẫn TƯƠNG ĐỐI `results/frontier/...` — test quên đặt `CRG_OUT` sẽ ghi thẳng vào `results/` thật |

Hồi quy: [`crsd/tests/test_launch_shard_artifacts.py`](crsd/tests/test_launch_shard_artifacts.py) —
kiểm `run_cmd` chạy trong `artifacts/`, và có một cổng chặn quét gốc repo không còn
`*.task.json` / `*.run.json` nào. Lỡ rơi ra root thì `git mv` vào đây ngay, nhưng nếu nó
rơi ra được thì nghĩa là một trong hai chỗ trên đã hở — sửa chỗ hở, đừng chỉ dọn file.

Trùng tên là chuyện bình thường — cùng một task chạy lại sẽ đè lên `.task.json` cũ. Cứ đè,
vì bản cũ đã được track trong git nên lấy lại từ history được; đừng đẻ thêm hậu tố
`_v2`, `_new` để né trùng.

## Kết quả: `Legacy_Results/` là ĐỒ CŨ, `results/` là đồ đang chạy

**Từ 10-09-2026 thư mục `results/` cũ đã chuyển sang `Legacy_Results/results/`** (ban đầu
đặt sai chính tả `Lagecy_`, đã đổi — tài liệu cũ trong repo có thể còn tên sai, tra cả hai).

| Thư mục | Là gì | Được làm gì với nó |
|---|---|---|
| `Legacy_Results/results/` | Toàn bộ data cũ tới 10-09-2026 (1.4 GB): `open_source/`, `frontier/`, `frontier/dense_grid/`, `scripted_reference/`, `raw/` | **ĐÓNG BĂNG.** Chỉ đọc, không ghi đè, không xoá. |
| `results/` | Data vòng chạy MỚI (nhánh `aamas2027-e0`) | Nơi duy nhất được phép ghi kết quả |

**Đừng tự ý đọc / phân tích `Legacy_Results/` rồi viết vào paper.** Data cũ chỉ được lôi ra
khi **người dùng yêu cầu rõ ràng**; lúc đó mới đọc, phân tích, và ghi kết quả vào `paper/`.
Không có yêu cầu thì coi như thư mục đó không tồn tại — kể cả khi đang thiếu số để điền vào
một bảng. Lý do: data cũ trải nhiều panel/prompt khác nhau, trộn nhầm vào bảng mới là lỗi
âm thầm và rất khó phát hiện lúc review.

### ⛔ Layout `results/` — CHỐT 10-09-2026, chỉ MỘT định dạng

```
results/
├── DATA_CARD.md          <- tài liệu tự mô tả + loader chạy được. ĐỌC TRƯỚC KHI PHÂN TÍCH
├── PROVENANCE.json       <- ván nào từ đâu ra
└── <experiment>/<p>/<model_tag>/p<p>_<lang>_<model_tag>.csv
```

Ví dụ: `results/exp_baseline/0.9/openai-gpt-5.6-luna/p0.9_en_openai-gpt-5.6-luna.csv`

**KHÔNG có `results/raw/`, KHÔNG có `results/wide/`, KHÔNG có `games.csv`/`turns.jsonl`
trong `results/`.** Cả hai tầng đó từng tồn tại trong ngày 10-09 rồi bị bỏ. Chỉ còn wide
CSV 82 cột, một dòng = một ván, mỗi agent một khối cột (`agent1_strategies`,
`agent1_scores`, …) — học theo corpus
`Prisoner_Dilemma_Game/Dataset/data_fairgame_frontier_llm` nhưng cho 6 agent. Đặc tả đầy đủ:
[`results/DATA_CARD.md`](results/DATA_CARD.md) và `plan/aamas2027-plan.md` §9.

**Ba luật đường dẫn, vi phạm là vỡ ingest chứ không phải bị bỏ qua:**

1. Dưới `results/<experiment>/` **chỉ được có thư mục tên là số** — loader sắp xếp bằng
   `float(p.name)`. Một `README.md` lạc vào đó ném `ValueError` và giết cả lần đọc. Đó là
   lý do `DATA_CARD.md` nằm ở gốc `results/`.
2. `<p>` trong tên thư mục và tên file là **cùng một chuỗi literal**: `0.9` không phải
   `0.90`, `1` không phải `1.0`, `0` không phải `0.0`.
3. `<model_tag>` lặp nguyên văn trong tên file và **bằng ô `agent1_llm`** (bàn đồng nhất).
   Bàn dị thể (E3a/E3b) dùng tiền tố `mix__`.

**Cách ghi kết quả — dùng đúng hai script này, đừng viết tay:**

```bash
python plan/scripts/to_wide_csv.py --src plan/runs    # shard tai ve -> results/
python plan/scripts/verify_wide.py --expect-reps 10   # exit 1 neu hong
```

`verify_wide.py` là **cổng bắt buộc trước khi đưa số vào paper**. Ba cổng của nó bắt loại
lỗi âm thầm: (a) **cắt-output** — lượt thiếu marker `CONTRIBUTION:` nghĩa là parser đã bịa
ra quyết định từ đoạn suy luận mà vẫn báo `parse_failed=False`; (b) **cân bằng** — mọi
model phải có ĐÚNG cùng số ván trong một experiment; (c) **ngôn ngữ** — chỉ `en`.

⚠️ **`results/` KHÔNG chứa reasoning và prompt.** Chúng chỉ nằm trong `turns.jsonl` của
thư mục shard tải về (`plan/runs/`, đã gitignore) và `results/` **không dựng lại được**.
Muốn giữ corpus reasoning thì **backup `plan/runs/` ra ngoài git**. Đổi lại `results/` chỉ
~1,5 KB/ván nên track trọn vào git — 440 ván hiện tại chỉ 640 KB.

⚠️ **`plan/scripts/merge_shards.py` đã bị THAY THẾ** bởi `to_wide_csv.py`. Nó ghi layout CŨ
(`results/frontier/<model>/<exp>/games.csv`) — đừng dùng cho vòng chạy này.
`plan/scripts/fill_missing.py` cũng còn hardcode layout cũ.

⚠️ **Pipeline phân tích bản Interface Focus ĐANG HỎNG ĐƯỜNG DẪN, và đó là cố ý để nguyên.**
Hai lần dời thư mục (10-09-2026) làm nó trỏ trượt:

- `paper/Interface_Focus/revision/_data.py` có `ROOT = parents[2]`, tính từ vị trí cũ
  `paper/revision/`. Sau khi dời, `ROOT` ra `paper/` nên `RESULTS` thành `paper/results` —
  không tồn tại.
- `make_figures*.py` glob `../results/open_source/` và `../results/frontier/*/...`, lệch một cấp.

Cả hai **ra kết quả rỗng thay vì báo lỗi**. Đừng sửa và đừng chạy cho tới khi người dùng yêu
cầu dựng lại figure bản IF; lúc đó mới trỏ sang `Legacy_Results/results/`.

## Notebook Kaggle (`kaggle/experiments/*.py`)

- **Tên file zip output = `<tên file notebook>_results.zip`**, đặt ở
  `/kaggle/working/` (Cell 8 cuối mỗi notebook). Ví dụ:
  - `baseline.py`   → `/kaggle/working/baseline_results.zip`
  - `persona.py`    → `/kaggle/working/persona_results.zip`
  - `comprehension.py` → `/kaggle/working/comprehension_results.zip`

  Lý do: tải nhiều notebook về rồi bỏ vào `results/raw/` thì nhìn tên zip biết ngay
  của experiment nào — KHÔNG dùng tên chung `crsd_results.zip` nữa.

  Thư mục kết quả bên trong zip vẫn giữ `crsd_results/<model_short>/<experiment>/`
  (đừng đổi — script phân tích đang đọc theo cấu trúc này).

- Khi tạo notebook mới bằng cách copy từ notebook cũ: nhớ sửa `zip_path` ở Cell 8
  và dòng "Output:" trong docstring cho khớp tên file mới.

- Các bản trong `kaggle/experiments/archive/` là bản cũ KHÔNG dùng nữa — không cần
  sửa theo quy ước này trừ khi lấy ra dùng lại.

## Kaggle Benchmarks — credential & cách switch khi hết (Model Proxy)

**Kho credential (NGOÀI repo, KHÔNG check vào git — đừng dán key thật vào file này):**
`D:\AI_PhD\GameTheory\kaggle_for_research\`
- `kaggle-api\*.txt`   — 7 token `KGAT_...`, **tên file = tên account** (chiboiz, chinguyentran,
  chisboiz, chunaiu, trnnguynchis, trunkdabest, vinhdinhthien).
- `kaggle-api-2\*.md`  — 5 token `KGAT_...` (acc1–acc5), token là dòng bắt đầu bằng `KGAT_`.
- `kaggle-api-3\*.txt` — **6 token, thêm 10-09-2026** (acc06–acc11). Cùng định dạng token
  thô như `kaggle-api/`, không phải `.md` như `kaggle-api-2/`.
- `kaggle-api-4\*.txt` — **2 token, thêm 11-09-2026** (`kakagotto`, `tonngohan`). Cùng
  định dạng token thô, tên file = tên account.
- `kaggle*.json` (root) — 5 cặp `username/key` kiểu cũ (foundnotkiet, kit567, hunhtrungkit,
  tnkiet, trungkiet).

⚠️ **CÓ HAI thư mục tên `kaggle_for_research`, và chỉ MỘT cái được code đọc.**

| Đường dẫn | Vai trò |
|---|---|
| `D:\AI_PhD\GameTheory\kaggle_for_research\` | ✅ **CRED_ROOT thật** — `launch_shard.py` chỉ đọc ở đây |
| `D:\AI_PhD\kaggle_for_research\` | ❌ Bản cũ/trùng (thiếu `kaggle-api-3/`), kèm các thư mục rác `kaggle-config-<account>/` do `KAGGLE_CONFIG_DIR` đẻ ra |

Ngày 11-09-2026 token account mới được thả vào **thư mục sai** (`D:\AI_PhD\kaggle_for_research\`),
nên `ls` ở CRED_ROOT ra rỗng và tưởng người dùng chưa thêm gì. **Không tìm thấy account mới
thì kiểm cả hai chỗ trước khi kết luận**, rồi copy về CRED_ROOT — đừng trỏ `ACCOUNTS` sang
thư mục kia, vì hai cây credential song song là cách chắc chắn nhất để probe và run đọc lệch nhau.

Bảng ánh xạ tên → credential nằm ở `ACCOUNTS` trong
[`plan/scripts/launch_shard.py`](plan/scripts/launch_shard.py) — thêm account mới thì sửa
đúng chỗ đó, mọi script khác đọc lại từ đấy.

**Tổng 25 account. Probe 11-09-2026 (sau khi thêm lô `kaggle-api-4/`): 21 sống.**

| | Account |
|---|---|
| ✅ **21 sống** | acc1–acc5 · acc06, acc07, acc08, acc09, acc11 · chisboiz · chunaiu · foundnotkiet · hunhtrungkit · **kakagotto** · kit567 · tnkiet · **tonngohan** · trungkiet · trunkdabest · vinhdinhthien |
| ❌ **4 chết** | `chiboiz` · `chinguyentran` · `trnnguynchis` · `acc10` |

⚠️ **21 nhãn sống KHÔNG phải 21 user Kaggle — chỉ có 17 (đo 17-09-2026).** Bốn cặp nhãn là
cùng một user, cùng quota 24h, cùng không gian tên task: `acc06 = acc1` (minh2duy),
`acc07 = acc2` (boymagic), `acc08 = acc3` (trngthtnhi), `acc09 = acc4` (osduyminh). Giao
hai nhãn của một user cho hai shard **cùng tên task** trong một đợt thì shard sau **push đè**
file sweep của shard trước (rep_start/reps khác nhau → chạy nhầm rep) và cả hai rút chung
một quota. Bảng `ALIASES` trong `launch_shard.py`; `drive_neutral.py` từ chối kế hoạch vi phạm.
Tra user thật của một nhãn: URL `kaggle.com/benchmarks/tasks/<user>/...` trong `shard.log`.

⚠️ **Push validate từng chạy NGUYÊN sweep (sửa 17-09-2026).** Guard "1 ván khi validate"
cũ so tên `gemini-3-flash-preview`; server đổi mặc định sang `gemini-3.7-flash` (muộn nhất
14-09) nên guard im lặng hết tác dụng — validate crg-e6-neutral chạy 30 ván suốt 35 phút và
rút cạn một user. Giờ `launch_shard.py` luôn nướng `CRG_EXPECT_MODEL=<slug -m>` vào shard;
model nào khác import shard là validate và chỉ chơi 1 ván. Hồi quy:
`crsd/tests/test_kaggle_push_validation_guard.py` (có bẫy tên Haiku
`anthropic/claude-haiku-4-5@20251001` ≠ slug, nên so sau khi chuẩn hoá dấu).

Cả 4 account chết **cùng một lỗi**: `403 "missing phone/identity verification"` khi xin
Model Proxy key. Login và xem model list vẫn được, nên nhìn bằng mắt sẽ tưởng còn dùng
tốt — chỉ bước xin key mới lộ. `trnnguynchis` hỏng từ 12-08 và tới 11-09 vẫn chưa được
xác minh; `acc10` chết ngay từ lúc thêm vào. Danh sách chết **không đổi** giữa probe 10-09
và 11-09, tức 4 cái này hỏng bền chứ không phải trục trặc nhất thời.

⚠️ **Sức khoẻ account TRÔI theo thời gian** — mất 2 account trong 4 tuần. **Đừng tin danh
sách trong file này**, nó là ảnh chụp. Probe lại trước mỗi đợt chạy lớn:

```bash
python plan/scripts/probe_accounts.py          # 8 luong song song, ~1 phut
```

Account chết vẫn được GIỮ trong bảng `ACCOUNTS` (không xoá) để probe kiểm lại được — một
account 403 vì chưa xác minh SĐT có thể sống lại sau khi người dùng xác minh.

**Trần credit ngày: 21 account × $10 = ~$210/ngày.** Hai account mới (`kakagotto`,
`tonngohan`) chưa tiêu đồng nào, nên chúng là chỗ còn nhiều quota nhất — ưu tiên đẩy
shard đắt vào đó trước khi đụng tới các account đã chạy E1/E2/E3a.

⚠️ **Probe chỉ trả lời CÒN/HẾT, KHÔNG trả lời CÒN BAO NHIÊU.** Xin được key ≠ đủ quota cho
shard của bạn. Đã trả giá cho bài học này 2 lần: `trunkdabest` probe xanh nhưng push
validate 403 với tiền cọc chỉ **$0.0092** — tức còn chưa tới một xu. Và ước lượng quota
bằng cách parse `cost_usd` từ log cũng **sai** (nhiều shard không ghi trường đó, ra $0.00
trông như chưa tiêu gì).

**Cách đo quota còn lại rẻ và đúng nhất: chính bước `push` validate.** Nó gọi model mặc
định của server, đặt cọc ~$0.009, nên account gần cạn sẽ 403 ngay ở đó — thất bại không
tốn gì. Vì vậy khi cần nhiều account, cứ thử push lần lượt và lấy những cái qua được, đừng
cố đoán trước.

**Muốn ước lượng gần đúng (11-09-2026): đọc `.run.json` đã tải về, đừng đọc log.** Artifact
tải về có trường `results[].dictResult.usage_total_cost_usd` — đây mới là con số chi phí
thật, khác với `cost_usd` trong log (trường đó nhiều shard không ghi).

```bash
# tong chi phi + cua so truot 24h theo account, doc tu D:/tmp/crgdl/<account>/**/*.run.json
python - <<'EOF'
import json; from pathlib import Path; from collections import defaultdict
from datetime import datetime, timedelta, timezone
cut = datetime.now(timezone.utc) - timedelta(hours=24); agg = defaultdict(float)
for rj in Path("D:/tmp/crgdl").glob("*/**/*.run.json"):
    d = json.load(open(rj, encoding="utf-8")); t = d.get("endTime") or d.get("startTime")
    if not t or datetime.fromisoformat(t.replace("Z","+00:00")) < cut: continue
    agg[rj.relative_to(Path("D:/tmp/crgdl")).parts[0]] += sum(
        (r.get("dictResult") or {}).get("usage_total_cost_usd", 0) or 0 for r in d.get("results") or [])
for a, c in sorted(agg.items(), key=lambda x: -x[1]): print(f"{a:16} da tieu 24h ${c:6.2f}  con ~${10-c:5.2f}")
EOF
```

**Hai cái bẫy của con số này, nhớ cả hai:**

1. **Nó là CẬN DƯỚI, không phải số đúng.** Đo 11-09-2026: **37/152 run.json không có
   trường cost** (~24%), nên thực tế đã tiêu **nhiều hơn** số in ra. Đừng lấy nó để quyết
   định "còn đủ chỗ cho shard $5" — chỉ dùng để XẾP HẠNG account nào rảnh nhất.
2. **Quota là cửa sổ TRƯỢT 24h, không reset nửa đêm.** Cho nên tổng chi phí trọn đời vô
   nghĩa (nhiều account đã vượt xa $10 cộng dồn qua nhiều ngày) — chỉ phần trong 24h qua
   mới tính vào trần. Account chạy shard $7 lúc 22:00 thì 22:00 hôm sau mới dùng lại được.

**Cách nạp credential (2 kiểu, chọn 1 theo nguồn):**
```bash
export KAGGLE_CONFIG_DIR=<thư mục riêng cho account này>   # tránh đụng ~/.kaggle
# kiểu token (kaggle-api/, kaggle-api-2/, kaggle-api-3/, kaggle-api-4/):
export KAGGLE_API_TOKEN=KGAT_xxxxxxxx
# kiểu cũ (kaggle*.json): đặt username/key hoặc copy file thành $KAGGLE_CONFIG_DIR/kaggle.json
export KAGGLE_USERNAME=... ; export KAGGLE_KEY=...
```

**Lấy Model Proxy key rồi gọi (chuẩn OpenAI-compatible):**
```bash
kaggle benchmarks auth -y --env-file account.env   # ghi MODEL_PROXY_URL + MODEL_PROXY_API_KEY
# POST tới: <MODEL_PROXY_URL>/openapi/chat/completions
#   Authorization: Bearer <MODEL_PROXY_API_KEY>
#   body: {"model":"gpt-5.4-nano-2026-03-17","messages":[...],"max_completion_tokens":N}
```
- MODEL_PROXY_URL hiện tại: `https://mp-staging.kaggle.net/models`
- **Proxy key HẾT HẠN sau ~2 tiếng** (`MODEL_PROXY_EXPIRY_TIME`). Hết thì chạy lại
  `kaggle benchmarks auth` cùng account để làm mới — KHÔNG cần đổi account.
- Response trả kèm `usage.cost` (nanodollars) để theo dõi chi phí/quota.

**Khi 1 account hết quota / rate-limit / key hết hạn không xin lại được → switch:**
1. Chuyển sang account kế tiếp trong danh sách account còn sống — **probe lại bằng
   `probe_accounts.py`, đừng tin con số viết trong file này** (nó là ảnh chụp và đã lạc
   hậu ba lần: 16 → 19 → 21). Mỗi account 1
   `KAGGLE_CONFIG_DIR` riêng để creds không đè nhau).
2. Chạy lại `kaggle benchmarks auth` để lấy proxy key mới cho account đó.
3. Bỏ qua `trnnguynchis` cho tới khi được verify.
4. Muốn kiểm tra nhanh account nào còn sống: gọi thử `gpt-5.4-nano` với prompt 1 chữ
   (rẻ nhất) — có `"choices"` trong response là OK.
