"""In-memory session tokens for the app lock.

Tokens live only in this process: restarting the app locks it again, and nothing
is written to disk. The server binds to the local machine, so this is meant to
stop other local processes and casual snooping from reading data without the
password, not to defend against an attacker who already controls the machine.
"""

import secrets
import threading
import time

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 30

_lock = threading.Lock()
_tokens: set[str] = set()
_failed_attempts = 0
_locked_until = 0.0


class TooManyAttemptsError(Exception):
    """Raised when password attempts are temporarily blocked."""

    def __init__(self, retry_after: int) -> None:
        super().__init__("Too many failed attempts")
        self.retry_after = retry_after


def issue_token() -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        _tokens.add(token)
    return token


def is_valid_token(token: str | None) -> bool:
    if not token:
        return False
    with _lock:
        return token in _tokens


def revoke_token(token: str | None) -> None:
    if not token:
        return
    with _lock:
        _tokens.discard(token)


def revoke_all_tokens() -> None:
    with _lock:
        _tokens.clear()


def check_attempts_allowed() -> None:
    """Raise TooManyAttemptsError while a lockout is in effect."""
    with _lock:
        remaining = _locked_until - time.monotonic()
    if remaining > 0:
        raise TooManyAttemptsError(int(remaining) + 1)


def record_failed_attempt() -> None:
    global _failed_attempts, _locked_until
    with _lock:
        _failed_attempts += 1
        if _failed_attempts >= MAX_FAILED_ATTEMPTS:
            _failed_attempts = 0
            _locked_until = time.monotonic() + LOCKOUT_SECONDS


def record_successful_attempt() -> None:
    global _failed_attempts
    with _lock:
        _failed_attempts = 0


def reset() -> None:
    """Clear all session state. Used by tests."""
    global _failed_attempts, _locked_until
    with _lock:
        _tokens.clear()
        _failed_attempts = 0
        _locked_until = 0.0
