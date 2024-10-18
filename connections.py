from os import environ
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Certifique-se de que a variável MONGODB_URI esteja definida no seu arquivo .env
client = MongoClient(environ.get("MONGODB_URI"), server_api=ServerApi("1"))
db = client["FinFusion"]
