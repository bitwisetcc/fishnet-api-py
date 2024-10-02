from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_pydantic import validate

from connections import db

collection = db["users"]
users = Blueprint("users", __name__)

# [POST] /users is implemented as /auth/register
# { is_company, name, email, phone, rg*1, cpf*1, cnpj*2, serial_CC, expiration_CC, backserial_CC, zip_code?, address? }

