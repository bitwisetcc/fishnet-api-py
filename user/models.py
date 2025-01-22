from collections import defaultdict
from typing import Dict

from bson import Regex
import pymongo

VALID_ORDERINGS = ["username", "created_at"]


def parse_filters(args: Dict[str, str]):
    filters = defaultdict(dict)
    ordering = {}

    if "name" in args:
        filters["name"] = {"$regex": Regex(args["name"], "i")}

    if "email" in args:
        filters["email"] = {"$regex": Regex(args["email"])}

    if "tel" in args:
        filters["tel"] = {"$regex": Regex(rf"\b{args['tel']}\d*")}

    if "role" in args:
        filters["role"] = "role"

    if "ordering" in args:
        symbol_mapping = {"+": pymongo.ASCENDING, "-": pymongo.DESCENDING}
        for ord in args["ordering"].split(","):
            key = ord[1:]
            direction = symbol_mapping.get(ord[0])

            assert key in VALID_ORDERINGS and direction, f"Invalid ordering '{ord}'"

            ordering[key] = direction

    if not ordering:
        ordering["_id"] = pymongo.ASCENDING

    return [{"$match": filters}, {"$sort": ordering}]
