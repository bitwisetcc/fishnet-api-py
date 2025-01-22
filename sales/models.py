from collections import defaultdict
from datetime import datetime
from typing import Any, Dict

import pymongo
from bson import Regex
from fpdf import FPDF

from connections import db

product_collection = db["teste_species"]

VALID_ORDERINGS = ["total", "date", "customer.name"]

SALE_ITEM_SCHEMA = {
    "type": "object",
    "required": ["_id", "quantity"],
    "properties": {
        "_id": {"type": "string"},
        "quantity": {"type": "integer", "minimum": 1},
    },
}

ADDRESS_SCHEMA = {
    "type": "object",
    "required": ["cep", "number"],
    "properties": {
        "cep": {"type": "string"},
        "number": {"type": "integer", "minimum": 1, "maximum": 10000},
        "street": {"type": "string"},
        "city": {"type": "string"},
        "uf": {"type": "string"},
    },
}

ANONYMOUS_USER_SCHEMA = {
    "type": "object",
    "required": ["name", "addr", "email"],
    "properties": {
        "name": {"type": "string"},
        "addr": ADDRESS_SCHEMA,
        "email": {"type": "string", "format": "email"},
        "phone": {"type": "string"},
    },
}

SALE_SCHEMA = {
    "type": "object",
    "required": ["items", "tax", "shipping", "shipping_provider", "payment_method"],
    "properties": {
        "items": {"type": "array", "minItems": 1, "items": SALE_ITEM_SCHEMA},
        "tax": {"type": "number", "exclusiveMinimum": 0},
        "shipping": {"type": "number", "minimum": 0},
        "shipping_provider": {"type": "string"},
        "payment_method": {
            "type": "string",
            "enum": ["debit", "credit", "pix"],
        },
        "payment_provider": {"type": "string"},
        "status": {
            "type": "integer",
            "enum": [0, 1, 2],
        },
        "created_at": {"type": "string"},
        "customer": ANONYMOUS_USER_SCHEMA,
        "customer_id": {"type": "string"},
    },
}


def generate_report(doc: dict[str, Any]) -> FPDF:
    pdf = FPDF()

    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(w=0, h=10, txt=doc["_id"], ln=1, align="L")
    pdf.cell(w=0, h=10, txt=doc["customer"]["name"], ln=1, align="L")
    pdf.cell(w=0, h=10, txt=doc["customer"]["email"], ln=1, align="L")
    pdf.cell(
        w=0,
        h=10,
        txt=f"Enviado via {doc['shipping_provider']} com taxa de R${doc['shipping']}",
        ln=1,
        align="L",
    )
    pdf.cell(w=0, h=10, txt="Itens comprados", ln=1, align="L")

    header = ["id", "nome", "preço unitário", "quantidade"]
    prods = [
        (item["_id"], p["name"], str(item["price"]), str(item["qty"]))
        for item, p in zip(doc["items"], doc["prods"])
    ]
    col_width = [60, 50, 35, 35]

    for i, (h, w) in enumerate(zip(header, col_width)):
        pdf.cell(
            w=w, h=8, txt=h, border=1, align="C", ln=int(bool(i == len(header) - 1))
        )

    for prod in prods:
        for i, (field, w) in enumerate(zip(prod, col_width)):
            pdf.cell(
                w=w,
                h=8,
                txt=field,
                border=1,
                align="C",
                # ln=int(bool(i == len(header) - 1)),
            )
        pdf.cell(w=0, h=8, txt="", border=0, align="C", ln=1)

    pdf.cell(w=0, h=10, txt=f"Total: R${doc['total']}", ln=1, align="L")

    return pdf


def parse_filters(args: Dict[str, str]):
    filters: dict[str, Any] = defaultdict(dict)
    ordering = {}

    if "username" in args:
        filters["customer.name"] = {"$regex": Regex(args["username"], "i")}

    if "payment_method" in args:
        filters["payment_method"] = {"$regex": Regex(args["payment_method"], "i")}

    if "status" in args:
        try:
            filters["status"] = int(args["status"])
        except ValueError:
            raise AssertionError("Status inválido")

    if "min_price" in args:
        filters["total"]["$gte"] = float(args["min_price"])

    if "max_price" in args:
        filters["total"]["$lte"] = float(args["max_price"])

    if "products" in args:
        filters["items._id"] = {"$in": args["products"].split(",")}

    if "min_date" in args:
        try:
            filters["date"]["$gte"] = parse_date(args["min_date"])
        except ValueError as e:
            raise AssertionError(str(e.args[0]))

    if "max_date" in args:
        try:
            filters["date"]["$lte"] = parse_date(args["max_date"])
        except ValueError as e:
            raise AssertionError(e.args[0])

    if "ordering" in args:
        symbol_mapping = {"+": pymongo.ASCENDING, "-": pymongo.DESCENDING}
        for ord in args["ordering"].split(","):
            key = ord[1:]
            direction = symbol_mapping.get(ord[0])

            assert key in VALID_ORDERINGS and direction, f"Invalid ordering '{ord}'"
            ordering[key] = direction

    if not ordering:
        ordering["_id"] = pymongo.ASCENDING


def parse_date(date_str):
    try:
        # Tentar converter a data no formato ISO 8601 (exemplo: "2023-11-24")
        return datetime.fromisoformat(date_str)
    except ValueError:
        # Se não for nesse formato, tentar como timestamp em milissegundos
        try:
            return datetime.fromtimestamp(int(date_str) // 1000)
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")
