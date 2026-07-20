# Kịch bản thuyết trình — Turn 3

**Tổng thời lượng mục tiêu: 20–22 phút nói + 8–10 phút thảo luận.**
Chữ in nghiêng là ghi chú diễn xuất (không đọc). Phần trong ngoặc vuông là con số cần nhớ, đừng đọc vẹt cả câu.

---

## 0. Mở đầu (slide tiêu đề) — 30 giây

> Dạ em chào thầy. Turn 3 này em chỉ làm đúng một việc: lấy câu hỏi mà Turn 2 để lại và đem đi thử.
>
> Kết luận ngắn gọn trước, để thầy tiện theo dõi: **cho model biết tổng quỹ thì nó lập tức thôi đóng thừa, nhưng vẫn không sợ rủi ro, và vẫn không chịu bù vào chỗ còn thiếu.** Cả deck còn lại là bằng chứng cho ba mệnh đề đó.

*Nói xong câu này rồi mới sang slide. Đừng để thầy phải chờ tới cuối mới biết kết luận.*

---

## 1. Turn 2 để lại câu hỏi gì — 1 phút 30

> Turn 2 mình chốt được ba điều. Một, model **hiểu luật và biết mức rủi ro** — em hỏi kiểm tra thì gần như 100% trả lời đúng, biết mục tiêu 120, biết rủi ro đang là 90%. Hai, nhưng model nhỏ thì **không cộng dồn được trạng thái**: đọc từng dòng lịch sử thì đúng, mà cộng chín dòng lại thì sai. Em gọi tắt là "đọc được nhưng cộng không được". Ba, dù vậy, **mọi cỡ model đều phớt lờ rủi ro** — 10% hay 90% chơi y như nhau.
>
> Ba điều đó đặt cạnh nhau thì gợi ra một giả thuyết rất tự nhiên, và đó chính là câu em ghi ở cuối deck Turn 2: *nếu chuyện bất thường là do model không tính nổi trạng thái, thì mình cho không nó con số, bất thường phải biến mất.*
>
> Turn này em làm đúng phép thử đó.

*Nhấn chữ "phải biến mất" — vì lát nữa nó không biến mất, và đó là cái hay của turn này.*

---

## 2. Thiết kế thí nghiệm — 2 phút

> Em gỡ hai chỗ mà em nghi là "khó" trong prompt.
>
> **Chỗ khó thứ nhất là cách diễn đạt rủi ro.** Bản gốc theo Milinski kể như một câu chuyện: "máy tính quay xổ số", "cả nhóm gặp thảm hoạ". Em nghi là mấy hình ảnh đó làm loãng con số xác suất, model đọc thành chuyện kể chứ không đọc thành 90%. Nên em nêu thẳng: "với xác suất 90 phần trăm...".
>
> **Chỗ khó thứ hai là trạng thái.** Bản gốc muốn biết quỹ được bao nhiêu thì phải tự cộng tám chín dòng lịch sử. Em in sẵn cho nó: tổng quỹ hiện tại, và tổng tích luỹ của từng người chơi.
>
> Ngoài hai chỗ đó, **mọi thứ giữ nguyên tuyệt đối**: vẫn 7 model mở — Qwen 7/32/72B, Gemma 9/27B, Llama 8/70B — nhân 3 mức rủi ro, nhân hai ngôn ngữ Anh–Việt, nhân 10 lần lặp. Ra 60 ván mỗi model, tổng 420 ván. Cùng seed, cùng common random numbers, agent trung tính, full history, không persona. Nên em so trực tiếp được với baseline Turn 1.
>
> Có một điểm em phải nói trước cho sòng phẳng: **hai thao tác này em chạy chung một ô**, chưa tách riêng. Nên cái em đo được là *tổng* hiệu ứng của cả hai, chưa biết công của từng cái. Đây là điểm đầu tiên em muốn xin ý thầy ở cuối buổi.

*Chủ động nói ra hạn chế này — thầy sẽ hỏi, nói trước thì mình dẫn chuyện.*

---

## 3–4. Hai slide prompt thật — 2 phút (mỗi slide ~1 phút)

*Hai slide này là prompt nguyên văn. Đừng đọc hết — chỉ chỉ tay vào đúng chỗ khác nhau.*

**Slide "Thao tác 1":**

