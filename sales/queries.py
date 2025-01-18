BASE_QUERY = [
    {
        "$lookup": {
            "from": "users",
            "localField": "customer_id",
            "foreignField": "_id",
            "as": "user",
            "pipeline": [
                {"$project": {"name": 1, "email": 1}},
                {"$set": {"_id": {"$toString": "$_id"}}},
            ],
        }
    },
    {"$unset": ["customer_id"]},
    {
        "$set": {
            "temp": "$customer",
            "customer": {"$arrayElemAt": ["$user", 0]},
            "items": {
                "$map": {
                    "input": "$items",
                    "as": "item",
                    "in": {
                        "_id": {"$toString": "$$item._id"},
                        "price": {"$toDouble": "$$item.price"},
                        "qty": "$$item.qty",
                        "name": "$$item.name",
                    },
                }
            },
            "tax": {"$toDouble": "$tax"},
            "shipping": {"$toDouble": "$shipping"},
            "_id": {"$toString": "$_id"},
            "total": {
                "$toDouble": {
                    "$sum": [
                        {
                            "$sum": {
                                "$map": {
                                    "input": "$items",
                                    "as": "item",
                                    "in": {"$multiply": ["$$item.price", "$$item.qty"]},
                                }
                            }
                        },
                        {"$toDouble": "$tax"},
                        {"$toDouble": "$shipping"},
                    ]
                }
            },
        }
    },
    {"$set": {"customer": {"$ifNull": ["$customer", "$temp", "$customer"]}}},
    {"$unset": ["temp", "user"]},
]

LOOKUP_PRODUCTS = [
    {
        "$lookup": {
            "from": "species",
            "localField": "items._id",
            "foreignField": "_id",
            "as": "prods",
        }
    }
]