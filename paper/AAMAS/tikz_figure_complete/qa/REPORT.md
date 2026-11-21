# Báo cáo kiểm tra figure

## Kết quả: PASS

Bản kiểm tra: `figure.pdf` và 19 PNG trong `assets/`.

| Hạng mục | Kết quả |
|---|---|
| Biên dịch thật từ TikZ | pdfLaTeX, thành công |
| Trang / kích thước | 1 trang; 188 × 106 mm |
| Cảnh báo lần biên dịch cuối | Không có cảnh báo font, Overfull, Underfull hoặc Missing character |
| Đủ nội dung chữ dự kiến | Có; kiểm tra chuỗi trực tiếp trên text objects của PDF |
| Nhãn Fixed | Đủ 5 nhãn chọn/copy được |
| Ký hiệu toán | →, ≥, ×, − trích xuất được |
| Font | 5 font resource; tất cả nhúng và có Unicode mapping |
| PNG RGBA | 19/19; có alpha bằng 0 và vùng hình alpha bằng 255 |
| Lề trong suốt của asset | 19/19 có biên ngoài trong suốt, không cắt vào silhouette |
| Ảnh nhúng trong PDF | 19 ảnh, mỗi ảnh có transparency mask |
| Hộp chữ giao nhau đáng kể | 0 |
| Chữ giao với pixel icon không trong suốt | 0 |
| Chữ nằm ngoài trang | 0 |
| Kiểm tra bằng mắt | Đã xem bản render Poppler và MuPDF; phóng lớn lưới bốn thiết kế |

Phép kiểm tra text–image dùng alpha mask thực tế: khoảng trống trong hình PNG không bị coi là phần hình cần tránh. Hộp chữ được kiểm tra bảo thủ theo bounding box trong PDF. Các tiếp giáp dưới 0,05 pt do làm tròn giữa những đoạn font của cùng dòng không bị coi là va chạm.

Đã sửa phần cắt vướng viền cyan dưới cụm Self-play và chỉnh đường loại nhãn Fixed để không cắt vào phần trán chéo của hai robot phía trên. Các nhãn được dời khỏi hình khi dựng TikZ.

Các giao nhau nội tại giữa robot và mặt bàn được giữ như ảnh nguồn. Chất lượng chi tiết raster vẫn bị giới hạn bởi ảnh đầu vào; không có thao tác tạo hình mới hoặc vector hóa giả.

Để chạy lại kiểm tra tự động, từ thư mục gốc chạy `python qa/validate.py`. Kết quả máy đọc được nằm trong `qa/validation.json`.