> Đây là prompt thật, thầy nhìn hai khối. Khối cũ: "the computer runs a lottery... the group is hit by a disaster". Khối mới: bỏ đúng hai hình ảnh đó đi, còn lại **giữ nguyên từng chữ**. Con số 90% không đổi, cấu trúc câu không đổi. Em chỉ bỏ phần kể chuyện bao quanh nó.

**Slide "Thao tác 2":**

> Còn đây là thao tác hai. Bên trên là khối "Current state" bản cũ: chỉ có số vòng và số tiền còn lại của mình, muốn biết quỹ thì tự cộng lấy tám dòng bên dưới.
>
> Bản mới thêm đúng hai dòng — em chỉ vào — dòng `Climate account so far: 130`, và dòng tổng tích luỹ từng ghế. Phần còn lại giữ nguyên từng byte.
>
> Nói cách khác: con số mà model từng phải **tự cộng**, giờ em **cho không**.

*Nếu còn thời gian, đây là chỗ chèn slide phụ `quotes_read_vs_add.txt` — xem mục "Slide dự phòng" cuối file.*

---

## 5. Kết quả 1 — hết đóng thừa (R1_excess) — 1 phút 30

> Cái được thấy ngay: **model thôi đốt tiền vô ích.**
>
> Mục tiêu chỉ cần 120 thôi. Baseline thì Qwen-7B đóng tổng **233** — gần gấp đôi mức cần thiết, tức là quăng đi hơn một trăm đơn vị mà chẳng mua được gì. Ở nhánh mới nó xuống **175**. Llama-8B từ 185 xuống 175. Gemma-27B về sát vạch, **121** — tức gần như đóng vừa đủ.
>
> Ba model vốn đã tiết kiệm sẵn thì gần như đứng yên. Hợp lý — chúng nó có gì để bỏ đâu.

---

## 6. Cơ chế cái phanh (R3_brake) — 1 phút 30

> Nhưng em muốn biết nó tiết kiệm **ở đâu**, nên em lọc riêng các lượt mà quỹ **đã vượt 120 rồi**. Ở những lượt đó, đồng nào đóng thêm cũng là tiền vứt đi — không mua thêm được chút an toàn nào cả, mục tiêu đã đạt rồi.
>
> Baseline: model vẫn đóng **2 đến 4 mỗi lượt**. Đều đặn, vòng nào cũng vậy, cho tới hết ván.
>
> Nhánh mới: Qwen-32B xuống **0.2**, Gemma-27B xuống tròn **0**.
>
> Tức là toàn bộ phần tiết kiệm ở slide trước không phải model đóng ít đi nói chung — mà là nó **biết dừng đúng lúc**. Thấy "đủ rồi" là tắt.

*Đây là kết quả sạch nhất của cả turn. Cho thầy vài giây nhìn hình.*

---

## 7. Nhịp chơi (R4_dynamics) — 1 phút

> Nhìn theo thời gian thì rõ hơn nữa. Baseline có hình dạng rất lạ: **đóng tăng dần cho tới vòng 10**, càng về cuối càng đóng nhiều — ngược hẳn với người, người ta gom sớm rồi thả lỏng về sau.
>
> Nhánh mới thì đường cong đổi hẳn: **vọt lên khi còn thiếu, rồi tắt hẳn khi đã đủ**. Đây là lần đầu trong ba turn em thấy được hình dạng "đủ thì thôi".

---

## 8. Vân tay lựa chọn (R8_choice) — 1 phút

> Xuống tận mức phân phối lựa chọn thì thấy cái này: **mức "đóng 0" lần đầu tiên xuất hiện thật sự.**
>
> Qwen-7B baseline chọn 0 đúng **0%** số lượt — không bao giờ. Nhánh mới: **22%**. Qwen-32B từ 3% lên 16%.
>
> Trước đây model gần như có một phản xạ "cứ đóng gì đó đi". Giờ nó học được cách **không** đóng.

---

## 8b. Bổ theo rủi ro — nhịp chơi (R4B_dynamics_risk) — 1 phút

