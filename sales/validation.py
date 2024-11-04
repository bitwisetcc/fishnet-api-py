from dataclasses import dataclass
from datetime import datetime
from decimal import Inexact
from enum import Enum
from typing import Optional, Self
from bson import Decimal128, ObjectId
from bson.errors import InvalidId


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
    id: ObjectId
    price: Decimal128
    qty: int

    _required = ["id", "price", "qty"]

    @staticmethod
    def from_dict(d: dict[str, str | float | int]) -> Self:
        for field in SaleItem._required:
            if field not in d:
                raise AssertionError(f"Missing field '{field}' for SaleItem")

        try:
            _id = ObjectId(d["id"])
            _price = Decimal128(str(d["price"]))
        except InvalidId:
            raise AssertionError(f"Invalid oid for SaleItem: '{d['id']}'")
        except Inexact:
            raise AssertionError(f"Failed price to cast to Decimal128: {d['qty']}")

        return SaleItem(_id, _price, d["qty"])

    def to_json(self) -> dict[str, str | float | int]:
        return {
            "_id": str(self.id),
            "price": float(self.price.to_decimal()),
            "qty": self.qty,
        }


class PaymentMethod(Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    PIX = "pix"


class SaleStatus(Enum):
    PROGRESS = 0
    DONE = 1
    CANCELLED = 2


class Sale:
    customer: ObjectId | AnonymousUser
    items: list[SaleItem]
    tax: Decimal128
    shipping: Decimal128
    shipping_provider: str
    payment_method: PaymentMethod
    payment_provider: str | None
    status: SaleStatus
    date: datetime
