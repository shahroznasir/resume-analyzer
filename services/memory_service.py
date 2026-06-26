import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = None
in_memory_cache = {}

try:
    redis_client = redis.Redis.from_url(redis_url, socket_timeout=2)
    redis_client.ping()
    print("Connected to Redis successfully.")
except Exception as e:
    print(f"Failed to connect to Redis. Error: {e}")
    print("Falling back to local In-Memory memory cache...")
    redis_client = None

SESSION_TTL = 3600
def get_session_memory(session_id: str) -> list:
    """Retrieve short-term session conversation history."""
    if redis_client:
        try:
            key = f"chat_session:{session_id}"
            data = redis_client.get(key)
            if data:
                return json.loads(data)
            return []
        except Exception as e:
            print(f"Error reading from Redis: {e}")
    return in_memory_cache.get(session_id, [])

def save_session_memory(session_id: str, history: list) -> None:
    """Save the short-term conversation history."""
    if redis_client:
        try:
            key = f"chat_session:{session_id}"
            redis_client.setex(key, SESSION_TTL, json.dumps(history))
            return
        except Exception as e:
            print(f"Error writing to Redis: {e}")
    in_memory_cache[session_id] = history

def update_session_memory(session_id: str, role: str, content: str) -> list:
    """Append a message to short-term session history, keep it capped at last 10 messages."""
    history = get_session_memory(session_id)
    history.append({"role": role, "content": content})
    if len(history) > 10:
        history = history[-10:]
    save_session_memory(session_id, history)
    return history

def clear_session_memory(session_id: str) -> None:
    """Clear short term session memory."""
    if redis_client:
        try:
            key = f"chat_session:{session_id}"
            redis_client.delete(key)
            return
        except Exception as e:
            print(f"Error deleting key from Redis: {e}")
    if session_id in in_memory_cache:
        del in_memory_cache[session_id]
