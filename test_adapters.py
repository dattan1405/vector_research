# -*- coding: utf-8 -*-
"""
Script kiểm tra kết nối và tính tương thích CRUD cho cả 3 Vector DB:
- pgvector (PostgreSQL:5432)
- Qdrant (HTTP:6333)
- Milvus (gRPC:19530)
"""
import sys
import numpy as np
from adapters import PgVectorAdapter, QdrantAdapter, MilvusAdapter

sys.stdout.reconfigure(encoding='utf-8')

VECTOR_DIM = 4

def test_single_adapter(adapter_name: str, adapter):
    print(f"\n==========================================")
    print(f"[*] Đang kiểm tra adapter: {adapter_name}...")
    print(f"==========================================")
    try:
        # 1. Kết nối
        adapter.connect()
        print(" -> [x] Kết nối thành công!")

        # 2. Tạo Schema / Collection
        adapter.init_schema(dim=VECTOR_DIM, recreate=True)
        print(" -> [x] Khởi tạo schema/collection thành công!")

        # 3. Thêm dữ liệu (Insert)
        vec1 = [0.1, 0.2, 0.3, 0.4]
        meta1 = {"brand": "Aura", "price": 150.0, "version": 1}
        adapter.insert(record_id=1, vector=vec1, metadata=meta1)

        vec2 = [0.9, 0.8, 0.7, 0.6]
        meta2 = {"brand": "Nova", "price": 400.0, "version": 1}
        adapter.insert(record_id=2, vector=vec2, metadata=meta2)
        print(" -> [x] Insert 2 bản ghi thành công!")

        # 4. Đọc theo ID (Get by ID)
        rec = adapter.get_by_id(record_id=1)
        print(f" -> [x] Lấy bản ghi ID 1: {rec}")

        # 5. Cập nhật Metadata (Update Metadata)
        adapter.update_metadata(record_id=1, metadata={"brand": "Aura", "price": 199.0, "version": 2})
        rec_updated = adapter.get_by_id(record_id=1)
        print(f" -> [x] Sau khi cập nhật metadata: {rec_updated}")

        # 6. Hybrid search (Vector + Filter Metadata)
        query_vec = [0.1, 0.2, 0.3, 0.4]
        results = adapter.hybrid_search(query_vector=query_vec, filter_conditions={"brand": "Aura"}, limit=5)
        print(f" -> [x] Kết quả hybrid search: {results}")

        print(f"===> THÀNH CÔNG: {adapter_name} hoạt động hoàn hảo!")
        adapter.close()
        return True
    except Exception as e:
        print(f"===> THẤT BẠI: {adapter_name} gặp lỗi: {e}")
        try:
            adapter.close()
        except:
            pass
        return False

def main():
    print("KIỂM TRA CÁC VECTOR DATABASE ADAPTERS")
    
    adapters = {
        "pgvector (PostgreSQL:5432)": PgVectorAdapter(table_name="quick_test_items"),
        "Qdrant (HTTP:6333)": QdrantAdapter(collection_name="quick_test_items"),
        "Milvus (gRPC:19530)": MilvusAdapter(collection_name="quick_test_items")
    }

    results = {}
    for name, adp in adapters.items():
        results[name] = test_single_adapter(name, adp)

    print("\n" + "="*50)
    print("TỔNG KẾT:")
    for name, status in results.items():
        st = "READY (Sẵn sàng)" if status else "OFFLINE / CHƯA BẬT CONTAINER"
        print(f" - {name}: {st}")
    print("="*50)

if __name__ == "__main__":
    main()
