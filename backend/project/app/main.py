# project/app/main.py - VERSIÓN FINAL SEMANA 1
import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import get_db_connection
from app.models import Paciente
from app.schemas import AuthRequest, PacienteResponse
from app.auth import generar_jwt
from psycopg2.extras import RealDictCursor
import jwt
from dotenv import load_dotenv

load_dotenv(override=False)

# Configurar esquema de seguridad para Swagger
security = HTTPBearer(
    scheme_name="JWT Bearer Token",
    description="Ingresa el token JWT en formato: Bearer <token>"
)

app = FastAPI(
    title="🏥 Historia Clínica Distribuida - API",
    description="""
    ## Sistema de Gestión de Historias Clínicas

    API REST para gestión de historias clínicas con base de datos distribuida (Citus).

    ### 🔐 Autenticación

    Esta API utiliza tokens JWT para autenticación. Para usar los endpoints protegidos:

    1. **Obtener Token:** Usa el endpoint `POST /token` con credenciales válidas
    2. **Configurar Autorización:**
       - Click en el botón **🔓 Authorize** (arriba a la derecha)
       - Ingresa: `Bearer [tu_token]` (incluye la palabra "Bearer" y un espacio)
       - Click **Authorize**
    3. **Usar Endpoints:** Ahora puedes acceder a todos los endpoints protegidos

    ### 📝 Credenciales de Prueba

    - **Username:** `admin`
    - **Password:** `admin`

    ### 🚀 Datos de Prueba

    El sistema incluye 3 pacientes de prueba:
    - ID 1: Juan Pérez (documento: 12345)
    - ID 2: María Gómez (documento: 67890)
    - ID 3: Pedro López (documento: 11111)

    ### 🏗️ Arquitectura

    - **Backend:** FastAPI + Python 3.10
    - **Base de Datos:** PostgreSQL con Citus (distribuida)
    - **Autenticación:** JWT (JSON Web Tokens)
    - **Despliegue:** Kubernetes (Minikube)

    ### 📚 Documentación

    - **Swagger UI:** `/docs` (esta página)
    - **ReDoc:** `/redoc`
    - **OpenAPI Schema:** `/openapi.json`
    """,
    version="1.0.0",
    contact={
        "name": "Equipo de Desarrollo",
        "email": "support@historiaclinica.com"
    },
    license_info={
        "name": "Proyecto Académico"
    }
)

# ==================== ENDPOINTS PÚBLICOS ====================

@app.get(
    "/",
    tags=["Sistema"],
    summary="🏠 Página de inicio",
    response_description="Información general de la API"
)
def read_root():
    """
    ## Endpoint Raíz

    Proporciona información general sobre la API y sus endpoints disponibles.

    **No requiere autenticación** ✅

    ### Respuesta
    Retorna un objeto JSON con:
    - Mensaje de bienvenida
    - Versión de la API
    - Estado operacional
    - Enlaces a documentación
    - Lista de endpoints principales
    """
    return {
        "message": "Bienvenido a la API de Historia Clínica Distribuida",
        "version": "1.0.0",
        "status": "operational",
        "documentation": {
            "swagger": "http://localhost:8000/docs",
            "redoc": "http://localhost:8000/redoc",
            "openapi": "http://localhost:8000/openapi.json"
        },
        "endpoints": {
            "authentication": "/token",
            "health_check": "/health",
            "get_patient": "/paciente/{id}",
            "list_patients": "/pacientes"
        },
        "database": {
            "type": "PostgreSQL + Citus",
            "distribution": "documento_id",
            "shards": 32
        }
    }

