"""Async HTTP client for ITI Enterprise AI Provider."""

import asyncio
import time
from typing import Any, Dict, Optional, Tuple
import httpx
from fastapi import HTTPException
from proxy.app.settings import settings
from proxy.app.utils import logger, log_request_metrics


class ITIClient:
    """Async HTTP client wrapper for ITI Enterprise AI Provider."""

    def __init__(self) -> None:
        self.client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        headers = {
            "Authorization": f"Bearer {settings.iti_api_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(
            base_url=settings.iti_base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(120.0),
        )

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None

    async def send_chat_request(
        self, endpoint: str, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int, float]:
        if not self.client:
            await self.start()

        max_attempts = max(1, settings.max_retries)
        backoff_delay = 1.0
        start_time = time.perf_counter()
        model_id = payload.get("model_id", "unknown")
        request_id = "pending"
        last_exception = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.client.post(endpoint, json=payload)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if response.status_code == 200:
                    data = response.json()
                    request_id = data.get("request_id", f"req_{int(time.time())}")
                    log_request_metrics(
                        request_id=request_id,
                        endpoint=endpoint,
                        model=model_id,
                        status_code=response.status_code,
                        latency_ms=latency_ms,
                    )
                    return data, response.status_code, latency_ms

                if response.status_code >= 500 or response.status_code == 429:
                    logger.warning(
                        f"ITI API returned status {response.status_code} on attempt {attempt}/{max_attempts}."
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(backoff_delay)
                        backoff_delay *= 2.0
                        continue

                try:
                    error_json = response.json()
                    error_msg = (
                        error_json.get("error", {}).get("message")
                        or error_json.get("detail")
                        or error_json.get("message")
                        or response.text
                    )
                except Exception:
                    error_msg = response.text or f"HTTP {response.status_code} Error"

                log_request_metrics(
                    request_id=request_id,
                    endpoint=endpoint,
                    model=model_id,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                )

                raise HTTPException(status_code=response.status_code, detail=error_msg)

            except (httpx.TransportError, httpx.TimeoutException) as exc:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                last_exception = exc
                if attempt < max_attempts:
                    await asyncio.sleep(backoff_delay)
                    backoff_delay *= 2.0
                else:
                    raise HTTPException(
                        status_code=504,
                        detail=f"Gateway timeout contacting upstream ITI service: {exc}",
                    )

        if last_exception:
            raise HTTPException(
                status_code=502,
                detail=f"Bad gateway contacting upstream ITI service: {last_exception}",
            )


iti_client = ITIClient()
