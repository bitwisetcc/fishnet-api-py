from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator


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

    @field_validator("price")
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("The price must be greater than zero.")
        return v


class CustomerModel(BaseModel):
    is_company: bool
    name: str
    email: EmailStr
    cellphone: str = Field(..., regex=r"^\d{11}$")
    birth_date: date
    rg: int
    cpf: str = Field(..., regex=r"^\d{11}$")
    cnpj: str = Field(None, regex=r"^\d{14}$")
    serial_cc: str = Field(..., min_length=16, max_length=16)
    expiration_cc: str = Field(..., min_length=5, max_length=5)
    backserial_cc: str = Field(..., min_length=3, max_length=3)

    @field_validator("expiration_cc")
    def validate_expiration_format(cls, v):
        if not (v[:2].isdigit() and v[3:].isdigit() and v[2] == "/"):
            raise ValueError("Expiration date must be in MM/YY format")
        return v


class EmployeeModel(BaseModel):
    name: str
    email: EmailStr
    cellphone: str
    birth_date: date
    rg: str
    cpf: str = Field(..., regex=r"^\d{11}$")
    status: str
    job_sector: str
    job_title: str


# class User(BaseModel):
#     role: str
#     name: str
#     email: EmailStr
#     cellphone: str = Field(..., regex=r"^\d{11}$")
#     birth_date: date
#     rg: str  # TODO: validate
#     cpf: str = Field(..., regex=r"^\d{11}$")  # TODO: validate
#     cnpj: str = Field(None, regex=r"^\d{14}$")  # TODO: validate
#     serial_cc: str = Field(..., min_length=16, max_length=16)
#     expiration_cc: str = Field(..., min_length=5, max_length=5)
#     backserial_cc: str = Field(..., min_length=3, max_length=3)

#     status: str
#     job_sector: str
#     job_title: str

#     @field_validator("role")
#     def validate_expiration_format(cls, v):
#         if not v in ["cpf", "cnpj", "staff"]:
#             raise ValueError("Invalid role.")

#         return v
