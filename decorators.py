from functools import wraps

import jwt
from flask import abort, current_app, request

ROLES = [None, "customer", "staff", "manager", "admin"]


def bearer_required(minimum_role="customer"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth = request.headers.get("Authorization")

            if auth is None:
                abort(400, description="Token ausente")

            try:
                payload = jwt.decode(
                    auth.encode(),
                    current_app.config["SECRET_KEY"],
                    algorithms=["HS256"],
                )
            except Exception as e:
                print(e.args)
                abort(400, description="Token inválido")

            if ROLES.index(payload["role"]) < ROLES.index(minimum_role):
                abort(403, description="Cargo inválido")

            return f(payload["sub"], *args, **kwargs)

        return decorated_function

    return decorator
