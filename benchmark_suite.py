# -*- coding: utf-8 -*-
import sys
import time
import json
import csv
import random
import concurrent.futures
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
import numpy as np

# Cho phép in tiếng Việt UTF-8 trên Windows console
sys.stdout.reconfigure(encoding='utf-8')

DB_CONFIG = {
    "dbname": "vector_db",
    "user": "admin",
    "password": "secretpassword",
    "host": "localhost",
    "port": "5432"
}

PRODUCT_IDS = list(range(1, 10001))
BRANDS = ["Helio", "Aura", "Nova", "Zenith", "Vortex"]

def get_db_pool(minconn=1, maxconn=60):
    return ThreadedConnectionPool(minconn, maxconn, **DB_CONFIG)

def read_operation(pool):
    conn = pool.getconn()
    start_time = time.time()
    success = False
    anomaly = False
    try:
        cursor = conn.cursor()
        query_vector = np.random.rand(128).tolist()
        brand = random.choice(BRANDS)
        price_limit = random.uniform(200, 800)
        
        sql = """
            SELECT id, product_name, brand, price, version, (embedding <=> %s::vector) AS distance
            FROM products
            WHERE brand = %s AND price < %s
            ORDER BY embedding <=> %s::vector
            LIMIT 5;
        """
        cursor.execute(sql, (query_vector, brand, price_limit, query_vector))
        rows = cursor.fetchall()
        
        # Consistent State check: Verify fetched rows are non-null and valid
        for r in rows:
            if r[3] is None or r[4] is None:  # price or version is null -> Inconsistent/Atomicity error
                anomaly = True
                
        cursor.close()
        success = True
    except Exception as e:
        success = False
    finally:
        pool.putconn(conn)
        
    latency_ms = (time.time() - start_time) * 1000
    return ("read", latency_ms, success, anomaly)

def write_operation(pool):
    conn = pool.getconn()
    start_time = time.time()
    success = False
    anomaly = False
    try:
        cursor = conn.cursor()
        target_id = random.choice(PRODUCT_IDS)
        price_delta = round(random.uniform(-5.0, 5.0), 2)
        
        # Concurrent Update on Metadata + Version
        sql = """
            UPDATE products 
            SET price = GREATEST(10.0, price + %s),
                view_count = view_count + 1,
                version = version + 1
            WHERE id = %s;
        """
        cursor.execute(sql, (price_delta, target_id))
        conn.commit()
        cursor.close()
        success = True
    except Exception as e:
        conn.rollback()
        success = False
        anomaly = True
    finally:
        pool.putconn(conn)
        
    latency_ms = (time.time() - start_time) * 1000
    return ("write", latency_ms, success, anomaly)

def run_scenario(name, read_ratio, num_threads, duration_sec=8):
    print(f"\n▶ Chạy Kịch bản: '{name}' | Luồng: {num_threads} | Tỷ lệ Đọc: {int(read_ratio*100)}% - Ghi: {int((1-read_ratio)*100)}%")
    pool = get_db_pool(minconn=1, maxconn=num_threads + 5)
    
    start_test_time = time.time()
    end_test_time = start_test_time + duration_sec
    
    results = []
    
    def worker():
        ops = []
        while time.time() < end_test_time:
            if random.random() < read_ratio:
                res = read_operation(pool)
            else:
                res = write_operation(pool)
            ops.append(res)
        return ops

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            results.extend(f.result())
            
    total_duration = time.time() - start_test_time
    pool.closeall()
    
    # Process Metrics
    total_ops = len(results)
    read_latencies = [r[1] for r in results if r[0] == "read" and r[2]]
    write_latencies = [r[1] for r in results if r[0] == "write" and r[2]]
    all_latencies = [r[1] for r in results if r[2]]
    anomalies = sum(1 for r in results if r[3])
    errors = sum(1 for r in results if not r[2])
    
    throughput = total_ops / total_duration if total_duration > 0 else 0
    avg_lat = np.mean(all_latencies) if all_latencies else 0
    p95_lat = np.percentile(all_latencies, 95) if all_latencies else 0
    p99_lat = np.percentile(all_latencies, 99) if all_latencies else 0
    
    summary = {
        "scenario_name": name,
        "threads": num_threads,
        "read_ratio_pct": int(read_ratio * 100),
        "write_ratio_pct": int((1 - read_ratio) * 100),
        "duration_sec": round(total_duration, 2),
        "total_ops": total_ops,
        "read_ops": len(read_latencies),
        "write_ops": len(write_latencies),
        "throughput_ops_sec": round(throughput, 2),
        "avg_latency_ms": round(avg_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "p99_latency_ms": round(p99_lat, 2),
        "anomalies_count": anomalies,
        "errors_count": errors
    }
    
    print(f"   ✓ Hoàn tất {total_ops:,} ops trong {total_duration:.2f}s | Throughput: {throughput:.2f} ops/sec")
    print(f"   - Latency Avg: {avg_lat:.2f} ms | P95: {p95_lat:.2f} ms | P99: {p99_lat:.2f} ms")
    print(f"   - Sai lệch (Anomalies): {anomalies} | Lỗi (Errors): {errors}")
    return summary

def main():
    scenarios = [
        ("Read-Heavy (90/10)", 0.90),
        ("Balanced (50/50)", 0.50),
        ("Write-Heavy (10/90)", 0.10)
    ]
    thread_counts = [10, 50]
    
    all_results = []
    
    print("=" * 65)
    print("🚀 BẮT ĐẦU BỘ THỬ NGHIỆM BENCHMARK ĐỒNG THỜI (PGVECTOR)")
    print("=" * 65)
    
    for name, ratio in scenarios:
        for threads in thread_counts:
            summary = run_scenario(name, ratio, threads, duration_sec=8)
            all_results.append(summary)
            time.sleep(1) # Nghỉ giữa các lượt chạy
            
    # Export to JSON
    json_path = "benchmark_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n📁 Đã xuất kết quả chi tiết dạng JSON vào file: benchmark_results.json")
    
    # Export to CSV
    csv_path = "benchmark_summary.csv"
    fieldnames = list(all_results[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    print(f"📁 Đã xuất bảng tổng hợp dạng CSV vào file: benchmark_summary.csv")
    
    print("\n" + "=" * 70)
    print("📊 BẢNG TỔNG HỢP KẾT QUẢ BENCHMARK")
    print("=" * 70)
    header_fmt = "{:<22} | {:<7} | {:<12} | {:<10} | {:<10} | {:<10}"
    print(header_fmt.format("Kịch bản", "Luồng", "Throughput", "Avg (ms)", "P95 (ms)", "Anomalies"))
    print("-" * 70)
    for r in all_results:
        print(header_fmt.format(
            r["scenario_name"],
            r["threads"],
            f"{r['throughput_ops_sec']} op/s",
            f"{r['avg_latency_ms']} ms",
            f"{r['p95_latency_ms']} ms",
            r["anomalies_count"]
        ))
    print("=" * 70)

if __name__ == "__main__":
    main()
