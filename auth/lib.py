from datetime import datetime as dt
import jwt


def encode_auth_token(user, secret) -> str:
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "name": user["name"],
    }

    return  jwt.encode(payload, secret)


def decode_auth_token(auth_token, secret) -> str:
    return jwt.decode(auth_token, secret)["sub"]
