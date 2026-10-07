# Nộp full paper AAMAS 2027 — hướng dẫn và checklist

Dựng ngày 07-10-2026 bằng `python paper/AAMAS/make_full_submission.py` (chạy từ gốc repo).

## ⏰ Hạn chót

**8/10/2026, 23:59 AoE (UTC−12) = 19:00 thứ Sáu 9/10/2026 giờ Việt Nam.**
Bạn có thể nộp lại bao nhiêu lần cũng được trước hạn, nên **upload sớm một bản**, rồi sửa sau nếu cần.

Cổng nộp: https://openreview.net/group?id=ifaamas.org/AAMAS/2027/Conference

## 📁 Trong thư mục này

| File | Upload vào trường OpenReview | Ghi chú |
|---|---|---|
| `main.pdf` | **PDF** (bài chính) | 8 trang nội dung, tài liệu tham khảo bắt đầu từ trang 9; ẩn danh |
| `supplementary_material.zip` | **Supplementary Material** | 1,7 MB (giới hạn 25 MB), gồm 1 file zip duy nhất đúng quy định |
| `HUONG_DAN_NOP.md` | (không upload) | file này |

Bên trong `supplementary_material.zip`:

```text
supplementary_material.pdf   supplement 50 trang
code/
  crg_game.py                code chơi game, gọi model qua router chuẩn OpenAI (mặc định OpenRouter)
  README.md                  cách chạy + cấu hình của từng thí nghiệm
  requirements.txt           chỉ cần thư viện chuẩn Python
data/
  exp_*/...                  3.950 ván (CSV), câu trả lời probe
  README.md                  mô tả dữ liệu và các cột
```

## ✅ Việc BẠN phải tự làm (tui không truy cập OpenReview được)

