# Vector–Metadata Consistency Verification Framework

Dự án Nghiên cứu Khoa học Sinh viên: **Nghiên cứu phương pháp kiểm định tính nguyên tử và nhất quán của dữ liệu Vector–Metadata trong cơ sở dữ liệu vector nguồn mở**.

---

## 📌 Tổng quan dự án
Nghiên cứu xây dựng framework kiểm định black-box đánh giá tính đúng đắn, nguyên tử (Atomicity) và nhất quán (Consistency) của dữ liệu kết hợp Vector–Metadata khi chịu tải đọc/ghi và truy vấn đồng thời (Concurrent Workloads) trên 3 hệ CSDL vector mã nguồn mở:
- **pgvector** (PostgreSQL Relational + Vector Extension)
- **Qdrant** (Vector Search Engine viết bằng Rust)
- **Milvus Standalone** (Distributed Vector Database)

---

## 🚀 Hướng dẫn khởi chạy nhanh cho thành viên nhóm (Quick Start)

### 1. Yêu cầu hệ thống
- Đã cài đặt **Docker Desktop** (bật WSL 2 backend).
- Đã cài đặt **Python 3.10+**.
- Đã cài đặt **Git**.

### 2. Thiết lập môi trường Python
```bash
# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 3. Khởi chạy 3 CSDL qua Docker
```bash
# Khởi động toàn bộ container ở chế độ nền
docker compose up -d
```
> **Ports hoạt động:**
> - PostgreSQL / pgvector: `5432`
> - Qdrant: `6333` (HTTP & Web UI: http://localhost:6333/dashboard), `6334` (gRPC)
> - Milvus Standalone: `19530` (gRPC), `9091` (Metrics)
> - MinIO (Storage của Milvus): `9000` (API), `9001` (Web Console: http://localhost:9001)

### 4. Kiểm tra kết nối và tính tương thích của cả 3 DB
Chạy script kiểm tra tự động:
```bash
python test_adapters.py
```
Nếu cả 3 hệ thống đều hiển thị `READY (Sẵn sàng)` thì môi trường đã hoàn toàn sẵn sàng cho thử nghiệm!

---

## 📂 Cấu trúc thư mục
```text
vector_research/
├── adapters/                # Module chuẩn hóa truy cập DB (Unified DB Layer)
│   ├── base.py              # Abstract Interface (BaseVectorDB)
│   ├── pgvector_adapter.py  # Adapter cho pgvector
│   ├── qdrant_adapter.py    # Adapter cho Qdrant
│   ├── milvus_adapter.py    # Adapter cho Milvus Standalone
│   └── __init__.py
├── invariants_spec.md       # Đặc tả 5 thuộc tính bất biến cần kiểm định (Atomicity, Fractured Read...)
├── test_adapters.py         # Script kiểm thử kết nối & thao tác CRUD cho cả 3 DB
├── docker-compose.yml       # Cấu hình container cho pgvector, Qdrant, Milvus, etcd, MinIO
├── requirements.txt         # Danh sách thư viện Python
├── products-10000.jsonl     # Tập mock data 10.000 records mẫu (vector 128 chiều)
├── import_data.py           # Script nạp mock data vào pgvector
├── benchmark_suite.py       # Prototype chạy benchmark đa luồng ban đầu
└── .gitignore               # Tự động bỏ qua virtualenv, log và cache
```

---

## 👥 Phân công nhiệm vụ (Theo Thuyết minh Đề tài)
* **Trương Minh Thuận (Chủ nhiệm):** Quản lý tiến độ, xây dựng mô hình nghiên cứu, đặc tả *Consistency Invariants*, viết báo cáo & bài báo.
* **Đỗ Văn Quý:** Quản lý môi trường Docker, phát triển module kết nối và chuẩn hóa thao tác với các CSDL vector (`adapters/`).
* **Lê Phúc Thịnh:** Xây dựng cơ chế ghi nhận lịch sử thực thi (`execution_logger.py`).
* **Ngô Đăng Quang:** Xây dựng bộ sinh workload đa luồng, thay đổi số luồng và tỷ lệ đọc/ghi (`workload_generator.py`).
* **Phạm Tấn Đạt:** Thu thập kết quả thực nghiệm, tính toán anomaly frequency, latency, recall; vẽ biểu đồ và trực quan hóa dữ liệu.
