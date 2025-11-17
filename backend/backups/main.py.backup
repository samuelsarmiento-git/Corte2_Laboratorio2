# project/app/main.py
from fastapi import FastAPI, HTTPException, Depends
from app.database import get_db_connection
from app.models import Paciente
from app.schemas import (
    AuthRequest,
    PacienteResponse,
    PacienteCreate,
    PacienteUpdate,
    FHIRSyncResponse
)
from app.auth import generar_jwt, validar_jwt
from app.fhir_client import get_fhir_client, FHIRClient
from psycopg2.extras import RealDictCursor
from typing import List, Optional

app = FastAPI(
    title="Middleware HC - Citus + FHIR",
    description="API para gestión de historias clínicas distribuidas con integración FHIR",
    version="2.0.0"
)

# ==================== ENDPOINTS PÚBLICOS ====================

@app.get("/", tags=["Sistema"])
def read_root():
    """Endpoint raíz para verificar que la API está funcionando"""
    return {
        "message": "Bienvenido a la API de Historia Clínica Distribuida con FHIR",
        "version": "2.0.0",
        "status": "operational",
        "features": ["Citus DB", "JWT Auth", "FHIR Integration"]
    }

@app.get("/health", tags=["Sistema"])
def health_check():
    """Verifica el estado de la API, base de datos y servidor FHIR"""
    try:
        # Verificar base de datos
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Verificar servidor FHIR
    fhir = get_fhir_client()
    fhir_status = fhir.test_connection()

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "fhir_server": fhir_status
    }

@app.post("/token", tags=["Autenticación"])
def login_for_token(auth: AuthRequest):
    """
    Genera un token JWT para autenticación.

    Credenciales de prueba:
    - username: admin
    - password: admin
    """
    if auth.username == "admin" and auth.password == "admin":
        token = generar_jwt({
            "sub": auth.username,
            "role": "admin"
        })
        return {
            "access_token": token,
            "token_type": "bearer"
        }

    raise HTTPException(
        status_code=401,
        detail="Credenciales inválidas"
    )

# ==================== ENDPOINTS PROTEGIDOS - PACIENTES ====================

@app.get("/paciente/{paciente_id}",
         response_model=PacienteResponse,
         tags=["Pacientes"])
def obtener_paciente(
    paciente_id: int,
    payload: dict = Depends(validar_jwt)
):
    """
    Obtiene los datos de un paciente por ID local.
    Requiere autenticación JWT.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, documento_id, nombre, apellido,
                   fecha_nacimiento, telefono, direccion, correo,
                   genero, tipo_sangre, fhir_id
            FROM public.pacientes
            WHERE id = %s
        """, (paciente_id,))

        row = cur.fetchone()
        cur.close()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Paciente con ID {paciente_id} no encontrado"
            )

        return PacienteResponse(**row)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar la base de datos: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.get("/pacientes",
         response_model=List[PacienteResponse],
         tags=["Pacientes"])
def listar_pacientes(
    payload: dict = Depends(validar_jwt),
    limit: int = 10
):
    """
    Lista todos los pacientes (con límite).
    Requiere autenticación JWT.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, documento_id, nombre, apellido,
                   fecha_nacimiento, telefono, direccion, correo,
                   genero, tipo_sangre, fhir_id
            FROM public.pacientes
            ORDER BY id
            LIMIT %s
        """, (limit,))

        rows = cur.fetchall()
        cur.close()

        return [PacienteResponse(**row) for row in rows]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar la base de datos: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.post("/pacientes",
          response_model=PacienteResponse,
          tags=["Pacientes"],
          status_code=201)
def crear_paciente(
    paciente: PacienteCreate,
    payload: dict = Depends(validar_jwt)
):
    """
    Crea un nuevo paciente en la base de datos local.
    Requiere autenticación JWT.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO public.pacientes
            (documento_id, nombre, apellido, fecha_nacimiento,
             telefono, direccion, correo, genero, tipo_sangre)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, documento_id, nombre, apellido,
                      fecha_nacimiento, telefono, direccion, correo,
                      genero, tipo_sangre, fhir_id
        """, (
            paciente.documento_id,
            paciente.nombre,
            paciente.apellido,
            paciente.fecha_nacimiento,
            paciente.telefono,
            paciente.direccion,
            paciente.correo,
            paciente.genero,
            paciente.tipo_sangre
        ))

        row = cur.fetchone()
        conn.commit()
        cur.close()

        return PacienteResponse(**row)

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear paciente: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

# ==================== ENDPOINTS FHIR ====================

