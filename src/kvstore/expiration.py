import time
from collections.abc import Callable

Clock = Callable[[], float]

class ExpirationRegistry:
    def __init__(self, clock: Clock = time.time):
        self._expires_at = {}
        self._clock = clock
    
    def set_expiry(self, key: str, expires_at: float) -> None:
        self._expires_at[key] = expires_at
    
    def clear_expiry(self, key: str) -> None:
        self._expires_at.pop(key, None)
    
    def get_expiry(self, key: str) -> float | None:
        return self._expires_at.get(key, None)
    
    def is_expired(self, key: str) -> bool:
        expires_at = self._expires_at.get(key)
        return expires_at is not None and expires_at <= self._clock()

    def expired_keys(self) -> list[str]:
        now = self._clock()
        return [key for key, expires_at in self._expires_at.items() if expires_at <= now]

    def all_expirations(self) -> dict[str, float]:
        return dict(self._expires_at)
    
    def clock_now(self):
        return self._clock()
