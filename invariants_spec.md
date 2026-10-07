# ĐẶC TẢ CÁC THUỘC TÍNH BẤT BIẾN CẦN KIỂM ĐỊNH (CONSISTENCY INVARIANTS)
**Đề tài:** Nghiên cứu phương pháp kiểm định tính nguyên tử và nhất quán của dữ liệu Vector–Metadata trong cơ sở dữ liệu vector nguồn mở.  
**Thời gian thực hiện:** Tháng 10/2026 (Nội dung 2 trong thuyết minh).

---

## 1. Mô hình dữ liệu thử nghiệm (Data Model)
Mỗi thực thể trong CSDL thử nghiệm biểu diễn một đối tượng có trạng thái đa chiều:
- **`id` (int64):** Khóa chính định danh duy nhất.
- **`vector` (float[d]):** Vector nhúng (embedding), kích thước \(d = 128\) (hoặc 768). Mỗi phiên bản vector được gắn nhãn giá trị đặc trưng (ví dụ: toàn bộ phần tử mang giá trị hàm của phiên bản \(v\)).
- **`metadata` (json/struct):**
  - `version` (int): Số phiên bản tăng dần (\(1, 2, 3, \dots\)).
  - `category` / `brand` (string): Thuộc tính phục vụ lọc danh mục.
  - `price` (float): Thuộc tính số phục vụ lọc khoảng (\(price < threshold\)).
  - `status` (string): Trạng thái bản ghi (`active`, `archived`, `deleted`).
  - `payload_checksum` (string/int): Mã kiểm tra tương ứng với phiên bản vector.

---

## 2. Danh mục 5 Invariants kiểm định tính Nguyên tử & Nhất quán

### Invariant 1: Tính nguyên tử khi cập nhật đồng thời (Vector–Metadata Atomicity)
* **Ý nghĩa:** Khi client gọi thao tác cập nhật cả vector và metadata từ phiên bản \(v_k\) lên \(v_{k+1}\), hệ thống phải đảm bảo tính *all-or-nothing*.
* **Điều kiện vi phạm (Anomaly):**
  - Client đọc được: `metadata.version == k + 1` NHƯNG `vector` vẫn thuộc phiên bản \(k\) (hoặc ngược lại).
  - Kết quả ANN query trả về khoảng cách khớp với vector mới, nhưng metadata lọc ra lại là giá trị cũ.

### Invariant 2: Đọc phân mảnh (Fractured Read / Isolation Anomaly)
* **Ý nghĩa:** Một truy vấn đọc một tập hợp các đối tượng hoặc kiểm tra liên thuộc tính không được quan sát thấy trạng thái giao thoa giữa các giao dịch chưa hoàn tất.
* **Điều kiện vi phạm:**
  - Client 1 cập nhật 2 trường liên đới trong metadata: `status = 'archived'` và `price = 0`.
  - Client 2 thực hiện truy vấn đồng thời và đọc thấy `status = 'archived'` nhưng `price` vẫn là giá trị cũ (\(> 0\)).

### Invariant 3: Mất mát cập nhật (Lost Update)
* **Ý nghĩa:** Khi 2 client đồng thời cập nhật trên cùng một bản ghi `id = X`.
* **Điều kiện vi phạm:**
  - Client 1 ghi phiên bản 2, Client 2 ghi phiên bản 3.
  - Sau khi cả hai báo thành công, trạng thái cuối cùng bị ghi đè không theo thứ tự tuần tự hoặc một trong hai thao tác bị mất không để lại dấu vết trong lịch sử commit.

### Invariant 4: Sai lệch giữa Bộ lọc Metadata và Chỉ mục Vector (Filtered ANN Stale Visibility)
* **Ý nghĩa:** Trong vector database, việc cập nhật index vector (HNSW / IVF) thường có độ trễ so với cập nhật metadata.
* **Điều kiện vi phạm:**
  - Bản ghi \(X\) vừa được cập nhật metadata để thỏa mãn bộ lọc (`brand = 'Aura'`).
  - Client thực hiện `hybrid_search(filter={"brand": "Aura"})` ngay lập tức nhưng bản ghi \(X\) bị bỏ sót vì chỉ mục vector chưa cập nhật payload mask hoặc ngược lại (trả về bản ghi dù metadata đã không còn thỏa mãn).

### Invariant 5: Tính đơn điệu khi đọc (Monotonic Reads Consistency)
* **Ý nghĩa:** Nếu một client đã quan sát thấy phiên bản \(v_{k}\) của bản ghi \(X\), các lần đọc tiếp theo của client đó trên cùng bản ghi không bao giờ được nhìn thấy phiên bản cũ hơn \(v_{j}\) (\(j < k\)).
* **Điều kiện vi phạm:** Thường gặp ở các hệ thống cụm phân tán (Milvus replicas/shards) khi truy vấn bị điều hướng đến một replica có replication lag.

---

## 3. Cấu trúc Lịch sử Thực thi (Execution History Log)
Mọi client khi thực hiện thao tác sẽ ghi log dạng JSON Lines (`history.jsonl`):
```json
{
  "client_id": 1,
  "op_id": "op-10492",
  "op_type": "UPDATE_BOTH",
  "target_id": 42,
  "start_time_ns": 1728284400123456789,
  "end_time_ns": 1728284400145678901,
  "input": {"version": 2, "vector_hash": "a1b2", "metadata": {"brand": "Aura", "price": 250}},
  "output": {"status": "SUCCESS"},
  "error": null
}
```
Bộ kiểm định (`checker.py`) sẽ đọc toàn bộ log này để dựng đồ thị phụ thuộc quan sát và đối chiếu với 5 Invariant trên.
