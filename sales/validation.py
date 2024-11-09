from dataclasses import dataclass
from datetime import datetime
from decimal import Inexact, InvalidOperation
from enum import Enum
from typing import Any, Optional, Self
from bson import Decimal128, ObjectId
from bson.errors import InvalidId
from flask import current_app
import jwt

from connections import db

product_collection = db["teste_species"]


@dataclass
class AnonymousUser:
    name: str
    surname: str
    addr: str
    cep: str
    email: str
    city: Optional[str] = None
    state: Optional[str] = None
    tel: Optional[str] = None

    @staticmethod
    def from_dict(d: dict[str, str]) -> Self:
        if d is None:
            raise AssertionError("Expected 'customer' dict, got None instead")
        for k, v in d.items():
            if not isinstance(v, str):
                raise AssertionError(f"Invalid field 'customer.{k}': {v} <{type(v)}>")

        try:
            return AnonymousUser(**d)
        except TypeError as error:
            raise AssertionError(error)

    def to_json(self) -> dict[str, str]:
        return {
            "name": self.name,
            "surname": self.surname,
            "addr": self.addr,
            "cep": self.cep,
            "email": self.email,
            "city": self.city,
            "state": self.state,
            "tel": self.tel,
        }


@dataclass
class SaleItem:
    # TODO: decrement items available quantity
    id: ObjectId
    price: Decimal128
    qty: int

    _required = ["id", "qty"]

    @staticmethod
    def from_dict(d: dict[str, str | int]) -> Self:
        for field in SaleItem._required:
            assert field in d, f"Missing field '{field}' for SaleItem"

        try:
            _id = ObjectId(d["id"])
            _price = product_collection.find_one({"_id": _id})["price"]
        except InvalidId:
            raise AssertionError(f"Invalid oid for SaleItem: '{d['id']}'")

        return SaleItem(_id, _price, d["qty"])

    def to_json(self) -> dict[str, str | float | int]:
        return {
            "_id": str(self.id),
            "price": float(self.price.to_decimal()),
            "qty": self.qty,
        }

    def to_bson(self) -> dict[str, str | float | int]:
        return {
            "_id": self.id,
            "price": self.price,
            "qty": self.qty,
        }


class PaymentMethod(Enum):
    MASTERCARD = "mastercard"
    VISA = "visa"
    PIX = "pix"


class SaleStatus(Enum):
    PROGRESS = 0
    DONE = 1
    CANCELLED = 2

    def __str__(self) -> str:
        return self.value


@dataclass
class Sale:
    items: list[SaleItem]
    tax: Decimal128
    shipping: Decimal128
    shipping_provider: str
    payment_method: PaymentMethod
    status: SaleStatus
    date: datetime
    payment_provider: Optional[str] = None
    customer: Optional[AnonymousUser] = None
    customer_id: Optional[ObjectId] = None

    @staticmethod
    def from_dict(d: dict[str, Any], token=None) -> Self:
        assert d.get("customer") or token, "Missing customer data"

        assert d.get("items") is not None and len(d["items"]) > 0, "The cart is empty"
        _items = [SaleItem.from_dict(item) for item in d["items"]]

        try:
            _tax = Decimal128(str(d.get("tax")))
            _shipping = Decimal128(str(d.get("shipping")))
        except (InvalidOperation, Inexact) as e:
            raise AssertionError("Failed cast to Decimal128: 'tax' or 'shipping'")

        assert isinstance(d.get("shipping_provider"), str), "Invalid shipping_provider"

        _payment_method = PaymentMethod(d.get("payment_method"))
        assert (
            _payment_method == PaymentMethod.PIX
            or d.get("payment_provider") is not None
        ), "Missing payment_provider"
        assert not (
            _payment_method == PaymentMethod.PIX
            and d.get("payment_provider") is not None
        ), "PIX payments should not have a payment_provider"

        _customer_id = None
        _customer = None

        if token:
            try:
                payload = jwt.decode(
                    token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
                )
                _customer_id = ObjectId(payload.get("sub"))
            except jwt.DecodeError:
                raise AssertionError("Invalid auth token")
            except InvalidId:
                raise AssertionError("Invalid oid in auth token")
        else:
            # TODO: avoid anonymous purchases from using existing e-mails
            _customer = AnonymousUser.from_dict(d.get("customer"))

        # Vulnerabilities: ValueError for SaleStatus and PaymentMethod
        return Sale(
            _items,
            _tax,
            _shipping,
            d.get("shipping_provider"),
            PaymentMethod(d.get("payment_method")),
            SaleStatus(d.get("status")),
            datetime.now(),
            d.get("payment_provider"),
            _customer,
            _customer_id,
        )

    def to_bson(self) -> dict[str, Any]:
        return {
            "items": [item.to_bson() for item in self.items],
            "tax": self.tax,
            "shipping": self.shipping,
            "shipping_provider": self.shipping_provider,
            "payment_method": self.payment_method.value,
            "status": self.status.value,
            "date": self.date,
            "payment_provider": self.payment_provider,
            "customer": self.customer and self.customer.to_json(),
            "customer_id": self.customer_id,
        }
