import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_middleware")

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config

# Simple in-memory rate limiting counter
RATE_LIMIT_STORE = {}
MAX_REQUESTS_PER_MINUTE = Config.RATE_LIMIT_PER_MINUTE
# The bundled dashboards run on the same machine and fire ~10 requests per refresh,
# which tripped the old 60/min limit almost immediately. Loopback clients are exempt.
EXEMPT_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}

class _Skip(Exception):
    pass


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
        is_api = not request.url.path.startswith(("/assets", "/favicon"))
        try:
            if client_ip in EXEMPT_HOSTS or not is_api:
                raise _Skip()
            count = RATE_LIMIT_STORE.get(rate_key, 0)
            if count >= MAX_REQUESTS_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    content={"error": f"Rate limit exceeded. Max {MAX_REQUESTS_PER_MINUTE} requests per minute."}
                )
            RATE_LIMIT_STORE[rate_key] = count + 1
            
            # Drop counters from previous minutes to prevent unbounded growth
            if len(RATE_LIMIT_STORE) > 1000:
                for k in [k for k in RATE_LIMIT_STORE if not k.endswith(f"_{current_minute}")]:
                    RATE_LIMIT_STORE.pop(k, None)
        except _Skip:
            pass
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
