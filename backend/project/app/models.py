# backend/project/app/models.py
"""
Modelos Pydantic para Historia Clínica Distribuida
Incluye: Usuario, Paciente (57 campos), Token
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import date, datetime
from enum import Enum


# ==================== ENUMS ====================

class RolEnum(str, Enum):
    """Roles disponibles en el sistema"""
    PACIENTE = "paciente"
    MEDICO = "medico"
    ADMISIONISTA = "admisionista"
    RESULTADOS = "resultados"
    ADMIN = "admin"


class TipoDocumentoEnum(str, Enum):
    """Tipos de documento de identidad"""
    CC = "CC"  # Cédula de Ciudadanía
    TI = "TI"  # Tarjeta de Identidad
    CE = "CE"  # Cédula de Extranjería
    PA = "PA"  # Pasaporte
    RC = "RC"  # Registro Civil


class SexoEnum(str, Enum):
    """Sexo biológico"""
    MASCULINO = "M"
    FEMENINO = "F"
    OTRO = "Otro"


class GrupoSanguineoEnum(str, Enum):
    """Grupos sanguíneos"""
    A_POSITIVO = "A+"
    A_NEGATIVO = "A-"
    B_POSITIVO = "B+"
    B_NEGATIVO = "B-"
    AB_POSITIVO = "AB+"
    AB_NEGATIVO = "AB-"
    O_POSITIVO = "O+"
    O_NEGATIVO = "O-"


class EstadoCivilEnum(str, Enum):
    """Estados civiles"""
    SOLTERO = "Soltero"
    CASADO = "Casado"
    UNION_LIBRE = "Union Libre"
    DIVORCIADO = "Divorciado"
    VIUDO = "Viudo"


class RegimenEnum(str, Enum):
    """Regímenes de afiliación"""
    CONTRIBUTIVO = "Contributivo"
    SUBSIDIADO = "Subsidiado"
    ESPECIAL = "Especial"
    NO_AFILIADO = "No afiliado"


class TipoAtencionEnum(str, Enum):
    """Tipos de atención médica"""
    URGENCIAS = "Urgencias"
    CONSULTA_EXTERNA = "Consulta Externa"
    HOSPITALIZACION = "Hospitalizacion"
    CIRUGIA = "Cirugia"
    PROCEDIMIENTO = "Procedimiento"


class EstadoEgresoEnum(str, Enum):
    """Estados de egreso"""
    MEJORADO = "Mejorado"
    IGUAL = "Igual"
    EMPEORADO = "Empeorado"
    FALLECIDO = "Fallecido"
    REMITIDO = "Remitido"


# ==================== MODELO USUARIO ====================

class Usuario(BaseModel):
    """Modelo completo de usuario"""
    id: int
    username: str
    rol: RolEnum
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    documento_vinculado: Optional[str] = None
    activo: bool = True
    fecha_creacion: datetime
    ultimo_acceso: Optional[datetime] = None

    class Config:
        from_attributes = True
        use_enum_values = True


class UsuarioCreate(BaseModel):
    """Schema para crear usuario"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    rol: RolEnum
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    documento_vinculado: Optional[str] = None


