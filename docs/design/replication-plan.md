# Kế hoạch replicate Milinski et al. (2008)

Nguồn chi tiết: [../papers/milinski-2008-collective-risk.md](../papers/milinski-2008-collective-risk.md).
PDF gốc: `papers/milinski-et-al-2008-*.pdf`.

## Checklist tham số (đã encode trong configs/game/*.json)

| Tham số | Giá trị gốc | Field config |
|---|---|---|
| Số người/nhóm | 6 | `nPlayers` |
| Endowment/người | 40 | `endowment` |
| Số vòng | 10 | `nRounds` |
| Lựa chọn đóng góp/vòng | 0, 2, 4 | `contributionOptions` |
| Mục tiêu nhóm | 120 | `target` |
| Đóng góp công bằng | 2/người/vòng (= 120/(6×10)) | (suy ra) |
| Xác suất mất nếu miss | 90% / 50% / 10% | `riskProbability` |
| Số nhóm/điều kiện | 10 | `repetitions` |
| Giao tiếp | không | `agentsCommunicate=false` |
| Biết số vòng | có | `nRoundsIsKnown=true` |

## Quy tắc payoff (đã encode trong engine/scoring.py)

- Tổng nhóm ≥ 120 → mỗi người giữ `endowment − tổng_đã_đóng`.
- Tổng nhóm < 120 → tung xúc xắc 1 lần: xác suất `risk` → tất cả = 0; ngược lại giữ phần còn lại.
- Tiền đã đóng luôn mất.

## Baseline người (để so sánh "LLM có giống người không")

- **90% risk**: ~50% số nhóm đạt mục tiêu.
- **50% risk**: hầu hết nhóm KHÔNG đạt.
- **10% risk**: gần như không nhóm nào đạt.

→ Kỳ vọng LLM "giống người" = reach-rate tăng theo mức rủi ro, cao nhất ở 90%.

## Thiết kế thí nghiệm (init)

`exp_baseline.json`: 3 mức rủi ro × {EN, VN} × 1 model × 10 lần lặp = **60 ván**,
agent trung tính (`personas_default`). Phân tích chính:

1. Reach-rate theo `riskProbability`, so baseline người.
2. So EN vs VN (reach-rate, mean_group_total) ở từng mức rủi ro.
3. Free-riding & Gini đóng góp; hiệu ứng vòng cuối.

## Lưu ý hiệu lực (validity)

- **Chất lượng dịch VN**: nên back-translate template VN để đảm bảo tương đương ngữ nghĩa với EN
  (giữ mọi yếu tố khác không đổi) — xem [../papers/language-effects-llm.md](../papers/language-effects-llm.md).
- **Parse rate**: theo dõi `parse_failed` trong `turns.jsonl`; model nhỏ + VN dễ lệch định dạng.
- **Mức rủi ro vs số mẫu**: 10 lần lặp đủ để thấy xu hướng; tăng `repetitions` cho thống kê chắc hơn.
- **Common random numbers**: ván cùng `rep` ở các mức rủi ro dùng chung draw thảm hoạ (so theo cặp).
