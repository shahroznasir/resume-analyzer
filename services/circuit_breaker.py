import time
import threading

class CircuitOpenException(Exception):
    """Exception raised when calls are rejected because the Circuit Breaker is OPEN."""
    pass

class CircuitBreaker:
    """
    Thread-safe implementation of the Circuit Breaker pattern.
    States:
      - CLOSED: Normal operation. All calls pass through.
      - OPEN: Circuit tripped due to repeated failures/rate limits. Calls immediately rejected.
      - HALF_OPEN: Trial period after recovery_time to test if service has recovered.
    """
    def __init__(self, failure_threshold: int = 3, recovery_time: float = 20.0, name: str = "AI_Service"):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.name = name
        
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_state_change = time.time()
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        """Determines whether a request is allowed to proceed based on circuit state."""
        with self._lock:
            now = time.time()
            if self.state == "OPEN":
                if now - self.last_state_change >= self.recovery_time:
                    self.state = "HALF_OPEN"
                    self.last_state_change = now
                    print(f"[CircuitBreaker-{self.name}] Transitioning from OPEN to HALF_OPEN. Testing API recovery...")
                    return True
                return False
            return True

    def record_success(self):
        """Records a successful execution, resetting failure counters and closing the circuit."""
        with self._lock:
            if self.state in ["HALF_OPEN", "OPEN"]:
                print(f"[CircuitBreaker-{self.name}] Service recovered! Transitioning from {self.state} to CLOSED.")
            self.failure_count = 0
            self.state = "CLOSED"

    def record_failure(self, error: Exception = None):
        """Records an execution failure. Trips the circuit to OPEN if threshold reached."""
        with self._lock:
            self.failure_count += 1
            now = time.time()
            err_msg = f" ({error})" if error else ""
            print(f"[CircuitBreaker-{self.name}] Failure recorded{err_msg}. Count: {self.failure_count}/{self.failure_threshold}")
            
            if self.state == "HALF_OPEN" or self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_state_change = now
                print(f"[CircuitBreaker-{self.name}] ALERT: Circuit TRIPPED to OPEN! Blocking requests for {self.recovery_time}s.")
