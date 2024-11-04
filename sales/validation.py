from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Self
from bson import Decimal128, ObjectId
from bson.errors import InvalidId


@dataclass
class AnonymousUser:
    name: str
    surname: str
    addr: str
    cep: str
    email: str
    city: str | None
    state: str | None
    tel: str | None

    @staticmethod
    def from_dict(d: dict[str, str]) -> Self:
        return AnonymousUser(**d)


@dataclass
class SaleItem:
    id: ObjectId
    price: Decimal128
    qty: int

    _required = ["id", "price", "qty"]

    @staticmethod
    def from_dict(d: dict[str, str]) -> Self:
        for field in d:
            if field not in SaleItem._required:
                raise AssertionError(f"Missing field '{field}' for SaleItem")

        try:
            _id = ObjectId(d["id"])
        except InvalidId:
            raise AssertionError(f"Invalid oid for SaleItem: '{d['id']}'")

        return SaleItem(_id, Decimal128(Decimal(d["price"])), d["qty"])

    def to_dict(self) -> dict[str,]:
        return {
            "_id": ObjectId(self.id),
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
