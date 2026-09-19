# Dựng lại figure bằng TikZ

> **Bản dùng trong paper (19-09-2026): `paper/AAMAS/figures/fig_game_designs.pdf`** là Figure 1 (`fig:overview`) của `paper/AAMAS/main.tex`: bố cục `figure_biolinum.tex`, màu `palettes/slate_mono.tex`. `bash palettes/build_palettes.sh` dựng `palettes/pdf/fig1_08_slate_mono.pdf` rồi chép sang `figures/` (xem mục 9). `figure_biolinum.pdf` là cùng bố cục ở bảng màu cũ (vivid), không còn được paper dùng. Bố cục Biolinum khác các biến thể font còn lại ở hai điểm: (1) đã **nén còn 188 × 90 mm** (giữ nguyên cỡ chữ, chỉ tiêu đề panel giảm từ 15.8 xuống 14 pt; bớt khoảng trắng, robot ở bốn ô design còn rộng 19.1 mm, icon nhỏ lại) để thân bài vẫn đúng 8 trang; (2) thứ tự model theo bài: Haiku, Flash-Lite, Luna, Qwen, Grok. Mọi mô tả kích thước 188 × 106 mm bên dưới là của `figure.tex` và các biến thể font khác. `qa/validate.py` chỉ kiểm `figure.pdf`; bản Biolinum đã qua cùng các kiểm tra (chữ không chồng nhau, không đè pixel icon, đủ 5 nhãn Fixed, font có ToUnicode), chỉ còn cảnh báo sẵn có về viền alpha 1–2/255 ở `group_mixed_tables.png`, `logo_claude.png`, `logo_gemini.png`.

Bộ này dựng lại figure trong ảnh được cung cấp thành PDF một trang, kích thước **188 × 106 mm**. PDF được biên dịch thực sự bằng **pdfLaTeX + TikZ**, không phải đặt nguyên ảnh vào PDF và không dùng OCR để tạo lớp chữ.

## Tệp chính

| Tệp | Nội dung |
|---|---|
| `figure.pdf` | Figure hoàn chỉnh, chữ có thể chọn, tìm kiếm và sao chép. |
| `figure.tex` | Mã nguồn TikZ đầy đủ, có chú thích và các macro bố cục. |
| `assets/` | 19 PNG RGBA đã tách nền; `manifest.json` ghi vùng cắt và kích thước. |
| `figure_preview.png` | Bản xem trước được render từ PDF, chiều rộng 2400 px. |
| `assets_contact_sheet.png` | Bảng xem toàn bộ asset trên nền caro để kiểm tra độ trong suốt. |
| `extract_assets.py` | Script tách lại asset từ đúng ảnh đầu vào, không sinh hình mới. |
| `qa/` | Kết quả kiểm tra, chữ trích xuất từ PDF, thông tin font và script kiểm tra lại. |

## 1. Biên dịch

Giữ `figure.tex` và thư mục `assets/` cùng cấp. Mở terminal tại thư mục này và chạy:

```bash
pdflatex -interaction=nonstopmode -halt-on-error figure.tex
```

Hoặc trên hệ thống có Bash:

```bash
bash build.sh
```

Dùng compiler **pdfLaTeX**. Các gói LaTeX cần có: `standalone`, `tikz`/PGF, `graphicx`, `amsmath`, `lmodern`, `tgheros` và `glyphtounicode`. Không cần Python để biên dịch figure, và không có font riêng cần cài thêm ngoài các gói LaTeX này.

Để dùng trên Overleaf, tải cả bộ ZIP, đặt `figure.tex` làm tệp chính và chọn compiler `pdfLaTeX`. Không chỉ tải riêng tệp `.tex`, vì figure cần các PNG trong `assets/`.

## 2. Chèn vào bài báo

Trong preamble của bài báo:

```latex
\usepackage{graphicx}
```

Trong bài báo hai cột:

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figure.pdf}
  \caption{The collective-risk game and the four experimental designs.}
  \label{fig:game-designs}
