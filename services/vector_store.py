import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment.")

genai_client = genai.Client(api_key=api_key)

QDRANT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "qdrant")
os.makedirs(QDRANT_DB_DIR, exist_ok=True)

COLLECTION_NAME = "resume_chunks"
VECTOR_SIZE = 3072  # gemini-embedding-001 vector dimension

class VectorStoreManager:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> QdrantClient:
        """Lazily initialize Qdrant client with automatic fallback to in-memory mode if disk storage is locked."""
        if self._client is None:
            try:
                self._client = QdrantClient(path=QDRANT_DB_DIR)
            except Exception as e:
                print(f"[VectorStore] Warning: Local storage locked ({e}). Falling back to in-memory Qdrant instance...")
                self._client = QdrantClient(":memory:")
            self._ensure_collection()
        return self._client

    def _ensure_collection(self):
        try:
            collections = [c.name for c in self.client.get_collections().collections]
            if COLLECTION_NAME not in collections:
                print(f"[VectorStore] Creating Qdrant collection '{COLLECTION_NAME}' (dim={VECTOR_SIZE})...")
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"[VectorStore] Error ensuring collection: {e}")

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector using Google gemini-embedding-001 model."""
        response = genai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        return response.embeddings[0].values

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Add text chunks into Qdrant vector database.
        Each chunk dict: {"id": int/str, "text": str, "metadata": dict}
        """
        points = []
        for idx, chunk in enumerate(chunks):
            vector = self.get_embedding(chunk["text"])
            point_id = chunk.get("id", idx + 1)
            if isinstance(point_id, int) or (isinstance(point_id, str) and point_id.isdigit()):
                point_id = int(point_id)
                
            payload = {
                "text": chunk["text"],
                **chunk.get("metadata", {})
            }
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        if points:
            self.client.upsert(collection_name=COLLECTION_NAME, points=points)
            print(f"[VectorStore] Upserted {len(points)} vector chunks into Qdrant collection '{COLLECTION_NAME}'.")

    def search_similar_chunks(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Search top-K most relevant resume chunks for a user query."""
        try:
            if self.client.count(COLLECTION_NAME).count == 0:
                from services.ingest_service import ensure_active_resume_indexed
                ensure_active_resume_indexed()
        except Exception as e:
            print(f"Auto-ingestion check warning: {e}")

        query_vector = self.get_embedding(query)
        response = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k
        )
        results = []
        for hit in response.points:
            results.append({
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
            })
        return results

    def clear_collection(self):
        """Reset collection when a new active resume is uploaded."""
        try:
            self.client.delete_collection(collection_name=COLLECTION_NAME)
            self._ensure_collection()
            print(f"[VectorStore] Cleared Qdrant collection '{COLLECTION_NAME}'.")
        except Exception as e:
            print(f"[VectorStore] Error clearing Qdrant collection: {e}")

vector_store = VectorStoreManager()
