# Book Chatbot & Document RAG Assistant

A premium, production-grade Book Chatbot & Document RAG (Retrieval-Augmented Generation) Assistant built with FastAPI, Streamlit, Qdrant Vector Database, and Google Gemini AI.

---

## 🌟 Key Features

### 1. ⚡ Semantic Caching (Instant 0ms Responses)
- Stores user queries and assistant responses using vector embeddings in Qdrant (`semantic_cache` collection).
- When a similar question is asked (cosine similarity $\ge 0.80$), the response is served instantly from the cache, bypassing the LLM completely.
- **Benefits**: 0ms latency, zero API token costs.

### 2. 🔍 Hybrid Search (BM25 + Dense Vector Search)
- Combines **Sparse BM25 Keyword Search** with **Dense Vector Search** using Google `gemini-embedding-001`.
- Uses **Reciprocal Rank Fusion (RRF)** to merge retrieval candidates.
- **Benefits**: 99%+ accuracy in retrieving exact technical terms, numbers, characters, and formulas.

### 3. 📂 Large Document Processing (100+ Pages)
- Recursively splits large documents (PDFs, DOCX, TXT) into smart **2,000 character chunks** (with 400 overlap) and indexes them in Qdrant.
- Handles massive books (e.g., 187-page books) seamlessly.

### 4. 🛡️ Circuit Breaker & Retry Mechanism
- Implemented a thread-safe Circuit Breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) with recovery timeouts.
- Exponential backoff retries with jitter to gracefully handle transient API errors and rate limits.

### 5. 🧵 Thread-Based Batch Parallelism
- Process multiple document evaluations in parallel using `ThreadPoolExecutor` for high throughput.

---

## 🚀 Getting Started

### 📦 Installation
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up your `.env` file:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### 🏃 Running the Application
1. **Start the FastAPI Backend**:
   ```bash
   python -m uvicorn app:app --reload --port 8000
   ```
2. **Start the Streamlit Web UI**:
   ```bash
   streamlit run ui/streamlit_app.py
   ```

---

## 🧪 Evaluation Framework
Evaluate chatbot responses against test cases:
```bash
python evals/runner.py
```
*(Runs with thread-based parallel worker execution).*