class UsuarioLogin(BaseModel):
    """Schema para login"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Respuesta de autenticación"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutos
    user: Usuario


# ==================== MODELO PACIENTE (57 CAMPOS) ====================

class PacienteBase(BaseModel):
    """Campos base del paciente (obligatorios en creación)"""
    # Identificación (9 campos obligatorios)
    tipo_documento: TipoDocumentoEnum
    numero_documento: str = Field(..., min_length=3, max_length=20)
    primer_apellido: str = Field(..., min_length=1, max_length=100)
    primer_nombre: str = Field(..., min_length=1, max_length=100)
    fecha_nacimiento: date
    sexo: SexoEnum


class PacienteCreate(PacienteBase):
    """Schema para crear paciente - incluye todos los campos opcionales"""
    # Identificación adicional (14 campos opcionales)
    segundo_apellido: Optional[str] = None
    segundo_nombre: Optional[str] = None
    genero: Optional[str] = None
    grupo_sanguineo: Optional[GrupoSanguineoEnum] = None
    factor_rh: Optional[str] = None
    estado_civil: Optional[EstadoCivilEnum] = None
    direccion_residencia: Optional[str] = None
    municipio: Optional[str] = None
    departamento: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    correo_electronico: Optional[EmailStr] = None
    ocupacion: Optional[str] = None
    entidad: Optional[str] = None
    regimen_afiliacion: Optional[RegimenEnum] = None
    tipo_usuario: Optional[str] = None

    # Atención (17 campos opcionales)
    tipo_atencion: Optional[TipoAtencionEnum] = None
    motivo_consulta: Optional[str] = None
    enfermedad_actual: Optional[str] = None
    antecedentes_personales: Optional[str] = None
    antecedentes_familiares: Optional[str] = None
    alergias_conocidas: Optional[str] = None
    habitos: Optional[str] = None
    medicamentos_actuales: Optional[str] = None

    # Signos vitales (9 campos opcionales)
    tension_arterial: Optional[str] = None
    frecuencia_cardiaca: Optional[int] = Field(None, ge=0, le=300)
    frecuencia_respiratoria: Optional[int] = Field(None, ge=0, le=100)
    temperatura: Optional[float] = Field(None, ge=30.0, le=45.0)
    saturacion_oxigeno: Optional[int] = Field(None, ge=0, le=100)
    peso: Optional[float] = Field(None, ge=0, le=500)
    talla: Optional[float] = Field(None, ge=0, le=300)

    # Diagnóstico (9 campos opcionales)
    examen_fisico_general: Optional[str] = None
    examen_fisico_sistemas: Optional[str] = None
    impresion_diagnostica: Optional[str] = None
    codigos_cie10: Optional[str] = None
    conducta_plan: Optional[str] = None
    recomendaciones: Optional[str] = None
    medicos_interconsultados: Optional[str] = None
    procedimientos_realizados: Optional[str] = None
    resultados_examenes: Optional[str] = None

    # Cierre (7 campos opcionales)
    diagnostico_definitivo: Optional[str] = None
    evolucion_medica: Optional[str] = None
    tratamiento_instaurado: Optional[str] = None
    formulacion_medica: Optional[str] = None
    educacion_paciente: Optional[str] = None
    referencia_contrarreferencia: Optional[str] = None
    estado_egreso: Optional[EstadoEgresoEnum] = None

    # Profesional (7 campos opcionales)
    nombre_profesional: Optional[str] = None
    tipo_profesional: Optional[str] = None
    registro_medico: Optional[str] = None
    cargo_servicio: Optional[str] = None
    firma_profesional: Optional[str] = None
    firma_paciente: Optional[str] = None
    responsable_registro: Optional[str] = None


class PacienteUpdate(BaseModel):
    """Schema para actualizar paciente - todos los campos opcionales"""
    # Permite actualizar cualquier campo excepto numero_documento
    tipo_documento: Optional[TipoDocumentoEnum] = None
    primer_apellido: Optional[str] = None
    segundo_apellido: Optional[str] = None
    primer_nombre: Optional[str] = None
    segundo_nombre: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[SexoEnum] = None
    genero: Optional[str] = None
    grupo_sanguineo: Optional[GrupoSanguineoEnum] = None
    factor_rh: Optional[str] = None
    estado_civil: Optional[EstadoCivilEnum] = None
    direccion_residencia: Optional[str] = None
    municipio: Optional[str] = None
    departamento: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    correo_electronico: Optional[EmailStr] = None
    ocupacion: Optional[str] = None
    entidad: Optional[str] = None
    regimen_afiliacion: Optional[RegimenEnum] = None
    tipo_usuario: Optional[str] = None
    tipo_atencion: Optional[TipoAtencionEnum] = None
    motivo_consulta: Optional[str] = None
    enfermedad_actual: Optional[str] = None
    antecedentes_personales: Optional[str] = None
    antecedentes_familiares: Optional[str] = None
    alergias_conocidas: Optional[str] = None
    habitos: Optional[str] = None
    medicamentos_actuales: Optional[str] = None
    tension_arterial: Optional[str] = None
    frecuencia_cardiaca: Optional[int] = None
    frecuencia_respiratoria: Optional[int] = None
    temperatura: Optional[float] = None
    saturacion_oxigeno: Optional[int] = None
    peso: Optional[float] = None
    talla: Optional[float] = None
    examen_fisico_general: Optional[str] = None
    examen_fisico_sistemas: Optional[str] = None
    impresion_diagnostica: Optional[str] = None
    codigos_cie10: Optional[str] = None
    conducta_plan: Optional[str] = None
    recomendaciones: Optional[str] = None
    medicos_interconsultados: Optional[str] = None
    procedimientos_realizados: Optional[str] = None
    resultados_examenes: Optional[str] = None
    diagnostico_definitivo: Optional[str] = None
    evolucion_medica: Optional[str] = None
    tratamiento_instaurado: Optional[str] = None
    formulacion_medica: Optional[str] = None
    educacion_paciente: Optional[str] = None
    referencia_contrarreferencia: Optional[str] = None
    estado_egreso: Optional[EstadoEgresoEnum] = None
    nombre_profesional: Optional[str] = None
    tipo_profesional: Optional[str] = None
    registro_medico: Optional[str] = None
    cargo_servicio: Optional[str] = None
    firma_profesional: Optional[str] = None
    firma_paciente: Optional[str] = None
    responsable_registro: Optional[str] = None


class PacienteResponse(PacienteBase):
    """Schema de respuesta completo con todos los campos"""
    id: int
    # Campos calculados (se calculan en la API, no en BD)
    edad: Optional[int] = None
    imc: Optional[float] = None

    @classmethod
    def from_db(cls, db_row: dict):
        """Crea instancia calculando edad e IMC"""
        from datetime import date

        # Calcular edad
        edad = None
        if db_row.get('fecha_nacimiento'):
            today = date.today()
            born = db_row['fecha_nacimiento']
            if isinstance(born, str):
                from datetime import datetime
                born = datetime.strptime(born, '%Y-%m-%d').date()
            edad = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        # Calcular IMC
        imc = None
        peso = db_row.get('peso')
        talla = db_row.get('talla')
        if peso and talla and talla > 0:
            imc = round(peso / ((talla/100) ** 2), 2)

        # Agregar campos calculados
        data = dict(db_row)
        data['edad'] = edad
        data['imc'] = imc

        return cls(**data)

    # Todos los campos opcionales del modelo completo
    segundo_apellido: Optional[str] = None
    segundo_nombre: Optional[str] = None
    genero: Optional[str] = None
    grupo_sanguineo: Optional[str] = None
    factor_rh: Optional[str] = None
    estado_civil: Optional[str] = None
    direccion_residencia: Optional[str] = None
    municipio: Optional[str] = None
    departamento: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    correo_electronico: Optional[str] = None
    ocupacion: Optional[str] = None
    entidad: Optional[str] = None
    regimen_afiliacion: Optional[str] = None
    tipo_usuario: Optional[str] = None
    fecha_atencion: Optional[datetime] = None
    tipo_atencion: Optional[str] = None
    motivo_consulta: Optional[str] = None
    enfermedad_actual: Optional[str] = None
    antecedentes_personales: Optional[str] = None
    antecedentes_familiares: Optional[str] = None
    alergias_conocidas: Optional[str] = None
    habitos: Optional[str] = None
    medicamentos_actuales: Optional[str] = None
    tension_arterial: Optional[str] = None
    frecuencia_cardiaca: Optional[int] = None
    frecuencia_respiratoria: Optional[int] = None
    temperatura: Optional[float] = None
    saturacion_oxigeno: Optional[int] = None
    peso: Optional[float] = None
    talla: Optional[float] = None
    examen_fisico_general: Optional[str] = None
    examen_fisico_sistemas: Optional[str] = None
    impresion_diagnostica: Optional[str] = None
    codigos_cie10: Optional[str] = None
    conducta_plan: Optional[str] = None
    recomendaciones: Optional[str] = None
    medicos_interconsultados: Optional[str] = None
    procedimientos_realizados: Optional[str] = None
    resultados_examenes: Optional[str] = None
    diagnostico_definitivo: Optional[str] = None
    evolucion_medica: Optional[str] = None
    tratamiento_instaurado: Optional[str] = None
    formulacion_medica: Optional[str] = None
    educacion_paciente: Optional[str] = None
    referencia_contrarreferencia: Optional[str] = None
    estado_egreso: Optional[str] = None
    nombre_profesional: Optional[str] = None
    tipo_profesional: Optional[str] = None
    registro_medico: Optional[str] = None
    cargo_servicio: Optional[str] = None
    firma_profesional: Optional[str] = None
    firma_paciente: Optional[str] = None
    fecha_cierre: Optional[datetime] = None
    responsable_registro: Optional[str] = None
    fecha_registro: Optional[datetime] = None
    ultima_actualizacion: Optional[datetime] = None
    activo: Optional[bool] = True

    class Config:
        from_attributes = True


class PacienteResumen(BaseModel):
    """Schema resumido para listados"""
    id: int
    numero_documento: str
    nombre_completo: str
    edad: Optional[int] = None
    sexo: str
    tipo_atencion: Optional[str] = None
    fecha_atencion: Optional[datetime] = None
    nombre_profesional: Optional[str] = None

    class Config:
        from_attributes = True
