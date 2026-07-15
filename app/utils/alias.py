import re
import secrets

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

# Valid custom aliases: 3-32 chars of letters, digits, hyphen, underscore.
ALIAS_PATTERN = re.compile(r"[A-Za-z0-9_-]{3,32}")

# Words that must not be used as aliases so they can't shadow API routes.
RESERVED_ALIASES = frozenset(
    {"api", "health", "docs", "redoc", "openapi.json", "static", "favicon.ico"}
)


def generate_alias(length: int) -> str:
    """Return a cryptographically-random base62 string of the given length."""
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))


def is_reserved(alias: str) -> bool:
    return alias.lower() in RESERVED_ALIASES
