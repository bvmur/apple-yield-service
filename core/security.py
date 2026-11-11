from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError 

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Пароль → хеш Argon2 (для хранения в БД)."""
    return _hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Совпадает ли введённый пароль с хешем из БД."""
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False