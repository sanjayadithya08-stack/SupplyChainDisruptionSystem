import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_middleware")

# Simple in-memory rate limiting counter
RATE_LIMIT_STORE = {}
MAX_REQUESTS_PER_MINUTE = 60

class AntigravityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Request logging and Rate Limiting.
        Antigravity Rule: Middleware must not crash the request if logging fails.
        """
        start_time = time.time()
        
        # Rate limiting logic
        client_ip = request.client.host if request.client else "unknown"
        current_minute = int(time.time() / 60)
        
        rate_key = f"{client_ip}_{current_minute}"
        try:
            count = RATE_LIMIT_STORE.get(rate_key, 0)
            if count >= MAX_REQUESTS_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded. Max 60 requests per minute."}
                )
            RATE_LIMIT_STORE[rate_key] = count + 1
            
            # Clean up old keys (primitive approach to prevent memory leak)
            if len(RATE_LIMIT_STORE) > 10000:
                RATE_LIMIT_STORE.clear()
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open if rate limiter breaks
            pass

        # Request processing
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"CRITICAL: Unhandled exception in {request.url.path}: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error. System recovered safely."}
            )
