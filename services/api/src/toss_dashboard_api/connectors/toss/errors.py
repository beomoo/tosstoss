from __future__ import annotations


class TossConnectorError(Exception):
    """Base class whose message and repr contain safe metadata only."""


class TossConfigurationError(TossConnectorError):
    def __init__(self, credential_state: str) -> None:
        self.credential_state = credential_state
        super().__init__(f"Toss credentials are unavailable ({credential_state}).")


class TossBoundaryError(TossConnectorError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Toss request was rejected by the connector boundary ({reason}).")


class TossLifecycleError(TossConnectorError):
    def __init__(self) -> None:
        super().__init__("Toss connector is closed.")


class TossTransportError(TossConnectorError):
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint
        super().__init__(f"Toss transport failed (endpoint={endpoint}).")


class TossResponseContractError(TossConnectorError):
    def __init__(self, endpoint: str, reason: str) -> None:
        self.endpoint = endpoint
        self.reason = reason
        super().__init__(f"Toss response contract failed (endpoint={endpoint}, reason={reason}).")


class TossContentTypeError(TossResponseContractError):
    def __init__(self, endpoint: str) -> None:
        super().__init__(endpoint, "unexpected-content-type")


class TossResponseTooLargeError(TossResponseContractError):
    def __init__(self, endpoint: str, limit_bytes: int) -> None:
        self.limit_bytes = limit_bytes
        super().__init__(endpoint, "response-too-large")


class TossRedirectError(TossConnectorError):
    def __init__(self, endpoint: str, status_code: int) -> None:
        self.endpoint = endpoint
        self.status_code = status_code
        super().__init__(
            f"Toss redirect was refused (endpoint={endpoint}, status_code={status_code})."
        )


class TossOAuthError(TossConnectorError):
    def __init__(self, status_code: int, oauth_code: str) -> None:
        self.status_code = status_code
        self.oauth_code = oauth_code
        super().__init__(
            f"Toss OAuth request failed (status_code={status_code}, oauth_code={oauth_code})."
        )


class TossInvalidClientError(TossOAuthError):
    pass


class TossOAuthPermissionError(TossOAuthError):
    pass


class TossHttpError(TossConnectorError):
    def __init__(
        self,
        *,
        endpoint: str,
        status_code: int,
        provider_code: str | None,
        request_id: str | None,
    ) -> None:
        self.endpoint = endpoint
        self.status_code = status_code
        self.provider_code = provider_code
        self.request_id = request_id
        safe_code = provider_code or "unknown"
        super().__init__(
            f"Toss HTTP request failed (endpoint={endpoint}, "
            f"status_code={status_code}, provider_code={safe_code})."
        )


class TossAuthenticationError(TossHttpError):
    pass


class TossPermissionError(TossHttpError):
    pass


class TossRateLimitError(TossHttpError):
    pass


class TossServerError(TossHttpError):
    pass


class TossRetryExhaustedError(TossHttpError):
    def __init__(
        self,
        *,
        endpoint: str,
        rate_group: str,
        status_code: int,
        provider_code: str | None,
        request_id: str | None,
        attempt_count: int,
        retry_after_seconds: int | None,
    ) -> None:
        self.rate_group = rate_group
        self.attempt_count = attempt_count
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            endpoint=endpoint,
            status_code=status_code,
            provider_code=provider_code,
            request_id=request_id,
        )
        safe_code = provider_code or "unknown"
        self.args = (
            f"Toss retry budget was exhausted (endpoint={endpoint}, "
            f"rate_group={rate_group}, status_code={status_code}, "
            f"provider_code={safe_code}, attempt_count={attempt_count}).",
        )


class TossRetryDeferredError(TossRateLimitError):
    def __init__(
        self,
        *,
        endpoint: str,
        rate_group: str,
        status_code: int,
        provider_code: str | None,
        request_id: str | None,
        attempt_count: int,
        retry_after_seconds: int,
    ) -> None:
        self.rate_group = rate_group
        self.attempt_count = attempt_count
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            endpoint=endpoint,
            status_code=status_code,
            provider_code=provider_code,
            request_id=request_id,
        )
        safe_code = provider_code or "unknown"
        self.args = (
            f"Toss retry was deferred (endpoint={endpoint}, rate_group={rate_group}, "
            f"status_code={status_code}, provider_code={safe_code}, "
            f"attempt_count={attempt_count}, "
            f"retry_after_seconds={retry_after_seconds}).",
        )