@app.post("/pacientes/{paciente_id}/sync-to-fhir",
          response_model=FHIRSyncResponse,
          tags=["FHIR"])
def sincronizar_paciente_a_fhir(
    paciente_id: int,
    payload: dict = Depends(validar_jwt)
):
    """
    Sincroniza un paciente local al servidor FHIR.
    Crea o actualiza el recurso Patient en FHIR.
    """
    conn = None
    try:
        # Obtener paciente local
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, documento_id, nombre, apellido,
                   fecha_nacimiento, telefono, direccion, correo,
                   genero, tipo_sangre, fhir_id
            FROM public.pacientes
            WHERE id = %s
        """, (paciente_id,))

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Paciente {paciente_id} no encontrado"
            )

        paciente_data = dict(row)
        fhir = get_fhir_client()

        # Si ya tiene FHIR ID, actualizar; sino, crear
        if paciente_data.get("fhir_id"):
            result = fhir.update_patient(paciente_data["fhir_id"], paciente_data)
            fhir_id = paciente_data["fhir_id"]
            message = "Paciente actualizado en FHIR"
        else:
            result = fhir.create_patient(paciente_data)
            fhir_id = result["fhir_id"]

            # Actualizar FHIR ID en base de datos local
            cur.execute("""
                UPDATE public.pacientes
                SET fhir_id = %s
                WHERE id = %s
            """, (fhir_id, paciente_id))
            conn.commit()

            message = "Paciente creado en FHIR"

        cur.close()

        return FHIRSyncResponse(
            success=True,
            message=message,
            fhir_id=fhir_id,
            local_id=paciente_id
        )

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al sincronizar con FHIR: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.get("/fhir/patient/{fhir_id}",
         tags=["FHIR"])
def obtener_paciente_fhir(
    fhir_id: str,
    payload: dict = Depends(validar_jwt)
):
    """
    Obtiene un paciente directamente del servidor FHIR.
    Retorna el recurso FHIR Patient completo.
    """
    fhir = get_fhir_client()
    return fhir.get_patient(fhir_id)

@app.get("/fhir/search",
         tags=["FHIR"])
def buscar_pacientes_fhir(
    nombre: str = None,
    apellido: str = None,
    documento: str = None,
    payload: dict = Depends(validar_jwt)
):
    """
    Busca pacientes en el servidor FHIR.

    Parámetros:
    - nombre: Nombre del paciente
    - apellido: Apellido del paciente
    - documento: Número de documento (identifier)
    """
    fhir = get_fhir_client()

    search_params = {}
    if nombre:
        search_params["given"] = nombre
    if apellido:
        search_params["family"] = apellido
    if documento:
        search_params["identifier"] = documento

    if not search_params:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos un parámetro de búsqueda"
        )

    patients = fhir.search_patients(**search_params)

    return {
        "total": len(patients),
        "patients": patients
    }

@app.post("/fhir/import/{fhir_id}",
          response_model=PacienteResponse,
          tags=["FHIR"])
def importar_desde_fhir(
    fhir_id: str,
    payload: dict = Depends(validar_jwt)
):
    """
    Importa un paciente desde FHIR a la base de datos local.
    """
    conn = None
    try:
        fhir = get_fhir_client()

        # Obtener paciente de FHIR
        fhir_patient = fhir.get_patient(fhir_id)

        # Convertir a formato local
        paciente_data = fhir.fhir_to_paciente(fhir_patient)
        paciente_data["fhir_id"] = fhir_id

        # Verificar si ya existe
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id FROM public.pacientes
            WHERE fhir_id = %s OR documento_id = %s
        """, (fhir_id, paciente_data.get("documento_id")))

        existing = cur.fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Paciente ya existe en la base de datos local"
            )

        # Insertar paciente
        cur.execute("""
            INSERT INTO public.pacientes
            (documento_id, nombre, apellido, fecha_nacimiento,
             telefono, direccion, correo, genero, fhir_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, documento_id, nombre, apellido,
                      fecha_nacimiento, telefono, direccion, correo,
                      genero, tipo_sangre, fhir_id
        """, (
            paciente_data.get("documento_id"),
            paciente_data.get("nombre"),
            paciente_data.get("apellido"),
            paciente_data.get("fecha_nacimiento"),
            paciente_data.get("telefono"),
            paciente_data.get("direccion"),
            paciente_data.get("correo"),
            paciente_data.get("genero"),
            fhir_id
        ))

        row = cur.fetchone()
        conn.commit()
        cur.close()

        return PacienteResponse(**row)

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al importar desde FHIR: {str(e)}"
        )
    finally:
        if conn:
            conn.close()