> Tới đây chắc thầy sẽ hỏi ngay: hai cái vừa rồi em gộp chung cả ba mức rủi ro, vậy nếu tách ra thì sao? Em bổ ra đây.
>
> Sáu ô: hàng trên là baseline, hàng dưới là nhánh mới; ba cột là rủi ro **10%, 50%, 90%**.
>
> Thầy đọc theo **hàng** thì thấy khác nhau rõ: hàng trên tăng dần tới chót, hàng dưới vọt rồi tắt. Đọc theo **cột** thì gần như không phân biệt được — ba cột chồng lên nhau gần khít.
>
> Nói gọn: cái đổi được nhịp chơi là **can thiệp prompt**, không phải **mức rủi ro**.

---

## 8c. Bổ theo rủi ro — vân tay lựa chọn (R8B_choice_risk) — 1 phút

> Cùng câu hỏi đó, nhưng xuống tận mức từng lượt chọn. Mỗi model giờ có ba dòng: 10%, 50%, 90%.
>
> Ba dòng của cùng một model gần như **trùng khít nhau**. Ví dụ Qwen-7B nhánh mới: chọn 0 ở mức 20% – 23% – 23% khi rủi ro đi từ 10% lên 90%. Chênh lệch lớn nhất trong cả bảng chỉ **2,8 điểm phần trăm** — đó là nhiễu, không phải phản ứng.
>
> Em nghĩ chỗ này đáng nói vì nó chặn được một phản biện: có thể ai đó bảo "tỉ lệ đạt mục tiêu là chỉ số thô, biết đâu bên trong model vẫn có điều chỉnh nhẹ theo rủi ro mà chỉ số thô không bắt được". Bổ tới mức phân phối lựa chọn rồi thì thấy: **không có điều chỉnh nào cả.**

---

## 9. Kết quả 2 — phép thử cốt lõi vẫn trượt (R2_reach_risk) — 2 phút

> Đó là phần được. Giờ tới phần **không được** — và đây mới là phần quan trọng.
>
> Trục hoành là mức rủi ro, trục tung là mức hợp tác. Ở người, Milinski đo được đường này **dốc mạnh**: rủi ro 90% thì một nửa số nhóm đạt mục tiêu, rủi ro 10% thì gần như không nhóm nào đạt. Người phản ứng với rủi ro.
>
> Còn đây là LLM. Em vừa **nêu thẳng xác suất**, vừa **cho không con số trạng thái** — hai chỗ khó đều gỡ rồi. Và đường vẫn **phẳng**. 10% hay 90% chơi hệt nhau.
>
> Em nhấn lại chỗ này vì nó dễ bị lướt qua: model **đọc đúng** 90%, Turn 2 em kiểm tra rồi, hỏi thì trả lời đúng gần như 100%. Nó biết. Nó chỉ không **dùng**.

---

## 10. Chuỗi loại trừ — 1 phút 30

> Gom lại thì sau ba turn em đã loại được bốn giả thuyết, theo thứ tự:
>
> Do model nhỏ quá? Không — Turn 2 chạy lên tới 72B vẫn phẳng.
> Do model mở, do em tự host, do sampling? Không — Turn 2 gọi Gemini qua API, đóng y hệt.
> Do hiểu sai luật hoặc không biết mức rủi ro? Không — kiểm tra gần 100% đúng.
> Do phải tự cộng trạng thái nên không theo dõi được? **Không** — và đó là đóng góp của turn này.
>
> Cái hay là turn này không chỉ nói "không phải". Nó cho thấy khi cho không con số thì model **dùng ngay** — dùng để tiêu ít đi. Nên không thể bảo là nó bỏ qua con số. Nó dùng, nhưng chỉ dùng cho một chiều.

*Đây là slide bản lề. Nói chậm.*

---

## 11. Kết quả 3 — cái mất (R5_gemma_cost) — 1 phút 30

> Và có cái giá phải trả, em không giấu.
>
> Gemma-9B ở baseline đạt mục tiêu **100%** số ván. Nhánh mới xuống **68%**. Gemma-27B từ 100% xuống **78%**. Kéo theo thảm hoạ thật: **23%** và **12%** số ván cả nhóm mất trắng — baseline là 0%.
>
> Nhưng thầy nhìn chỗ này: **32 ván trượt đều rơi vào khoảng 112 đến 118.** Không phải trượt xa. Chỉ **hụt 2 đến 8 đơn vị** — trong khi một vòng cuối cả nhóm thừa sức đóng tới 24.
>
> Nên đây không phải "model chơi tệ đi". Đây là model **chơi sát vạch rồi hụt chân**.

