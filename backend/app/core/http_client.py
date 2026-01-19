"""
Shared HTTP Client
Singleton HTTP client with connection pooling for better performance
"""
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global HTTP client instance
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """
    Get or create shared HTTP client instance.
    Uses connection pooling for better performance.
    """
    global _http_client
    
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            follow_redirects=True
        )
        logger.info("Created shared HTTP client with connection pooling")
    
    return _http_client


async def close_http_client():
    """
    Close HTTP client (call on application shutdown)
    """
    global _http_client
    
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("Closed shared HTTP client")
