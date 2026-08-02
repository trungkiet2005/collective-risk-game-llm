# CLAUDE.md — quy ước làm việc trong repo CRSD-LLM

Tài liệu trạng thái/lộ trình nằm ở [PROJECT.md](PROJECT.md). File này chỉ ghi các
quy ước bắt buộc khi sửa code.

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