---

## 12. Vì sao trượt — bất đối xứng (R6_asymmetry) — 1 phút 30

> Em bổ theo "còn thiếu bao nhiêu" ở vòng cuối để xem model có phản ứng theo lỗ hổng không.
>
> Kết quả: thiếu 1 đến 6, model đóng khoảng **2**. Thiếu 13 đến 24, model vẫn đóng khoảng **2**. Cùng một mức quen thuộc, bất kể lỗ hổng to nhỏ ra sao.
>
> Ở Gemma, những lỗ hổng vòng cuối mà cả nhóm thừa sức bít — từ 24 trở xuống — nay **hụt một phần ba số lần**.
>
> Tức là con số dùng để **dừng** thì được, để **bù** thì không.

---

## 13. Ca tệ nhất — Gemma vòng cuối — 2 phút

*Slide đắt nhất deck. Đọc nguyên văn phần lý giải, chậm, để thầy nghe ra chỗ sai.*

> Em muốn cho thầy xem một ca cụ thể, vì nó nói rõ hơn mọi biểu đồ.
>
> Gemma-2-27B, rủi ro 90%, **vòng cuối cùng**. Prompt in rõ mọi thứ: vòng 10 trên 10, tiền còn lại 22, quỹ khí hậu đang **118**. Mục tiêu 120 — tức chỉ **thiếu đúng 2**. Mức được phép là 0, 2, 4. Sáu người chơi. Thừa sức bù.
>
> Đây là lý giải nguyên văn của model, em đọc:
>
> *"Mục tiêu gần đạt: quỹ đã 118, chỉ cần thêm 2 đơn vị nữa."* — Đọc đúng.
> *"Rủi ro cao: nếu không đạt, với xác suất 90% mọi người mất trắng."* — Cũng đọc đúng.
> *"Lợi ích cá nhân: bạn hiện có 22. **Đóng góp thêm bất kỳ số nào cũng có nguy cơ cao mất trắng.**"*
>
> Chỗ này là chỗ sai, thầy. Nó **ngược**. Đóng 2 chính là thứ **chặn** mất trắng. Model lấy đúng hai tiền đề đúng rồi suy ra kết luận ngược dấu.
>
> Rồi nó kết: *"chiến lược hợp lý nhất là không đóng góp thêm... hy vọng nhóm sẽ tự động đạt được mục tiêu."*
>
> Cả sáu người chơi đều ra 0. Quỹ đóng ở 118. Trượt. 90% cả nhóm mất trắng — vì thiếu 2 đơn vị mà ai cũng có sẵn.

*Ngừng một nhịp sau câu cuối.*

---

## 14. Không phải lỗi số học — 1 phút

> Ba mảnh khớp nhau như thế này:
>
> Model **đọc đúng** tổng quỹ — vì em in sẵn. Model **đọc đúng** mức rủi ro — Turn 2 đã kiểm.
> Model **dùng được** con số đó cho một việc: đủ rồi thì dừng.
> Model **không dùng** chính con số đó cho việc ngược lại: thiếu thì bù.
>
> Nên nói gọn: cho biết tổng quỹ là trao cho model một cái **phanh**, không phải một cái **vô lăng**.
>
> Trước turn này em vẫn ngờ lỗ hổng nằm ở **số học**. Hoá ra số học chỉ là lớp ngoài. Lỗi nằm ở khâu **nối con số vào hành động**.

---

## 15. Ai được ai mất (R7_payoff) — 1 phút

> Về tiền mang về thì cùng một can thiệp lại tác động **hai chiều ngược nhau**.
>
> Model từng tiêu hoang thì được lợi lớn: Qwen-7B từ **1.2** lên **10.8**, gấp chín lần — vì nó ngừng quăng tiền đi.
>
> Model vốn đã tiết kiệm thì **thiệt**: Gemma-9B từ 18.5 xuống **14.8** — vì cái nó bỏ đi không phải phần thừa, mà là phần **đệm an toàn**.

---

## 16. Trục ngôn ngữ (R9_lang) — 45 giây

