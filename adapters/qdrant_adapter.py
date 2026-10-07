# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from .base import BaseVectorDB

class QdrantAdapter(BaseVectorDB):
    def __init__(self, host="localhost", port=6333, collection_name="test_items"):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client = None

    def connect(self) -> None:
        self.client = QdrantClient(host=self.host, port=self.port, timeout=10.0)

    def init_schema(self, dim: int, recreate: bool = False) -> None:
        collections = [c.name for c in self.client.get_collections().collections]
        if recreate and self.collection_name in collections:
            self.client.delete_collection(collection_name=self.collection_name)
            collections.remove(self.collection_name)
            
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE)
            )

    def insert(self, record_id: int, vector: List[float], metadata: Dict[str, Any]) -> bool:
        point = models.PointStruct(id=record_id, vector=vector, payload=metadata)
        self.client.upsert(collection_name=self.collection_name, points=[point])
        return True

    def update_metadata(self, record_id: int, metadata: Dict[str, Any]) -> bool:
        self.client.set_payload(collection_name=self.collection_name, payload=metadata, points=[record_id])
        return True

    def update_vector(self, record_id: int, vector: List[float]) -> bool:
        self.client.update_vectors(
            collection_name=self.collection_name,
            points=[models.PointVectors(id=record_id, vector=vector)]
        )
        return True

    def update_both(self, record_id: int, vector: List[float], metadata: Dict[str, Any]) -> bool:
        point = models.PointStruct(id=record_id, vector=vector, payload=metadata)
        self.client.upsert(collection_name=self.collection_name, points=[point])
        return True

    def delete(self, record_id: int) -> bool:
        self.client.delete(collection_name=self.collection_name, points_selector=models.PointIdsList(points=[record_id]))
        return True

    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        points = self.client.retrieve(collection_name=self.collection_name, ids=[record_id], with_payload=True)
        if points:
            p = points[0]
            return {"id": p.id, "metadata": p.payload, "version": p.payload.get("version", 1) if p.payload else 1}
        return None

    def hybrid_search(self, query_vector: List[float], filter_conditions: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        conditions = []
        for k, v in filter_conditions.items():
            conditions.append(models.FieldCondition(key=k, match=models.MatchValue(value=v)))
            
        query_filter = models.Filter(must=conditions) if conditions else None
        res = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit
        )
        hits = res.points
        return [{"id": h.id, "metadata": h.payload, "version": h.payload.get("version", 1) if h.payload else 1, "distance": float(h.score)} for h in hits]

    def close(self) -> None:
        if self.client:
            self.client.close()
