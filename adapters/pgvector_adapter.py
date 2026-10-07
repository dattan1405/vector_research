# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import Json
from .base import BaseVectorDB

class PgVectorAdapter(BaseVectorDB):
    def __init__(self, host="localhost", port=5432, dbname="vector_db", user="admin", password="secretpassword", table_name="test_items"):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password
        self.table_name = table_name
        self.conn = None

    def connect(self) -> None:
        self.conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password
        )
        self.conn.autocommit = True
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    def init_schema(self, dim: int, recreate: bool = False) -> None:
        with self.conn.cursor() as cur:
            if recreate:
                cur.execute(f"DROP TABLE IF EXISTS {self.table_name};")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id BIGINT PRIMARY KEY,
                    vector vector({dim}),
                    metadata JSONB,
                    version INT DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def insert(self, record_id: int, vector: List[float], metadata: Dict[str, Any]) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table_name} (id, vector, metadata, version) VALUES (%s, %s::vector, %s, %s) "
                f"ON CONFLICT (id) DO UPDATE SET vector = EXCLUDED.vector, metadata = EXCLUDED.metadata, version = EXCLUDED.version;",
                (record_id, vector, Json(metadata), metadata.get("version", 1))
            )
        return True

    def update_metadata(self, record_id: int, metadata: Dict[str, Any]) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table_name} SET metadata = %s, version = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s;",
                (Json(metadata), metadata.get("version", 1), record_id)
            )
        return True

    def update_vector(self, record_id: int, vector: List[float]) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table_name} SET vector = %s::vector, updated_at = CURRENT_TIMESTAMP WHERE id = %s;",
                (vector, record_id)
            )
        return True

    def update_both(self, record_id: int, vector: List[float], metadata: Dict[str, Any]) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table_name} SET vector = %s::vector, metadata = %s, version = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s;",
                (vector, Json(metadata), metadata.get("version", 1), record_id)
            )
        return True

    def delete(self, record_id: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self.table_name} WHERE id = %s;", (record_id,))
        return True

    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT id, metadata, version FROM {self.table_name} WHERE id = %s;", (record_id,))
            row = cur.fetchone()
            if row:
                return {"id": row[0], "metadata": row[1], "version": row[2]}
            return None

    def hybrid_search(self, query_vector: List[float], filter_conditions: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        where_clauses = []
        params = [query_vector]
        for k, v in filter_conditions.items():
            where_clauses.append(f"metadata->>'{k}' = %s")
            params.append(str(v))
        
        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"""
            SELECT id, metadata, version, (vector <=> %s::vector) AS distance
            FROM {self.table_name}
            {where_str}
            ORDER BY distance ASC
            LIMIT %s;
        """
        params.append(limit)
        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            return [{"id": r[0], "metadata": r[1], "version": r[2], "distance": float(r[3])} for r in rows]

    def close(self) -> None:
        if self.conn:
            self.conn.close()
