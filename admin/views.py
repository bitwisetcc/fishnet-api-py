import os
import random
from flask import Blueprint, jsonify, send_file
from openpyxl import Workbook
from connections import db

admin = Blueprint("admin", __name__)


def product_to_row(prod):
    return [
        str(str(prod["_id"])),
        prod["name"],
        prod["scientificName"],
        float(prod["price"].to_decimal()),
    ]


@admin.get("/backup/prods")
def backup_products():
    workbook = Workbook()
    sheet = workbook.active

    data = db["teste_species"].find()
    for row in data:
        sheet.append(product_to_row(row))

    backup_id = random.randrange(start=1)

    if not os.path.exists("/tmp/fishnet/backup"):
        os.makedirs("/tmp/fishnet/backup")

    temp_path = f"/tmp/fishnet/backup/{backup_id}.xlsx"

    workbook.save(temp_path)

    try:
        return send_file(temp_path)
    except Exception as e:
        return jsonify({"message": e.args}), 400
    # finally:
    #     os.remove(temp_path)


@admin.get("/backup/sales")
def backup_sales():
    data = db["sales"]
