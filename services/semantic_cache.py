import uuid
from typing import Optional
from services.vector_store import vector_store, VECTOR_SIZE
from qdrant_client.models import Distance, VectorParams, PointStruct

CACHE_COLLECTION = "semantic_cache"

class SemanticCacheManager:
    def __init__(self):
        self._ensure_cache_collection()

    @staticmethod
    def _ensure_cache_collection():
        try:
            collections = [c.name for c in vector_store.client.get_collections().collections]
            if CACHE_COLLECTION not in collections:
                print(f"[SemanticCache] Creating Qdrant collection '{CACHE_COLLECTION}'...")
                vector_store.client.create_collection(
                    collection_name=CACHE_COLLECTION,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"[SemanticCache] Warning ensuring cache collection: {e}")

    @staticmethod
    def get_cached_response(query: str, similarity_threshold: float = 0.80) -> Optional[str]:
        """
        Checks if a semantically similar query exists in cache.
        Returns cached response string if similarity >= threshold, else None.
        """
        try:
            query_vector = vector_store.get_embedding(query)
            response = vector_store.client.query_points(
                collection_name=CACHE_COLLECTION,
                query=query_vector,
                limit=1
            )
            if response.points:
                hit = response.points[0]
                if hit.score >= similarity_threshold:
                    print(f"[SemanticCache HIT!] Similarity score: {hit.score:.4f} for query '{query}'")
                    return hit.payload.get("response")
        except Exception as e:
            print(f"[SemanticCache] Lookup warning: {e}")
        return None

    @staticmethod
    def store_cached_response(query: str, response_text: str):
        """Stores query embedding and response into semantic cache."""
        if not response_text.strip() or "Error:" in response_text:
            return
        try:
            query_vector = vector_store.get_embedding(query)
            point_id = str(uuid.uuid4())
            payload = {
                "query": query,
                "response": response_text
            }
            vector_store.client.upsert(
                collection_name=CACHE_COLLECTION,
                points=[PointStruct(id=point_id, vector=query_vector, payload=payload)]
            )
            print(f"[SemanticCache] Successfully cached response for query '{query[:30]}...'")
        except Exception as e:
            print(f"[SemanticCache] Store warning: {e}")

semantic_cache = SemanticCacheManager()
