import httpx
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class GitHubRateLimitError(Exception):
    pass

class GitHubClient:    
    BASE_URL = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.access_token}",
            "X-GitHub-Api-Version": self.API_VERSION,
        }

    async def _request_with_retry(self, method: str, endpoint: str, max_retries: int = 3, **kwargs) -> httpx.Response:
        url = f"{self.BASE_URL}{endpoint}"
        
        async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
            for attempt in range(max_retries):
                response = await client.request(method, url, **kwargs)
                
                if response.status_code in (403, 429):
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_seconds = int(retry_after)
                        logger.warning(f"GitHub Rate Limit hit. Retrying after {wait_seconds} seconds...")
                        await asyncio.sleep(wait_seconds)
                        continue
                        
                    x_ratelimit_remaining = response.headers.get("X-RateLimit-Remaining")
                    if x_ratelimit_remaining == "0":
                        reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
                        import time
                        wait_seconds = max(0, reset_timestamp - int(time.time()))
                        if wait_seconds > 60:
                            raise GitHubRateLimitError(f"Rate limit exhausted. Reset in {wait_seconds}s.")
                        
                        logger.warning(f"GitHub Primary Rate Limit hit. Retrying after {wait_seconds} seconds...")
                        await asyncio.sleep(wait_seconds)
                        continue
                    
                    if response.status_code == 403 and "rate limit" not in response.text.lower():
                        break
                        
                response.raise_for_status()
                return response
                
            response.raise_for_status()
            return response

    async def get_user_repositories(self) -> list[Dict[str, Any]]:
        """Fetch repositories available to the authenticated user."""
        response = await self._request_with_retry("GET", "/user/repos?per_page=100&sort=updated")
        return response.json()
        
    async def create_webhook(self, owner: str, repo: str, webhook_url: str, secret: str) -> Dict[str, Any]:
        """Register a push webhook for the repository."""
        payload = {
            "name": "web",
            "active": True,
            "events": ["push"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "insecure_ssl": "0",
                "secret": secret
            }
        }
        response = await self._request_with_retry("POST", f"/repos/{owner}/{repo}/hooks", json=payload)
        return response.json()
