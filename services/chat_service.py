import os
from google.genai import types
from services.gemini_service import client, generate_content_with_retry, generate_content_stream_with_retry
from services.document_service import extract_document_text
from services.vector_store import vector_store

RESUME_DIR = "resume"

def get_resume_context() -> str:
    """Scan resume/ directory and extract raw text from the first supported file found."""
    if not os.path.exists(RESUME_DIR):
        os.makedirs(RESUME_DIR, exist_ok=True)
        return ""
    
    for filename in os.listdir(RESUME_DIR):
        if filename.lower().endswith((".pdf", ".docx", ".txt")):
            file_path = os.path.join(RESUME_DIR, filename)
            try:
                text = extract_document_text(file_path)
                if text.strip():
                    return text
            except Exception as e:
                print(f"Error reading document file {filename}: {e}")
    return ""

def stream_chat_response(message: str, history: list):
    """
    Stream chatbot response using Vector RAG (Qdrant + Google Embeddings + Gemini 2.5 Flash).
    Performs top-K similarity search to retrieve relevant book/document chunks.
    """
    retrieved_chunks = []
    try:
        retrieved_chunks = vector_store.search_similar_chunks(query=message, top_k=4)
    except Exception as e:
        print(f"Vector search warning/error: {e}. Falling back to full document text.")

    if retrieved_chunks:
        context_blocks = [f"[Chunk {idx+1}] {c['text']}" for idx, c in enumerate(retrieved_chunks)]
        retrieved_context_str = "\n\n".join(context_blocks)
        rag_context_prompt = f"Retrieved Book/Document Knowledge Chunks (Qdrant Vector DB):\n---\n{retrieved_context_str}\n---"
    else:
        full_text = get_resume_context()
        if full_text:
            rag_context_prompt = f"Book/Document Content:\n---\n{full_text}\n---"
        else:
            rag_context_prompt = "No book or document has been uploaded yet."

    system_prompt = f"""
You are an intelligent Book and Document RAG Assistant powered by Qdrant and Gemini AI.
Here is the retrieved context knowledge from the vector database:
{rag_context_prompt}

Instructions:
1. Answer the user's questions accurately and concisely based on the retrieved book/document context.
2. If the question can be answered from the retrieved context, explain clearly with details from the text.
3. Be helpful, professional, and articulate. Use multi-turn conversation memory to understand context.
"""

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.3,
        top_p=0.95,
        max_output_tokens=1000
    )

    contents = []
    for msg in history:
        contents.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )
    
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)]
        )
    )

    try:
        response = generate_content_stream_with_retry(
            model="gemini-2.5-flash",
            contents=contents,
            config=config
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        yield f"Error: Failed to fetch response from Gemini ({e})"


def is_query_safe_and_relevant(message: str) -> bool:
    """
    Checks if the user query is safe from malicious prompt injection attacks.
    """
    blocked_keywords = [
        "jailbreak", "ignore instructions", "bypass security", 
        "system prompt", "dan mode", "forget everything"
    ]
    message_lower = message.lower()
    for keyword in blocked_keywords:
        if keyword in message_lower:
            print(f"Guardrail trigger: Programmatic keyword '{keyword}' found.")
            return False
    return True
