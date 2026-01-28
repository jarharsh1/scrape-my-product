"""
Rate limiting implementation using token bucket algorithm.
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    capacity: int  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Returns True if tokens were consumed, False if not enough tokens.
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    async def wait_for_token(self, tokens: int = 1):
        """Wait until a token is available, then consume it."""
        while not self.consume(tokens):
            # Calculate wait time
            needed = tokens - self.tokens
            wait_time = needed / self.refill_rate
            await asyncio.sleep(min(wait_time, 0.1))


class RateLimiter:
    """
    Rate limiter for managing request rates to different domains.

    Uses per-domain token buckets to ensure fair rate limiting.
    """

    def __init__(
        self,
        requests_per_minute: int = 30,
        burst_limit: int = 5
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum sustained request rate
            burst_limit: Maximum burst size (bucket capacity)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    def _get_bucket(self, domain: str) -> TokenBucket:
        """Get or create a token bucket for a domain."""
        if domain not in self._buckets:
            self._buckets[domain] = TokenBucket(
                capacity=self.burst_limit,
                refill_rate=self.refill_rate
            )
        return self._buckets[domain]

    async def acquire(self, domain: str, tokens: int = 1):
        """
        Acquire permission to make a request to a domain.

        Blocks until rate limit allows the request.

        Args:
            domain: The domain being accessed
            tokens: Number of tokens to consume (usually 1)
        """
        async with self._lock:
            bucket = self._get_bucket(domain)

        await bucket.wait_for_token(tokens)

    def try_acquire(self, domain: str, tokens: int = 1) -> bool:
        """
        Try to acquire permission without blocking.

        Returns True if acquired, False if rate limited.
        """
        bucket = self._get_bucket(domain)
        return bucket.consume(tokens)

    def get_wait_time(self, domain: str) -> float:
        """Get estimated wait time in seconds for a domain."""
        bucket = self._get_bucket(domain)
        bucket._refill()
        if bucket.tokens >= 1:
            return 0.0
        return (1 - bucket.tokens) / bucket.refill_rate


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        from app.config import config
        _rate_limiter = RateLimiter(
            requests_per_minute=config.scraper.requests_per_minute,
            burst_limit=config.scraper.burst_limit
        )
    return _rate_limiter