@app.get(
    "/health",
    tags=["Sistema"],
    summary="🏥 Verificación de salud",
    response_description="Estado del sistema y conexión a BD"
)
def health_check():
    """
    ## Health Check

    Verifica el estado de la API y la conexión con la base de datos.

    **No requiere autenticación** ✅

    ### Verificaciones
    - ✅ API operativa
    - ✅ Conexión a base de datos

    ### Códigos de Respuesta
    - **200:** Sistema saludable
    - **503:** Error de conexión a BD

    ### Ejemplo de Respuesta Exitosa
    ```json
    {
      "status": "healthy",
      "database": "connected"
    }
    ```
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2025-11-05T12:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )

@app.post(
    "/token",
    tags=["Autenticación"],
    summary="🔑 Obtener Token JWT",
    response_description="Token de acceso generado"
)
def login_for_token(auth: AuthRequest):
    """
    ## Generar Token de Autenticación

    Genera un token JWT válido por 30 minutos.

    **No requiere autenticación** ✅

    ### Credenciales de Prueba
    ```json
    {
      "username": "admin",
      "password": "admin"
    }
    ```

    ### Ejemplo de Request
    ```bash
    curl -X POST http://localhost:8000/token \\
      -H "Content-Type: application/json" \\
      -d '{"username":"admin","password":"admin"}'
    ```

    ### Respuesta Exitosa
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    }
    ```

    ### Cómo Usar el Token

    1. **Copiar** el `access_token` de la respuesta
    2. **Click** en el botón 🔓 **Authorize** (arriba)
    3. **Ingresar:** `Bearer [access_token]`
    4. **Click** en **Authorize** y luego **Close**
    5. ¡Listo! Ahora puedes usar todos los endpoints protegidos

    ### Códigos de Respuesta
    - **200:** Token generado exitosamente
    - **401:** Credenciales inválidas

    ### Notas
    - El token expira en 30 minutos
    - En Semana 2 se validará contra la base de datos
    """
    if auth.username == "admin" and auth.password == "admin":
        token = generar_jwt({
            "sub": auth.username,
            "role": "admin"
        })
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 1800  # 30 minutos en segundos
        }

    raise HTTPException(
        status_code=401,
        detail="Credenciales inválidas. Usa username: 'admin', password: 'admin'"
    )

# ==================== ENDPOINTS PROTEGIDOS ====================

@app.get(
    "/paciente/{paciente_id}",
    response_model=PacienteResponse,
    tags=["Pacientes"],
    summary="👤 Obtener Paciente por ID",
    response_description="Datos completos del paciente"
)
def obtener_paciente(
    paciente_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    ## Obtener Información de un Paciente

    Retorna todos los datos de un paciente específico.

    **Requiere autenticación JWT** 🔒

    ### Parámetros
    - **paciente_id** (path): ID del paciente (1, 2 o 3 para datos de prueba)

    ### Pacientes de Prueba
    - `1`: Juan Pérez (documento: 12345)
    - `2`: María Gómez (documento: 67890)
    - `3`: Pedro López (documento: 11111)

    ### Ejemplo de Request
    ```bash
    curl http://localhost:8000/paciente/1 \\
      -H "Authorization: Bearer <tu_token>"
    ```

    ### Respuesta Exitosa
    ```json
    {
      "id": 1,
      "documento_id": "12345",
      "nombre": "Juan",
      "apellido": "Pérez",
      "fecha_nacimiento": "1995-04-12",
      "telefono": "3001234567",
      "direccion": "Calle 123 #45-67",
      "correo": "juanp@example.com"
    }
    ```

    ### Códigos de Respuesta
    - **200:** Paciente encontrado
    - **401:** Token inválido o expirado
    - **404:** Paciente no encontrado
    - **500:** Error de base de datos
    """
    # Validar token
    token = credentials.credentials
    SECRET_KEY = os.getenv("SECRET_KEY", "20240902734")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, documento_id, nombre, apellido,
                   fecha_nacimiento, telefono, direccion, correo
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

        return PacienteResponse(
            id=row['id'],
            documento_id=row['documento_id'],
            nombre=row['nombre'],
            apellido=row['apellido'],
            fecha_nacimiento=str(row['fecha_nacimiento']) if row['fecha_nacimiento'] else None,
            telefono=row.get('telefono'),
            direccion=row.get('direccion'),
            correo=row.get('correo')
        )

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

@app.get(
    "/pacientes",
    response_model=list[PacienteResponse],
    tags=["Pacientes"],
    summary="📋 Listar Pacientes",
    response_description="Lista de pacientes"
)
def listar_pacientes(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: int = 10
):
    """
    ## Listar Todos los Pacientes

    Retorna una lista paginada de pacientes.

    **Requiere autenticación JWT** 🔒

    ### Parámetros Query
    - **limit** (opcional): Número máximo de resultados (default: 10)

    ### Ejemplo de Request
    ```bash
    # Listar primeros 10 pacientes
    curl http://localhost:8000/pacientes \\
      -H "Authorization: Bearer <tu_token>"

    # Listar primeros 5 pacientes
    curl http://localhost:8000/pacientes?limit=5 \\
      -H "Authorization: Bearer <tu_token>"
    ```

    ### Respuesta Exitosa
    ```json
    [
      {
        "id": 1,
        "documento_id": "12345",
        "nombre": "Juan",
        "apellido": "Pérez",
        "fecha_nacimiento": "1995-04-12",
        "telefono": "3001234567",
        "direccion": "Calle 123 #45-67",
        "correo": "juanp@example.com"
      },
      {
        "id": 2,
        "documento_id": "67890",
        "nombre": "María",
        "apellido": "Gómez",
        ...
      }
    ]
    ```

    ### Códigos de Respuesta
    - **200:** Lista de pacientes retornada
    - **401:** Token inválido o expirado
    - **500:** Error de base de datos

    ### Notas
    - Los resultados se ordenan por ID ascendente
    - En Semana 2 se añadirá paginación completa
    """
    # Validar token
    token = credentials.credentials
    SECRET_KEY = os.getenv("SECRET_KEY", "20240902734")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, documento_id, nombre, apellido,
                   fecha_nacimiento, telefono, direccion, correo
            FROM public.pacientes
            ORDER BY id
            LIMIT %s
        """, (limit,))

        rows = cur.fetchall()
        cur.close()

        return [
            PacienteResponse(
                id=row['id'],
                documento_id=row['documento_id'],
                nombre=row['nombre'],
                apellido=row['apellido'],
                fecha_nacimiento=str(row['fecha_nacimiento']) if row['fecha_nacimiento'] else None,
                telefono=row.get('telefono'),
                direccion=row.get('direccion'),
                correo=row.get('correo')
            )
            for row in rows
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar la base de datos: {str(e)}"
        )
    finally:
        if conn:
            conn.close()
