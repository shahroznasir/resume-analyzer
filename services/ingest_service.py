import os
import uuid
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from services.vector_store import vector_store

def ingest_document_text(text: str, source_filename: str = "active_resume") -> int:
    """
    Splits document text into overlapping chunks using RecursiveCharacterTextSplitter
    and indexes them into the Qdrant vector database.
    Returns total chunks indexed.
    """
    if not text.strip():
        print("Empty text provided for ingestion. Skipping.")
        return 0

    # Clear existing active resume chunks in vector store
    vector_store.clear_collection()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    raw_chunks = splitter.split_text(text)
    print(f"Split document into {len(raw_chunks)} chunks for vector indexing.")

    formatted_chunks = []
    for idx, chunk in enumerate(raw_chunks):
        formatted_chunks.append({
            "id": idx + 1,
            "text": chunk,
            "metadata": {
                "source": source_filename,
                "chunk_index": idx,
                "total_chunks": len(raw_chunks)
            }
        })

    vector_store.add_chunks(formatted_chunks)
    return len(formatted_chunks)
