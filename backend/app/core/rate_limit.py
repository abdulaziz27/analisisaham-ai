"""
Rate Limiting Middleware
Simple in-memory rate limiter for API protection
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from collections import defaultdict
from datetime import datetime, timedelta
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.
    For production, consider using Redis-based rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        # Store request timestamps per IP
        self.minute_requests: Dict[str, list] = defaultdict(list)
        self.hour_requests: Dict[str, list] = defaultdict(list)
        self._cleanup_interval = timedelta(minutes=5)
        self._last_cleanup = datetime.now()
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded IP (if behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory leak"""
        now = datetime.now()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_minute = now - timedelta(minutes=1)
        cutoff_hour = now - timedelta(hours=1)
        
        # Clean minute requests
        for ip in list(self.minute_requests.keys()):
            self.minute_requests[ip] = [
                ts for ts in self.minute_requests[ip] if ts > cutoff_minute
            ]
            if not self.minute_requests[ip]:
                del self.minute_requests[ip]
        
        # Clean hour requests
        for ip in list(self.hour_requests.keys()):
            self.hour_requests[ip] = [
                ts for ts in self.hour_requests[ip] if ts > cutoff_hour
            ]
            if not self.hour_requests[ip]:
                del self.hour_requests[ip]
        
        self._last_cleanup = now
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/"]:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        now = datetime.now()
        
        # Cleanup old entries periodically
        self._cleanup_old_entries()
        
        # Check minute limit
        minute_cutoff = now - timedelta(minutes=1)
        recent_minute_requests = [
            ts for ts in self.minute_requests[client_ip] 
            if ts > minute_cutoff
        ]
        
        if len(recent_minute_requests) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {len(recent_minute_requests)} requests/minute")
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Limit: {self.requests_per_minute} requests per minute."
            )
        
        # Check hour limit
        hour_cutoff = now - timedelta(hours=1)
        recent_hour_requests = [
            ts for ts in self.hour_requests[client_ip]
            if ts > hour_cutoff
        ]
        
        if len(recent_hour_requests) >= self.requests_per_hour:
            logger.warning(f"Hourly rate limit exceeded for IP {client_ip}: {len(recent_hour_requests)} requests/hour")
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Limit: {self.requests_per_hour} requests per hour."
            )
        
        # Record request
        self.minute_requests[client_ip].append(now)
        self.hour_requests[client_ip].append(now)
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            self.requests_per_minute - len(recent_minute_requests) - 1
        )
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            self.requests_per_hour - len(recent_hour_requests) - 1
        )
        
        return response
