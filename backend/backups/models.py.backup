# project/app/models.py
import os
# project/app/models.py
from pydantic import BaseModel
from typing import Optional

class Paciente(BaseModel):
    id: int
    documento_id: str
    nombre: str
    apellido: str
    fecha_nacimiento: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    correo: Optional[str] = None
    genero: Optional[str] = None
    tipo_sangre: Optional[str] = None
    fhir_id: Optional[str] = None  # Nuevo: ID en servidor FHIR
