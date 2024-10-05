from decimal import Decimal
from flask import Flask, request, jsonify
from flask_pydantic import validate
from pydantic import BaseModel, EmailStr, Field, field_validator
from pymongo import MongoClient
from bson import ObjectId
from datetime import date
from bson.errors import InvalidId

app = Flask(__name__)

# Conectar ao MongoDB
client = MongoClient("mongodb+srv://api-tester:QyHLaCgakHRjtn9n@finfusion1.uzpenme.mongodb.net/?retryWrites=true&w=majority&appName=FinFusion1")
db = client['FinFusion']

# Coleções
species_collection = db['teste_species']
customer_collection = db['customer']
employee_collection = db['employee']

# Modelos de Dados
class SpeciesModel(BaseModel):
    name_species: str
    price: Decimal
    picture: str
    description: str
    ecosystem: str
    feeding: str
    size: str
    tank_size: str
    velocity: str
    origin: str
    social_behavior: str

    @field_validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('The price must be greater than zero.')
        return v

class CustomerModel(BaseModel):
    is_company: bool
    name: str
    email: EmailStr
    cellphone: str = Field(..., regex=r'^\d{11}$')
    birth_date: date
    rg: int
    cpf: str = Field(..., regex=r'^\d{11}$')
    cnpj: str = Field(None, regex=r'^\d{14}$')
    serial_cc: str = Field(..., min_length=16, max_length=16)
    expiration_cc: str = Field(..., min_length=5, max_length=5)
    backserial_cc: str = Field(..., min_length=3, max_length=3)

    @field_validator('expiration_cc')
    def validate_expiration_format(cls, v):
        if not (v[:2].isdigit() and v[3:].isdigit() and v[2] == '/'):
            raise ValueError("Expiration date must be in MM/YY format")
        return v

class EmployeeModel(BaseModel):
    name: str
    email: EmailStr
    cellphone: str
    birth_date: date
    rg: str
    cpf: str = Field(..., regex=r'^\d{11}$')
    status: str
    job_sector: str
    job_title: str

# Conversão de ObjectId
def to_dict(item):
    item['_id'] = str(item['_id'])
    return item

# Rotas CRUD - Species (Produtos)
@app.route('/species', methods=['POST'])
@validate()
def create_species(body: SpeciesModel):
    species = body.dict()
    result = species_collection.insert_one(species)
    return jsonify(str(result.inserted_id)), 201

@app.route('/species', methods=['GET'])
def get_species():
    species = list(species_collection.find())
    return jsonify([to_dict(f) for f in species]), 200

@app.route('/species/<id>', methods=['GET'])
def get_species_by_id(id):
    try:
        species = species_collection.find_one({'_id': ObjectId(id)})
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400
    if species:
        return jsonify(to_dict(species)), 200
    return jsonify({"error": "Species not found"}), 404

@app.route('/species/<id>', methods=['PUT'])
@validate()
def update_species(id, body: SpeciesModel):
    updated_species = body.dict()
    result = species_collection.update_one({'_id': ObjectId(id)}, {'$set': updated_species})
    if result.matched_count:
        return jsonify({"message": "Species updated"}), 200
    return jsonify({"error": "Species not found"}), 404

@app.route('/species/<id>', methods=['DELETE'])
def delete_species(id):
    result = species_collection.delete_one({'_id': ObjectId(id)})
    if result.matched_count and result.modified_count:
        return jsonify({"message": "Species updated"}), 200
    elif result.matched_count:
        return jsonify({"message": "No changes were made"}), 200
    else:
        return jsonify({"error": "Species not found"}), 404

# Rotas CRUD - Customer (Clientes)
@app.route('/customer', methods=['POST'])
@validate()
def create_customer(body: CustomerModel):
    customer = body.dict()
    result = customer_collection.insert_one(customer)
    return jsonify(str(result.inserted_id)), 201

@app.route('/customer', methods=['GET'])
def get_customers():
    customers = list(customer_collection.find())
    return jsonify([to_dict(c) for c in customers]), 200

@app.route('/customer/<id>', methods=['GET'])
def get_customer_by_id(id):
    customer = customer_collection.find_one({'_id': ObjectId(id)})
    if customer:
        return jsonify(to_dict(customer)), 200
    return jsonify({"error": "Customer not found"}), 404

@app.route('/customer/<id>', methods=['PUT'])
@validate()
def update_customer(id, body: CustomerModel):
    updated_customer = body.dict()
    result = customer_collection.update_one({'_id': ObjectId(id)}, {'$set': updated_customer})
    if result.matched_count:
        return jsonify({"message": "Customer updated"}), 200
    return jsonify({"error": "Customer not found"}), 404

@app.route('/customer/<id>', methods=['DELETE'])
def delete_customer(id):
    result = customer_collection.delete_one({'_id': ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "Customer deleted"}), 200
    return jsonify({"error": "Customer not found"}), 404

# Rotas CRUD - Employee (Funcionários)
@app.route('/employee', methods=['POST'])
@validate()
def create_employee(body: EmployeeModel):
    employee = body.dict()
    result = employee_collection.insert_one(employee)
    return jsonify(str(result.inserted_id)), 201

@app.route('/employee', methods=['GET'])
def get_employees():
    employees = list(employee_collection.find())
    return jsonify([to_dict(e) for e in employees]), 200

@app.route('/employee/<id>', methods=['GET'])
def get_employee_by_id(id):
    employee = employee_collection.find_one({'_id': ObjectId(id)})
    if employee:
        return jsonify(to_dict(employee)), 200
    return jsonify({"error": "Employee not found"}), 404

@app.route('/employee/<id>', methods=['PUT'])
@validate()
def update_employee(id, body: EmployeeModel):
    updated_employee = body.dict()
    result = employee_collection.update_one({'_id': ObjectId(id)}, {'$set': updated_employee})
    if result.matched_count:
        return jsonify({"message": "Employee updated"}), 200
    return jsonify({"error": "Employee not found"}), 404

@app.route('/employee/<id>', methods=['DELETE'])
def delete_employee(id):
    result = employee_collection.delete_one({'_id': ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "Employee deleted"}), 200
    return jsonify({"error": "Employee not found"}), 404

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