> Trục ngôn ngữ vẫn còn, em báo cáo cho đủ. Gemma-9B bản tiếng Anh tụt trung bình xuống **117.5** — dưới vạch — nên chỉ đạt **37%** số ván. Cùng model đó, cùng điều kiện, bản tiếng Việt đạt **100%**.
>
> Chênh lệch Anh–Việt không mất đi ở nhánh mới.

---

## 17. Bảng tổng hợp — 1 phút

*Đừng đọc cả bảng. Chỉ hai dòng tô màu.*

> Bảng này để thầy đối chiếu. Em chỉ nhấn hai dòng tô đậm.
>
> Dòng trên: đóng góp khi quỹ đã đủ 120 — từ **2–4** xuống **0 đến 1.7**. Phanh ăn.
> Dòng dưới: phản ứng với rủi ro — **không**, và **vẫn không**. Không đổi.
>
> Và ba model còn lại — Qwen-32B, 72B, Llama-8B — vẫn giữ nguyên 100% đạt mục tiêu, chỉ tiêu ít đi. Nên cái giá phải trả tập trung ở Gemma, không phải toàn cục.

---

## 18–19. Tổng kết + so ba turn — 1 phút 30

> Bức tranh sau ba turn, em phát biểu thành một câu: **hợp tác của LLM là thói quen, không phải tính toán** — và turn này là bằng chứng trực tiếp đầu tiên cho câu đó.
>
> Cho không con số thì model dùng ngay, để bỏ phần đóng thừa. Cùng con số đó không tạo ra phản ứng với rủi ro. Và không tạo ra hành vi bù đắp — thiếu 2 hay thiếu 18, vẫn đóng mức quen thuộc là 2.
>
> Gemma đọc đúng 118 trên 120, đọc đúng 90%, mà vẫn kết luận ngược. Nên lỗi không ở khâu đọc, cũng không ở khâu cộng.
>
> Một câu để nhớ: **thông tin tốt hơn làm model tiết kiệm hơn, không làm nó an toàn hơn.**

---

## 20. Điểm xin ý thầy — 2 phút

*Chuyển giọng: hết báo cáo, sang hỏi. Đừng hỏi dồn — nêu ba cái, rồi im.*

> Em có ba chỗ muốn xin ý thầy.
>
> **Thứ nhất, về thiết kế.** Turn này em gộp hai thao tác vào một ô nên chưa tách được công của từng cái. Chạy 2×2 đầy đủ thì tốn thêm hai ô, bảy model, khoảng 840 ván. Thầy thấy có đáng không, hay tổng hiệu ứng là đủ để viết? Ngoài ra Llama-70B ở arm này là bản **3.3** còn baseline Turn 1 là **3.1**, nên cặp đó chưa so sạch — em có nên chạy lại 3.1 để khép bảng không.
>
> **Thứ hai, về bước kế tiếp.** Bước tự nhiên là in sẵn luôn *"còn thiếu bao nhiêu"* và *"mỗi người cần đóng bao nhiêu"* — tức là bón tới tận miệng. Nếu vẫn không bù thì loại nốt giả thuyết "không suy ra được lỗ hổng", và lúc đó em nghĩ chỉ còn lại một cách giải thích: model đang bắt chước một mức đóng góp quen thuộc chứ không hề tối ưu gì cả.
>
> **Thứ ba, một câu diễn giải em còn phân vân.** Gemma trượt là vì mất phần đệm dư. Vậy phần đệm đó nên coi là **hành vi phòng vệ hợp lý** trước một nhóm không đoán trước được, hay là **lãng phí**? Em hỏi vì nó đổi dấu toàn bộ kết quả: nếu đệm là hợp lý thì can thiệp của em làm model *tệ đi* chứ không phải tốt lên.
>
> Và cuối cùng, em có nên đưa arm frontier — gpt-nano, DeepSeek, Claude — vào đúng điều kiện này luôn không ạ.

---

## 21. Slide chốt — 20 giây

> Cho model **biết** tổng quỹ, nó lập tức **thôi đóng thừa**. Cùng con số đó **không** làm nó sợ rủi ro hơn, và **không** làm nó bù vào chỗ còn thiếu.
>
> Đó là một cái **phanh** — không phải một cái **vô lăng**.
>
> Em xin hết ạ.

---
---

# Chuẩn bị hỏi đáp

