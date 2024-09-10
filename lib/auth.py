import datetime as dt
from typing import Dict
import bcrypt
import jwt


class UserNotFound(Exception):
    pass


def encode_auth_token(user_id, secret) -> Exception | str:
    try:
        payload = {
            "exp": dt.datetime.now() + dt.timedelta(days=0, seconds=5),
            "iat": dt.datetime.now(),
            "sub": user_id,
        }
        return jwt.encode(payload, secret, algorithm="HS256")
    except Exception as e:
        raise e


def decode_auth_token(auth_token, secret) -> str:
    # Possible exceptions: jwt.ExpiredSignatureError, jwt.InvalidTokenError
    return jwt.decode(auth_token, secret)["sub"]


def find_user_by_email(email) -> Dict[str, str | bytes]:
    return {
        "email": email,
        "password": bcrypt.hashpw(b"123456", bcrypt.gensalt()),
    }
    user = customers.find_one({"email": email})
    if user is None:
        user = employees.find_one({"email": email})
        if user is None:
            raise Exception("User does not exist.")
    return user
