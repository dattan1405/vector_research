# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional
from pymilvus import MilvusClient, DataType
from .base import BaseVectorDB

class MilvusAdapter(BaseVectorDB):
    def __init__(self, uri="http://localhost:19530", collection_name="test_items"):
        self.uri = uri
        self.collection_name = collection_name
        self.client: Optional[MilvusClient] = None

    def connect(self) -> None:
        self.client = MilvusClient(uri=self.uri)

    def init_schema(self, dim: int, recreate: bool = False) -> None:
        if self.client.has_collection(self.collection_name):
            if recreate:
                self.client.drop_collection(self.collection_name)
                
        if not self.client.has_collection(self.collection_name):
            schema = self.client.create_schema(
                auto_id=False,
                enable_dynamic_field=True
            )
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
            schema.add_field(field_name="version", datatype=DataType.INT64)

            index_params = self.client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                metric_type="COSINE",
                index_type="FLAT"
            )

            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                index_params=index_params
            )

    def insert(self, record_id: int, vector: List[float], metadata: Dict[str, Any]) -> bool:
        data = {
            "id": record_id,
            "vector": vector,
            "version": metadata.get("version", 1),
            **metadata
        }
        self.client.upsert(collection_name=self.collection_name, data=[data])
        return True

    def update_metadata(self, record_id: int, metadata: Dict[str, Any]) -> bool:
        # Trong Milvus, lấy vector hiện tại sau đó upsert lại cùng metadata mới
        res = self.client.get(collection_name=self.collection_name, ids=[record_id], output_fields=["*"], consistency_level="Strong")
        if not res:
            return False
        current_vector = res[0].get("vector")
        data = {
            "id": record_id,
            "vector": current_vector,
            "version": metadata.get("version", 1),
            **metadata
        }
        self.client.upsert(collection_name=self.collection_name, data=[data])
        return True

    def update_vector(self, record_id: int, vector: List[float]) -> bool:
        res = self.client.get(collection_name=self.collection_name, ids=[record_id], output_fields=["*"], consistency_level="Strong")
        if not res:
            return False
        item = res[0]
        item["vector"] = vector
        self.client.upsert(collection_name=self.collection_name, data=[item])
        return True

    def update_both(self, record_id: int, vector: List[float], metadata: Dict[str, Any]) -> bool:
        data = {
            "id": record_id,
            "vector": vector,
            "version": metadata.get("version", 1),
            **metadata
        }
        self.client.upsert(collection_name=self.collection_name, data=[data])
        return True

    def delete(self, record_id: int) -> bool:
        self.client.delete(collection_name=self.collection_name, ids=[record_id])
        return True

    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        res = self.client.get(collection_name=self.collection_name, ids=[record_id], output_fields=["*"], consistency_level="Strong")
        if res:
            item = dict(res[0])
            rid = item.pop("id", record_id)
            ver = item.pop("version", 1)
            item.pop("vector", None)
            return {"id": rid, "metadata": item, "version": ver}
        return None

    def hybrid_search(self, query_vector: List[float], filter_conditions: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        filter_exprs = []
        for k, v in filter_conditions.items():
            if isinstance(v, str):
                filter_exprs.append(f'{k} == "{v}"')
            else:
                filter_exprs.append(f'{k} == {v}')
        filter_str = " and ".join(filter_exprs) if filter_exprs else ""

        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            filter=filter_str if filter_str else None,
            limit=limit,
            output_fields=["*"],
            consistency_level="Strong"
        )
        output = []
        if results and len(results) > 0:
            for hit in results[0]:
                entity = hit.get("entity", {})
                rid = entity.pop("id", hit.get("id"))
                ver = entity.pop("version", 1)
                entity.pop("vector", None)
                output.append({
                    "id": rid,
                    "metadata": entity,
                    "version": ver,
                    "distance": float(hit.get("distance", 0.0))
                })
        return output

    def close(self) -> None:
        if self.client:
            self.client.close()