**"Sao em chắc là do prompt chứ không phải do sampling / nhiễu?"**
> Dạ cùng seed và common random numbers với baseline, 10 lần lặp mỗi ô, 420 ván. Khoảng chênh ở Qwen-7B là 233 xuống 175 — lớn hơn nhiễu giữa các lần lặp nhiều lần. Còn dòng "phản ứng rủi ro" thì ngược lại: nó phẳng ở *mọi* model, mọi ngôn ngữ, mọi lần lặp — nhất quán tới mức khó đổ cho nhiễu.

**"Model có thật sự đọc dòng tổng quỹ mình in vào không, hay bỏ qua?"**
> Có ạ, và em có bằng chứng nguyên văn. Ở nhánh mới, model trích thẳng con số: *"the climate account already has 130 units, which is 10 units over the required target of 120"*. Còn ở baseline, cùng model cùng vòng, nó tự cộng và cộng sai — bảo tám vòng nhân 12 bằng 144, thực ra là 96, rồi ngừng đóng dựa trên chính con số sai đó. *(Nếu thầy muốn xem, mở slide dự phòng.)*

**"Vì sao chỉ Gemma trượt mà mấy model kia không?"**
> Vì Gemma vốn chơi sát vạch nhất. Baseline nó đóng 126 trên mục tiêu 120 — đệm chỉ 6. Bỏ đệm đi là hụt ngay. Qwen-7B đóng 233, cắt hơn 50 vẫn còn dư chán. Nói cách khác cái phanh tác động đều nhau, nhưng model nào ít đệm thì phanh làm nó vượt vạch.

**"Đây có phải là kết quả tiêu cực không? Có viết thành bài được không?"**
> Em nghĩ được, mà phải khung lại. Đóng góp không phải "can thiệp có hiệu quả", mà là **loại được giả thuyết cuối cùng còn lại về nguyên nhân kỹ thuật**, cộng với một phân ly rất sạch: cùng một con số, dùng được cho chiều dừng, không dùng được cho chiều bù. Cái phân ly đó mới là kết quả, và nó là kết quả dương.

**"Nếu đổi payoff / đổi phần thưởng thì có khác không?"**
> Dạ em chưa đo. Nhưng em ngờ là ít khác, vì lý do này: ở ca Gemma vòng cuối, payoff đã cực rõ rồi — đóng 2 để giữ 20, hay giữ 22 để 90% mất sạch. Chênh lệch kỳ vọng khổng lồ mà model vẫn chọn sai. Nên em nghĩ vấn đề không nằm ở độ lớn phần thưởng.

**"Sao không thử prompt chain-of-thought / bắt nó tính rõ ra?"**
> Đây đúng là hướng em định làm ngay sau — chính là ý "in sẵn còn thiếu bao nhiêu" ở slide thảo luận. Em muốn đi từng nấc: từ *bắt tự cộng* → *cho tổng* → *cho lỗ hổng* → *cho luôn mức cần đóng*. Nấc nào hành vi đổi thì chỗ đứt gãy nằm ở đó.

---

# Slide dự phòng (chưa gắn vào deck)

File `assets/quotes_read_vs_add.txt` đã viết xong nhưng **chưa có frame nào dùng**. Nội dung là cặp trích dẫn Qwen-32B trước/sau, cho thấy rất rõ:
- **Cũ:** tự cộng → sai (144 thay vì 96) → dừng đóng dựa trên con số sai.
- **Mới:** đọc thẳng "130" → dừng đúng lúc.

Đây là bằng chứng mạnh nhất cho câu "model thật sự đọc dòng mình in vào". Hai lựa chọn:
1. Chèn thành frame sau slide "Thao tác 2" (+1 phút nói) — em khuyên làm vậy nếu buổi này có ≥25 phút.
2. Giữ làm slide backup cuối deck, chỉ mở khi thầy hỏi.

Nếu muốn chèn, thêm vào sau dòng 90 của [slide.tex](slides/turn_3/slide.tex#L90):

```latex
\begin{frame}[fragile]{Model có thật sự đọc dòng vừa thêm không?}
  \promptbox{\fontsize{6.6}{7.6}\selectfont}{assets/quotes_read_vs_add.txt}
  \take{Cũ: tự cộng ra \weak{144} (đúng ra 96) rồi dừng theo con số sai.
  Mới: trích thẳng \good{130} rồi dừng đúng lúc.}
\end{frame}
```
