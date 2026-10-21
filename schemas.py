from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


Categoria = Literal["cena", "alojamiento", "actividades", "transporte", "otros"]


class UsuarioRegistro(BaseModel):
    """Datos que envía una persona al registrarse."""
    nombre: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=150)
    password: str = Field(min_length=6, max_length=72)


class UsuarioLogin(BaseModel):
    """Datos que envía una persona al iniciar sesión."""
    email: str
    password: str


class UsuarioRespuesta(BaseModel):
    """Lo que devolvemos de un usuario. Nunca incluye la contraseña."""
    id: int
    nombre: str
    email: str


class Token(BaseModel):
    """La 'pulsera' que recibe el usuario al iniciar sesión."""
    access_token: str
    token_type: str



class GastoNuevo(BaseModel):
    """Un gasto del desglose (por ejemplo, la cena del sábado)."""
    concepto: str = Field(min_length=2, max_length=150)
    categoria: Categoria = "otros"
    importe: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class GrupoNuevo(BaseModel):
    """Datos para crear un grupo: título, descripción y al menos un gasto."""
    titulo: str = Field(min_length=2, max_length=150)
    descripcion: str = Field(default="", max_length=2000)
    gastos: list[GastoNuevo] = Field(min_length=1)


class GastoRespuesta(BaseModel):
    id: int
    concepto: str
    categoria: str
    importe: float


class MiembroRespuesta(BaseModel):
    usuario_id: int
    nombre: str
    email: str
    es_creador: bool
    porcentaje: float   
    debe: float         
    pagado: float       
    pendiente: float   


class PagoRespuesta(BaseModel):
    id: int
    usuario_id: int
    nombre: str
    importe: float
    fecha: date
    nota: str | None = None


class GrupoResumen(BaseModel):
    """Una fila de la lista 'mis grupos'."""
    id: int
    titulo: str
    descripcion: str
    total: float
    rol: str            


class GrupoDetalle(BaseModel):
    """Todo lo que se ve al abrir un grupo."""
    id: int
    titulo: str
    descripcion: str
    creador_id: int
    soy_creador: bool
    total: float
    porcentaje_asignado: float
    reparto_completo: bool   
    total_pagado: float
    total_pendiente: float
    gastos: list[GastoRespuesta]
    miembros: list[MiembroRespuesta]
    pagos: list[PagoRespuesta]