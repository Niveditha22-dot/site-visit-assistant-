import os
import time
import hashlib
import hmac

import jwt
from fastapi import Depends, Header, HTTPException


def _secret() -> str:
    return os.environ["SECRET_KEY"]


def verify_password(password: str, stored: str) -> bool:
    salt_hex, hash_hex = stored.split("$")
    h = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(h.hex(), hash_hex)


def make_token(user_id: int, role: str, **extra) -> str:
    claims = {"sub": str(user_id), "role": role, "exp": int(time.time()) + 8 * 3600, **extra}
    return jwt.encode(claims, _secret(), algorithm="HS256")


def current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not signed in")
    try:
        data = jwt.decode(authorization[7:], _secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired, please sign in again")
    return {"id": int(data["sub"]), "role": data["role"], "since": data.get("since")}


def require_roles(*roles: str):
    def checker(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, "You do not have access to this")
        return user
    return checker
