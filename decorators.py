from enum import Enum
from functools import total_ordering, wraps

from bson import ObjectId
import jwt
from flask import abort, current_app, request


@total_ordering
class Role(Enum):
    ANONYMOUS = 0
    CUSTOMER = 1
    STAFF = 2
    MANAGER = 3
    ADMIN = 4

    @staticmethod
    def from_str(s: str) -> "Role":
        match s:
            case "customer":
                return Role.CUSTOMER
            case "staff":
                return Role.STAFF
            case "manager":
                return Role.MANAGER
            case "admin":
                return Role.ADMIN
            case _:
                return Role.ANONYMOUS

    def __lt__(self, other):
        if not self.__class__ is other.__class__:
            return NotImplemented

        return self.value < other.value


def bearer_required(minimum_role=Role.CUSTOMER):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth = request.headers.get("Authorization")

            if auth is None:
                abort(400, "Token ausente")

            try:
                payload = jwt.decode(
                    auth.encode(),
                    current_app.config["SECRET_KEY"],
                    algorithms=["HS256"],
                )
            except Exception as e:
                print(e.args)
                abort(400, "Token inválido")

            if Role.from_str(payload["role"]) < minimum_role:
                abort(403, "Cargo inválido")

            return f(ObjectId(payload["sub"]), *args, **kwargs)

        return decorated_function

    return decorator
