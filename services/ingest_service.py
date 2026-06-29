import os
from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore # noqa
from services.vector_store import vector_store, COLLECTION_NAME
from services.document_service import extract_document_text

RESUME_DIR = "resume"

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
        chunk_size=2000,
        chunk_overlap=400,
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

def ensure_active_resume_indexed():
    """Checks if Qdrant collection is empty and automatically indexes any resume file found in resume/ folder."""
    try:
        count = vector_store.client.count(COLLECTION_NAME).count
        if count == 0 and os.path.exists(RESUME_DIR):
            for filename in os.listdir(RESUME_DIR):
                if filename.lower().endswith((".pdf", ".docx", ".txt")):
                    file_path = os.path.join(RESUME_DIR, filename)
                    text = extract_document_text(file_path)
                    if text.strip():
                        print(f"Auto-indexing active resume '{filename}' into Qdrant...")
                        ingest_document_text(text, filename)
                        break
    except Exception as e:
        print(f"Warning in ensure_active_resume_indexed: {e}")
