# project/app/schemas.py
from pydantic import BaseModel
from typing import Optional

class AuthRequest(BaseModel):
    username: str
    password: str

class PacienteResponse(BaseModel):
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
    fhir_id: Optional[str] = None

class PacienteCreate(BaseModel):
    documento_id: str
    nombre: str
    apellido: str
    fecha_nacimiento: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    correo: Optional[str] = None
    genero: Optional[str] = None
    tipo_sangre: Optional[str] = None

class FHIRSyncResponse(BaseModel):
    success: bool
    message: str
    fhir_id: Optional[str] = None
    local_id: Optional[int] = None
