import json
import psycopg2
from psycopg2.extras import execute_values
import time

# 1. Kết nối CSDL pgvector
conn = psycopg2.connect(
    dbname="vector_db", user="admin", password="secretpassword",
    host="localhost", port="5432"
)
cursor = conn.cursor()

# Đọc thử 1 dòng để xác định chính xác số chiều của vector
with open('products-10000.jsonl', 'r', encoding='utf-8') as f:
    first_line = json.loads(f.readline())
    vector_dim = len(first_line['vector'])

print(f"Hệ thống nhận diện vector có {vector_dim} chiều.")

# 2. Tạo bảng Schema khớp hoàn toàn với file của Thịnh
cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS products (
        id INT PRIMARY KEY,
        embedding vector({vector_dim}),
        version INT,
        partition_key INT,
        product_name VARCHAR(255),
        description TEXT,
        brand VARCHAR(100),
        price FLOAT,
        stock_quantity INT,
        view_count INT,
        is_active INT
    );
""")
# Xóa dữ liệu cũ nếu chạy lại script nhiều lần
cursor.execute("TRUNCATE TABLE products;") 
conn.commit()

# 3. Đọc toàn bộ file JSONL vào bộ nhớ
data_to_insert = []
with open('products-10000.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        item = json.loads(line.strip())
        data_to_insert.append((
            item['id'], item['vector'], item['version'], item['partition_key'],
            item['product_name'], item['description'], item['brand'],
            item['price'], item['stock_quantity'], item['view_count'], item['is_active']
        ))

print(f"Đã đọc {len(data_to_insert)} records. Bắt đầu đẩy vào DB...")

# 4. Bắt đầu bấm giờ đo Latency cho thao tác Bulk Insert
start_time = time.time()

insert_query = """
    INSERT INTO products (
        id, embedding, version, partition_key, product_name, 
        description, brand, price, stock_quantity, view_count, is_active
    ) VALUES %s
"""
# execute_values giúp đóng gói 10.000 records thành các batch nhỏ đẩy vào DB cực nhanh
execute_values(cursor, insert_query, data_to_insert, page_size=1000)
conn.commit()

# Dừng bấm giờ
end_time = time.time()
latency_ms = (end_time - start_time) * 1000

print("-" * 30)
print(f"Nạp dữ liệu hoàn tất!")
print(f"Tổng thời gian (Total Latency): {latency_ms:.2f} ms")
print(f"Độ trễ trung bình mỗi record: {latency_ms / len(data_to_insert):.2f} ms/record")

cursor.close()
conn.close()