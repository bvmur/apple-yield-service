from argon2 import PasswordHasher

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Пароль → хеш Argon2 (для хранения в БД)."""
    return _hasher.hash(password)