1. **Điền Submission ID.** Mở submission trên OpenReview, lấy số (Submission Number), sửa
   [main.tex dòng 36](../main.tex#L36): `\acmSubmissionID{1234}`. Template quy định số này
   in lên trang 1 ở chế độ ẩn danh. Rồi build lại:
   ```powershell
   cd paper/AAMAS; pdflatex main.tex; pdflatex main.tex; cd ../..
   python paper/AAMAS/make_full_submission.py
   ```
2. **Sửa Title trên OpenReview** thành:
   `Cooperation Without Adaptation: LLM Agents in a Collective-Risk Dilemma`
   (bản abstract nộp ngày 1/10 dùng tiêu đề cũ "Paying When It Cannot Help: …").
3. **Dán lại Abstract trên OpenReview** từ [OPENREVIEW_ABSTRACT.txt](../OPENREVIEW_ABSTRACT.txt)
   (đã đồng bộ chữ-đúng-chữ với main.tex, 251 từ, giới hạn 100–300). Abstract trong paper đã
   viết lại so với bản 1/10, nên trên OpenReview phải khớp với PDF.
   ⚠️ Q&A của AAMAS: tiêu đề/abstract *không nên đổi đáng kể* sau hạn abstract, chỉ cho sửa nhỏ.
   Bạn đã chọn giữ tiêu đề mới; nếu muốn chắc ăn có thể email PC chairs: aamas2027pcs@gmail.com.
4. **Reciprocal reviewer:** người được chỉ định reviewer phải **bấm chấp nhận lời mời trước
   8/10/2026**. Không đạt thì bài có thể bị desk-reject. Kiểm email/OpenReview của người đó.
5. **Checkbox sinh viên:** tick "the primary author is a student" nếu tác giả đầu là sinh viên
   (để xét giải Best Student Paper; reviewer không thấy).
6. **Findings of AAMAS:** mặc định bài không được nhận sẽ được xét đăng ở *Findings* (CC-BY).
   Muốn từ chối thì tick opt-out trong form. Không làm gì = đồng ý.
7. **Chính sách AI:** được dùng AI để trau chuốt câu chữ và viết code thí nghiệm, không cần
   khai. Nếu AI góp phần tạo **giả thuyết hoặc phương pháp**, phải khai chi tiết (công cụ,
   phiên bản, prompt) trong paper hoặc supplement. Bạn tự cân nhắc mục này.
8. Kiểm tra lần cuối trên OpenReview rằng PDF và zip đã lên, rồi mở lại xem PDF hiển thị đúng.

## 🔍 Đã kiểm tự động (cổng của script, chạy lại mỗi lần build)

- Template: `aamas.cls` và `ACM-Reference-Format.bst` **trùng byte** với
  `aamas_2027_template.zip` chính thức; `\documentclass[sigconf,anonymous]{aamas}`, khối copyright
  CC-BY và `\submissionType{Research Paper Track}` đúng mẫu.
- Nội dung chính đúng 8 trang, references bắt đầu trang 9.
- Không có font Type 3; metadata PDF không có tác giả, ngày giờ, đường dẫn file.
- Không có tên tác giả, email, tên trường, account Kaggle, đường dẫn máy, repo GitHub, username
  git trong PDF (ngoài danh sách tham khảo) và trong mọi file của `code/` và `data/`.
- `crg_game.py` = `crg_task_server.py` đã gỡ hết Kaggle Benchmarks: lớp client, tự xin lại token,
  guard push-validation và decorator task bị bỏ; thay bằng router gọi API chuẩn OpenAI
  (`submission_kit/router_client.py`), chạy bằng `python crg_game.py`. Không còn chữ "kaggle" nào.
  Cổng kiểm: mọi định nghĩa ngoài lớp client có cây cú pháp (AST) **giống hệt** bản gốc, tức prompt,
  parser, retry, seed, xổ số, đối thủ scripted đúng là code đã chơi các ván; và chơi trọn 1 ván
  self-play + 1 ván với đối thủ scripted qua router giả lập cục bộ. Đã gọi thật 1 lượt qua
  OpenRouter thành công (tài khoản OpenRouter hiện gần hết credit nên chưa chạy trọn ván thật).

## ⚠️ Lưu ý còn lại

- **Template prompt tiếng Việt** (`TEMPLATE_VN`, không dùng trong paper) vẫn còn trong
  `crg_game.py` vì nó là một phần của chương trình. Theo reviewer guideline, chỉ bị tính là vi
  phạm ẩn danh khi *lộ rõ danh tính* tác giả, nên mức rủi ro thấp.
- Gói **không** kèm script phân tích (theo yêu cầu chỉ giữ code chơi game); supplement ghi rằng
  code phân tích sẽ công bố cùng bản cuối.
- `figures/fig_game_designs.pdf` (Figure 1) dùng ảnh PNG robot trong `tikz_figure_complete/assets/`.
  Nếu ảnh đó do AI sinh: quy định cho phép ảnh AI **chỉ khi generative AI là chủ đề của bài**.
  Bài này về LLM agent nên nhiều khả năng ổn, nhưng bạn nên tự xác nhận nguồn ảnh.
- Nếu bài được nhận: phải công bố supplementary material công khai dạng lưu trữ (Zenodo, GitHub,
  arXiv) cho bản camera-ready (hạn 25/01/2027). Không được đổi danh sách/thứ tự tác giả sau khi nhận.
- Mốc tiếp theo: rebuttal 20–24/11/2026, thông báo kết quả 21/12/2026.

## Nguồn (đọc ngày 07-10-2026)

- Call for main track: https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/call-for-main-track/
- Submission instructions: https://warwick.ac.uk/fac/sci/dcs/aamas2027/guidelines-and-policies/instructions/
- Q&A: https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/qa/
- Reviewer guidelines: https://warwick.ac.uk/fac/sci/dcs/aamas2027/calls/reviewer-guidelines/
- Findings: https://warwick.ac.uk/fac/sci/dcs/aamas2027/guidelines-and-policies/findings/
- Reciprocal reviewer policy: https://warwick.ac.uk/fac/sci/dcs/aamas2027/guidelines-and-policies/reciprocal-reviewer-policy/
