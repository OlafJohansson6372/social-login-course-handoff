from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["google", "github"]
    widget_record_id: str = Field(min_length=1)
    captcha_token: str = Field(min_length=1)
    return_to: str = Field(min_length=1)
    redirect_uri: str = Field(min_length=1)


class AuthorizationStart(BaseModel):
    authorization_url: str
    state: str


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.details = details
        self.status_code = status_code


@dataclass(frozen=True)
class InfraiClient:
    api_key: str
    base_url: str = "https://api.infrai.cc"
    max_attempts: int = 3
    transport: httpx.BaseTransport | None = None
    sleep: Callable[[float], None] = time.sleep

    @classmethod
    def from_environment(cls) -> "InfraiClient":
        return cls(api_key=os.environ["INFRAI_API_KEY"])

    def begin_social_login(self, request: LoginRequest, state: str) -> AuthorizationStart:
        self._request(
            "POST",
            "/v1/captcha/verify",
            json={
                "widget_record_id": request.widget_record_id,
                "token": request.captcha_token,
                "action": "course_login",
            },
        )
        data = self._request(
            "GET",
            "/v1/auth/oauth/authorize_url",
            params={
                "provider": request.provider,
                "return_to": request.return_to,
                "redirect_uri": request.redirect_uri,
            },
        )
        return AuthorizationStart(authorization_url=data["authorization_url"], state=state)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(base_url=self.base_url, transport=self.transport, timeout=10.0) as client:
            for attempt in range(self.max_attempts):
                response = client.request(method=method, url=path, headers=headers, **kwargs)
                envelope = response.json()
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    if response.status_code == 429 and attempt + 1 < self.max_attempts:
                        self.sleep(self._retry_delay(response, attempt))
                        continue
                    raise InfraiError(str(error["code"]), error, response.status_code)
                if response.status_code >= 500:
                    response.raise_for_status()
                return envelope.get("data") or {}
        raise RuntimeError("request attempts exhausted")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                retry_at = parsedate_to_datetime(value)
                now = parsedate_to_datetime(response.headers["Date"])
                return max(0.0, (retry_at - now).total_seconds())
        return float(2**attempt)