\end{figure*}
```

Dùng `figure` thay cho `figure*` trong tài liệu một cột. Nên giữ chiều rộng hiển thị gần 180–190 mm để các nhãn nhỏ còn dễ đọc. Chèn PDF thay vì ảnh preview để giữ chữ và các đường vẽ dạng vector.

## 3. Bộ asset: 19 PNG nền trong suốt

**Năm cụm hoàn chỉnh**, mỗi cụm giữ robot và bàn chung với nhau:

- `group_game.png`: sáu robot, bàn và tiền ở phần The game.
- `group_self_play.png`: cụm Self-play.
- `group_prompt_tests.png`: cụm Prompt tests.
- `group_scripted_partners.png`: cụm Scripted partners, đã loại nhãn chữ Fixed.
- `group_mixed_tables.png`: cụm Mixed tables.

**Năm logo không kèm tên:** `logo_claude.png`, `logo_gpt.png`, `logo_gemini.png`, `logo_qwen.png`, `logo_grok.png`.

**Chín icon:** `icon_players.png`, `icon_rounds.png`, `icon_endowment.png`, `icon_contribution.png`, `icon_target.png`, `icon_risk.png`, `icon_success.png`, `icon_catastrophe.png`, `icon_no_catastrophe.png`.

Số thứ tự 1–4, vòng tròn chứa số, các nhãn Fixed và mọi tên mô hình đều được tạo lại bằng TikZ; chúng không bị giữ dưới dạng chữ raster trong PNG.

## 4. Chỉnh bố cục, màu và chữ

Toàn bộ tọa độ trong `figure.tex` dùng mm, gốc phía trên bên trái và trục y hướng xuống.

- Sửa các lệnh `\definecolor` để thay bảng màu.
- `\card{x1}{y1}{x2}{y2}{màu nền}{màu viền}` tạo các ô bo góc.
- `\asset{tên không có đuôi PNG}{x tâm}{y tâm}{rộng tối đa}{cao tối đa}` đặt icon, giữ nguyên tỉ lệ ảnh.
- Các `\node` chứa toàn bộ chữ. `\fsize{...}` đặt cỡ chữ theo pt.
- `\designhead` tạo số thứ tự, tên thiết kế và dòng mô tả; `\fixedbadge` tạo nhãn Fixed.

## 5. Thay đổi nội dung so với ảnh gốc

Tiêu đề gốc `Outcomes (if total < 120)` mâu thuẫn với việc chứa trường hợp `Target reached`. Trong bản dựng:

- Tiêu đề chung là `Outcomes`.
- Điều kiện `Miss: total < 120` được ghi riêng.
- Ô Target reached ghi rõ `total ≥ 120`.

Xác suất p và 1 − p được chuyển xuống dòng riêng để các ô dễ đọc và không sát mép. Các tên mô hình, con số trong luật chơi, mô tả thiết kế và màu robot còn lại được giữ theo ảnh cung cấp. Tên phiên bản mô hình được chép từ ảnh, không phải kết quả xác minh độc lập về các bản phát hành.

## 6. Kiểm tra chất lượng đã thực hiện

Kết quả chi tiết có trong `qa/validation.json` và `qa/REPORT.md`.

- PDF có 1 trang, đúng khổ 188 × 106 mm.
- Có đủ 19 PNG trong suốt và 19 hình nhúng có alpha mask.
- Đủ các nhãn cần thiết; cả năm chữ Fixed đều là text thật.
- Các ký hiệu →, ≥, × và − trích xuất được thành Unicode.
- Tất cả 5 font resource đều được nhúng và có ánh xạ Unicode.
- Không phát hiện chữ ra ngoài trang, giao nhau giữa các hộp chữ, hoặc chữ đè lên phần pixel không trong suốt của icon.
- Lần biên dịch cuối không có lỗi, cảnh báo font, Overfull hay Underfull.
- Đã kiểm tra trực quan bản render Poppler và MuPDF, bao gồm phần dày đặc chữ và các nhãn Fixed.

Các robot chồng lên bàn *bên trong một cụm* là cấu trúc của hình gốc và được giữ nguyên, không phải lỗi chồng lấn mới của bố cục TikZ.

## 7. Giới hạn của ảnh nguồn

Khung, nền, đường viền và chữ là vector/text. **Robot và logo vẫn là PNG raster được tách từ ảnh nguồn**, không phải icon SVG vẽ lại. Tách nền không tạo thêm chi tiết hay độ phân giải thật. Ở khổ PDF mặc định, độ phân giải thực của các asset khoảng 227–281 dpi.

Một vài nhãn Fixed trong ảnh gốc chạm đường viền thân robot. Bộ tách giữ vùng hình còn nhìn thấy, loại phần nhãn và không tự sinh thêm chi tiết đã bị che. Toàn bộ chữ Fixed được đặt lại, có khoảng cách với hình.

Không có tệp font được phân phối trong bộ này; các font cần thiết được nhúng trong PDF như khi biên dịch LaTeX thông thường.

## 8. Tách lại asset hoặc chạy lại kiểm tra

Python chỉ cần cho hai thao tác tùy chọn này:

```bash
python -m pip install -r requirements-tools.txt
python extract_assets.py "/duong/dan/anh-goc.png" --output assets
pdflatex -interaction=nonstopmode -halt-on-error figure.tex
python qa/validate.py
```

Script tách cần đúng ảnh đầu vào **1672 × 941 px**; không thay kích thước ảnh trước khi chạy. Nguồn gốc tọa độ và mô tả từng asset được ghi trong `assets/manifest.json`.

## 9. Biến thể màu của Figure 1 (`palettes/`, 19-09-2026)

`figure_biolinum.tex` nhận một file bảng màu qua `\FigPalette`; không có nó thì PDF ra **y hệt** Figure 1 hiện tại (đã so từng pixel ở 200 dpi). Mỗi `palettes/<tên>.tex` chỉ định nghĩa lại màu (và `\headruletrue` nếu bỏ dải tiêu đề), không đụng tới bố cục. Chỉ phần vector đổi màu: khung, dải tiêu đề, nền và viền ô, vòng số 1–4, nhãn Fixed. Robot, logo và icon là PNG nên giữ nguyên màu.

| File | Kiểu |
|---|---|
| `fig1_01_vivid.pdf` | Bảng màu cũ, trùng với `figure_biolinum.pdf` |
| `fig1_02_white_minimal.pdf` | Nền trắng toàn bộ, viền xám mảnh, không dải tiêu đề |
| `fig1_03_classic_paper.pdf` | Nền ngà, viền nâu nhạt, dải navy và xanh chai, điểm nhấn màu đất |
| `fig1_04_nature.pdf` | Bảng màu NPG (ggsci) |
| `fig1_05_science.pdf` | Bảng màu AAAS (ggsci) |
| `fig1_06_okabe_ito.pdf` | Okabe–Ito, an toàn cho người mù màu; số 1–4 chữ đen vì chữ trắng không đủ tương phản trên nền cam |
| `fig1_07_tableau.pdf` | Tableau 10 |
| `fig1_08_slate_mono.pdf` | **Figure 1 của paper** (chép sang `figures/fig_game_designs.pdf`). Một màu xám đá, in trắng đen không mất gì |
| `fig1_09_modern_soft.pdf` | Panel xám nhạt, ô pastel, không dải tiêu đề |

Dựng lại tất cả và trang so sánh `palettes/fig1_palettes_overview.pdf` (kèm `.png`):

```bash
bash palettes/build_palettes.sh
```

**Figure 1 dùng bảng màu nào:** `main.tex` gọi `figures/fig_game_designs.pdf`, vì mọi figure của paper phải nằm trong `paper/AAMAS/figures/`. Không đặt tên `fig_overview.pdf`: tên đó thuộc overview cũ và `analysis/overview.py` vẫn ghi đè lên nó. `build_palettes.sh` chép bảng màu `PAPER_PALETTE` (hiện là `slate_mono`) sang `figures/` sau mỗi lần build, kèm `.png` xem trước. Đổi bố cục thì sửa `figure_biolinum.tex`, đổi màu thì sửa `palettes/slate_mono.tex`, đổi hẳn sang bảng màu khác thì sửa `PAPER_PALETTE`; xong chạy lại script. Đừng sửa tay file trong `figures/`, và đừng chép đè PDF biến thể lên `figure_biolinum.pdf`, vì như vậy PDF và mã nguồn sẽ lệch nhau.

## 10. Bản bố cục dòng chảy (`figure_flow.tex`, 20-09-2026)

Cùng nội dung, cùng asset, cùng font Biolinum và cùng khổ **188 × 90 mm** với Figure 1 hiện tại, nên thay vào `main.tex` không đổi số trang. Khác ở bố cục, theo mẫu "dải hàng + nhãn bên trái + mũi tên khối": bốn dải phẳng chạy hết chiều ngang (The game, Outcomes, Models we study, Four designs), nhãn màu ở đầu mỗi dải, mũi tên xám nối The game → Outcomes và Models → Four designs. **Không còn ô bo góc, khung panel (a)/(b) hay dải tiêu đề**; icon và chữ nằm thẳng trên dải, không nằm trong ô nào. Nhãn "Miss: total < 120" của phần Outcomes nay là một dấu ngoặc chung phía trên hai kết cục miss, thay cho dòng chữ nằm ở góc tiêu đề ô Outcomes cũ. Nhãn "Fixed" là chữ thường, không còn huy hiệu nền xám.

```bash
bash build_flow.sh    # dựng figure_flow.pdf, chép sang ../figures/fig_game_designs_flow.pdf (+ .png)
```

`build_flow.sh` **không đụng** `fig_game_designs.pdf` (bản ô bo góc do `palettes/build_palettes.sh` dựng). Muốn dùng bản này làm Figure 1, đổi đúng một dòng trong `main.tex`: `\includegraphics[width=\textwidth]{figures/fig_game_designs_flow.pdf}`. Màu chỉnh ở khối `\definecolor` đầu file (`CoolBand`/`WarmBand` cho dải, `CoolLabel`/`WarmLabel` cho nhãn và vòng số); muốn hệ đơn sắc như `slate_mono` thì đặt bốn màu đó về cùng một họ xám. Toạ độ tính bằng mm, y hướng xuống, mọi dòng chữ neo theo baseline nên các hàng thẳng nhau.
