# backend/project/app/main.py
"""
API Principal - Sistema de Historia Clínica Distribuida
VERSIÓN CORREGIDA - Fixes para listar, buscar y exportar PDF
"""

import os
from datetime import timedelta, datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from psycopg2.extras import RealDictCursor
import io

from app.database import get_db_connection
from app.models import (
    Usuario, UsuarioCreate, UsuarioLogin, TokenResponse,
    PacienteCreate, PacienteUpdate, PacienteResponse, PacienteResumen,
    RolEnum
)
from app.auth import (
    authenticate_user, create_access_token, get_token_expiration,
    get_current_active_user, require_role, require_admin,
    require_medico, require_admisionista, require_staff,
    user_can_access_patient
)

# ==================== CONFIGURACIÓN APP ====================

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="🏥 Sistema de Historia Clínica Distribuida",
    description="""
    ## Sistema Completo de Gestión de Historias Clínicas Electrónicas

    ### 🔐 Sistema de Roles

    El sistema cuenta con 5 roles diferenciados:

    - **👨‍⚕️ Médico**: Acceso completo a historias clínicas, puede crear y modificar
    - **📋 Admisionista**: Registra nuevos pacientes y actualiza datos básicos
    - **🧪 Resultados**: Ingresa resultados de exámenes y procedimientos
    - **🙍 Paciente**: Solo puede ver su propia historia clínica
    - **👑 Admin**: Acceso total al sistema, gestión de usuarios

    ### 🚀 Características

    - ✅ 57 campos de historia clínica completa
    - ✅ Autenticación con base de datos (bcrypt)
    - ✅ Control de acceso por roles
    - ✅ CRUD completo de pacientes
    - ✅ Exportación a PDF
    - ✅ Base de datos distribuida con Citus (32 shards)

    ### 📝 Usuarios de Prueba

    Todos con password: `password123`

    | Usuario | Rol | Descripción |
    |---------|-----|-------------|
    | `admin` | Admin | Administrador del sistema |
    | `dr_rodriguez` | Médico | Dr. Carlos Rodríguez |
    | `dra_martinez` | Médico | Dra. Ana Martínez |
    | `admisionista1` | Admisionista | María González |
    | `resultados1` | Resultados | Pedro López |
    | `paciente_juan` | Paciente | Juan Pérez (doc: 12345) |
    | `paciente_maria` | Paciente | María Gómez (doc: 67890) |

    ### 📚 Documentación

    - **Swagger UI**: `/docs` (esta página)
    - **ReDoc**: `/redoc`
    - **OpenAPI**: `/openapi.json`
    """,
    version="2.0.0",
    contact={
        "name": "Equipo de Desarrollo",
        "email": "support@historiaclinica.com"
    }
)

# ==================== CONFIGURACIÓN CORS ====================
origins = [
    "http://localhost",
    "http://localhost:5000",
    "http://127.0.0.1",
    "http://127.0.0.1:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ==================== ENDPOINTS PÚBLICOS ====================

@app.get(
    "/",
    tags=["Sistema"],
    summary="🏠 Información del sistema"
)
def root():
    """Información general de la API"""
    return {
        "nombre": "Sistema de Historia Clínica Distribuida",
        "version": "2.0.0",
        "estado": "operativo",
        "características": [
            "57 campos de historia clínica",
            "5 roles de usuario",
            "Autenticación con BD",
            "CRUD completo",
            "Exportación PDF",
            "Base de datos distribuida"
        ],
        "roles_disponibles": ["admin", "medico", "admisionista", "resultados", "paciente"],
        "documentacion": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }


@app.get(
    "/health",
    tags=["Sistema"],
    summary="🏥 Estado del sistema"
)
def health_check():
    """
    Verifica el estado de la API y la base de datos.
    Retorna información detallada de conectividad.
    """
    from datetime import datetime

    health_status = {
        "timestamp": datetime.now().isoformat(),
        "api": "operativa",
        "base_datos": {
            "estado": "desconocido",
            "detalles": None,
            "error": None
        },
        "configuracion": {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "database": os.getenv("POSTGRES_DB", "historiaclinica")
        }
    }

    # Intentar conexión a base de datos
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Test 1: Verificar conexión
        cur.execute("SELECT 1 as test")
        test_result = cur.fetchone()

        # Test 2: Verificar versión
        cur.execute("SELECT version()")
        version_result = cur.fetchone()

        # Test 3: Verificar tablas
        cur.execute("""
            SELECT COUNT(*) as count FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('usuarios', 'pacientes')
        """)
        tables_result = cur.fetchone()
        tables_count = tables_result['count']

        # Test 4: Verificar distribución Citus
        cur.execute("""
            SELECT COUNT(*) as count
            FROM citus_tables
            WHERE table_name::text = 'pacientes'
        """)
        citus_result = cur.fetchone()
        distributed = citus_result['count'] > 0

        # Test 5: Contar registros
        cur.execute("SELECT COUNT(*) as count FROM public.usuarios")
        users_count = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM public.pacientes")
        patients_count = cur.fetchone()['count']

        cur.close()

        health_status["base_datos"] = {
            "estado": "conectada",
            "version": version_result['version'][:50] + "...",
            "tablas_requeridas": tables_count == 2,
            "distribucion_citus": distributed,
            "datos": {
                "usuarios": users_count,
                "pacientes": patients_count
            },
            "detalles": "Todas las verificaciones pasaron exitosamente",
            "error": None
        }

        # Determinar estado general
        if tables_count == 2 and distributed:
            health_status["estado"] = "saludable"
            status_code = 200
        else:
            health_status["estado"] = "degradado"
            health_status["advertencias"] = []
            if tables_count != 2:
                health_status["advertencias"].append("Faltan tablas requeridas")
            if not distributed:
                health_status["advertencias"].append("Tabla pacientes no está distribuida")
            status_code = 200

    except RuntimeError as e:
        # Error de conexión detallado
        health_status["base_datos"] = {
            "estado": "error_conexion",
            "detalles": str(e),
            "error": "No se pudo establecer conexión con PostgreSQL"
        }
        health_status["estado"] = "no_saludable"
        status_code = 503

    except Exception as e:
        # Error inesperado
        health_status["base_datos"] = {
            "estado": "error",
            "detalles": str(e),
            "error": f"Error inesperado: {type(e).__name__}"
        }
        health_status["estado"] = "no_saludable"
        status_code = 503

    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

    # Retornar respuesta con código apropiado
    if status_code == 503:
        raise HTTPException(status_code=503, detail=health_status)

    return health_status

# ==================== AUTENTICACIÓN ====================

@app.post(
    "/token",
    response_model=TokenResponse,
    tags=["🔐 Autenticación"],
    summary="Iniciar sesión"
)
def login(credentials: UsuarioLogin):
    """
    Autenticación de usuarios contra la base de datos.

    **Usuarios de prueba** (password: `password123`):
    - `admin` - Administrador
    - `dr_rodriguez` - Médico
    - `dra_martinez` - Médico
    - `admisionista1` - Admisionista
    - `resultados1` - Resultados
    - `paciente_juan` - Paciente (doc: 12345)
    - `paciente_maria` - Paciente (doc: 67890)

    **Respuesta exitosa** incluye:
    - Token JWT válido por 30 minutos
    - Información del usuario autenticado
    """
    user = authenticate_user(credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas"
        )

    # Crear token con información del usuario
    access_token = create_access_token(
        data={
            "sub": user.username,
            "rol": user.rol,
            "user_id": user.id
        }
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=get_token_expiration(),
        user=user
    )


@app.get(
    "/me",
    response_model=Usuario,
    tags=["🔐 Autenticación"],
    summary="Información del usuario actual"
)
def get_me(current_user: Usuario = Depends(get_current_active_user)):
    """
    Obtiene información del usuario autenticado.
    Requiere token JWT válido.
    """
    return current_user


# ==================== GESTIÓN DE USUARIOS (Solo Admin) ====================

@app.post(
    "/usuarios",
    response_model=Usuario,
    tags=["👥 Usuarios"],
    summary="Crear usuario (Admin)",
    status_code=201
)
def crear_usuario(
    usuario: UsuarioCreate,
    current_user: Usuario = Depends(require_admin())
):
    """
    Crea un nuevo usuario en el sistema.

    **Requiere rol**: Admin

    La contraseña se hashea automáticamente con bcrypt.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar que el username no exista
        cur.execute("SELECT id FROM public.usuarios WHERE username = %s", (usuario.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El username ya existe")

        # Insertar usuario con contraseña hasheada
        cur.execute("""
            INSERT INTO public.usuarios
            (username, password_hash, rol, nombres, apellidos, documento_vinculado)
            VALUES (%s, crypt(%s, gen_salt('bf')), %s, %s, %s, %s)
            RETURNING id, username, rol, nombres, apellidos, documento_vinculado,
                      activo, fecha_creacion, ultimo_acceso
        """, (
            usuario.username,
            usuario.password,
            usuario.rol,
            usuario.nombres,
            usuario.apellidos,
            usuario.documento_vinculado
        ))

        row = cur.fetchone()
        conn.commit()
        cur.close()

        return Usuario(**dict(row))

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")
    finally:
        if conn:
            conn.close()


@app.get(
    "/usuarios",
    response_model=List[Usuario],
    tags=["👥 Usuarios"],
    summary="Listar usuarios (Admin)"
)
def listar_usuarios(
    current_user: Usuario = Depends(require_admin()),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Lista todos los usuarios del sistema.

    **Requiere rol**: Admin
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, username, rol, nombres, apellidos, documento_vinculado,
                   activo, fecha_creacion, ultimo_acceso
            FROM public.usuarios
            ORDER BY fecha_creacion DESC
            LIMIT %s
        """, (limit,))

        rows = cur.fetchall()
        cur.close()

        return [Usuario(**dict(row)) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar usuarios: {str(e)}")
    finally:
        if conn:
            conn.close()


# ==================== CRUD PACIENTES ====================

@app.post(
    "/pacientes",
    response_model=PacienteResponse,
    tags=["👨‍⚕️ Pacientes"],
    summary="Crear paciente (Admisionista/Médico/Admin)",
    status_code=201
)
def crear_paciente(
    paciente: PacienteCreate,
    current_user: Usuario = Depends(require_role(RolEnum.ADMISIONISTA, RolEnum.MEDICO, RolEnum.ADMIN))
):
    """
    Registra un nuevo paciente en el sistema.

    **Requiere rol**: Admisionista, Médico o Admin

    **Campos obligatorios**:
    - tipo_documento
    - numero_documento (único)
    - primer_apellido
    - primer_nombre
    - fecha_nacimiento
    - sexo

    **Campos opcionales**: 57 campos adicionales disponibles
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar que el documento no exista
        cur.execute(
            "SELECT id FROM public.pacientes WHERE numero_documento = %s",
            (paciente.numero_documento,)
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un paciente con documento {paciente.numero_documento}"
            )

        # Construir query dinámicamente
        fields = []
        values = []
        placeholders = []

        for field, value in paciente.dict(exclude_unset=True).items():
            if value is not None:
                fields.append(field)
                values.append(value)
                placeholders.append("%s")

        query = f"""
            INSERT INTO public.pacientes ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """

        cur.execute(query, values)
        row = cur.fetchone()
        conn.commit()
        cur.close()

        return PacienteResponse.from_db(dict(row))

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear paciente: {str(e)}")
    finally:
        if conn:
            conn.close()


@app.get(
    "/pacientes/{numero_documento}",
    response_model=PacienteResponse,
    tags=["👨‍⚕️ Pacientes"],
    summary="Obtener paciente por documento"
)
def obtener_paciente(
    numero_documento: str,
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Obtiene la historia clínica completa de un paciente.

    **Control de acceso**:
    - Staff (médico/admisionista/resultados/admin): acceso a cualquier paciente
    - Paciente: solo acceso a su propia historia
    """
    # Verificar permisos
    if not user_can_access_patient(current_user, numero_documento):
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para acceder a este paciente"
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM public.pacientes
            WHERE numero_documento = %s
            ORDER BY id DESC
            LIMIT 1
        """, (numero_documento,))

        row = cur.fetchone()
        cur.close()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Paciente con documento {numero_documento} no encontrado"
            )

        return PacienteResponse.from_db(dict(row))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener paciente: {str(e)}")
    finally:
        if conn:
            conn.close()


# ==================== FIX 1: LISTAR PACIENTES CORREGIDO ====================
@app.get(
    "/pacientes",
    response_model=List[PacienteResumen],
    tags=["👨‍⚕️ Pacientes"],
    summary="Listar pacientes (Staff)"
)
def listar_pacientes(
    current_user: Usuario = Depends(require_staff()),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Lista todos los pacientes del sistema (vista resumida).

    **Requiere rol**: Médico, Admisionista, Resultados o Admin

    **FIX**: Calcula edad usando DATE_PART en lugar de columna
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # ✅ FIX: Calcular edad con DATE_PART, no usar columna inexistente
        cur.execute("""
            SELECT
                id,
                numero_documento,
                CONCAT(primer_nombre, ' ', primer_apellido) as nombre_completo,
                DATE_PART('year', AGE(fecha_nacimiento))::INTEGER as edad,
                sexo,
                tipo_atencion,
                fecha_atencion,
                nombre_profesional
            FROM public.pacientes
            WHERE activo = TRUE
            ORDER BY fecha_registro DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))

        rows = cur.fetchall()
        cur.close()

        return [PacienteResumen(**dict(row)) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar pacientes: {str(e)}")
    finally:
        if conn:
            conn.close()


@app.put(
    "/pacientes/{numero_documento}",
    response_model=PacienteResponse,
    tags=["👨‍⚕️ Pacientes"],
    summary="Actualizar paciente (Médico/Admin)"
)
def actualizar_paciente(
    numero_documento: str,
    paciente: PacienteUpdate,
    current_user: Usuario = Depends(require_medico())
):
    """
    Actualiza los datos de un paciente existente.

    **Requiere rol**: Médico o Admin

    Solo se actualizan los campos proporcionados (PATCH semántico).
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar que el paciente exista
        cur.execute(
            "SELECT id FROM public.pacientes WHERE numero_documento = %s",
            (numero_documento,)
        )
        if not cur.fetchone():
            raise HTTPException(
                status_code=404,
                detail=f"Paciente con documento {numero_documento} no encontrado"
            )

        # Construir query de actualización dinámicamente
        updates = []
        values = []

        for field, value in paciente.dict(exclude_unset=True).items():
            if value is not None:
                updates.append(f"{field} = %s")
                values.append(value)

        if not updates:
            raise HTTPException(status_code=400, detail="No hay campos para actualizar")

        values.append(numero_documento)

        query = f"""
            UPDATE public.pacientes
            SET {', '.join(updates)}, ultima_actualizacion = NOW()
            WHERE numero_documento = %s
            RETURNING *
        """

        cur.execute(query, values)
        row = cur.fetchone()
        conn.commit()
        cur.close()

        return PacienteResponse.from_db(dict(row))

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar paciente: {str(e)}")
    finally:
        if conn:
            conn.close()


@app.delete(
    "/pacientes/{numero_documento}",
    tags=["👨‍⚕️ Pacientes"],
    summary="Eliminar paciente (Admin)",
    status_code=204
)
def eliminar_paciente(
    numero_documento: str,
    current_user: Usuario = Depends(require_admin())
):
    """
    Realiza un borrado lógico del paciente (marca como inactivo).

    **Requiere rol**: Admin

    **Nota**: No se eliminan datos, solo se marca como inactivo.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE public.pacientes
            SET activo = FALSE, ultima_actualizacion = NOW()
            WHERE numero_documento = %s
        """, (numero_documento,))

        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Paciente con documento {numero_documento} no encontrado"
            )

        conn.commit()
        cur.close()

        return None

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar paciente: {str(e)}")
    finally:
        if conn:
            conn.close()


# ==================== FIX 2: BÚSQUEDA CORREGIDA ====================
@app.get(
    "/pacientes/buscar/query",  # ✅ FIX: Cambiar ruta para evitar conflicto
    response_model=List[PacienteResumen],
    tags=["👨‍⚕️ Pacientes"],
    summary="Buscar pacientes (Staff)"
)
def buscar_pacientes(
    nombre: Optional[str] = Query(None, description="Nombre o apellido del paciente"),
    documento: Optional[str] = Query(None, description="Número de documento"),
    current_user: Usuario = Depends(require_staff()),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Búsqueda de pacientes por nombre o documento.

    **Requiere rol**: Médico, Admisionista, Resultados o Admin

    **FIX**: Endpoint correcto con parámetros query

    **Parámetros**:
    - `nombre`: Busca en primer_nombre y primer_apellido (ILIKE)
    - `documento`: Busca en numero_documento (ILIKE)

    **Uso**:
    ```
    GET /pacientes/buscar/query?nombre=Juan
    GET /pacientes/buscar/query?documento=12345
    GET /pacientes/buscar/query?nombre=Maria&documento=678
    ```
    """
    if not nombre and not documento:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos un parámetro de búsqueda (nombre o documento)"
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        conditions = ["activo = TRUE"]
        params = []

        if nombre:
            conditions.append("(primer_nombre ILIKE %s OR primer_apellido ILIKE %s)")
            params.extend([f"%{nombre}%", f"%{nombre}%"])

        if documento:
            conditions.append("numero_documento ILIKE %s")
            params.append(f"%{documento}%")

        params.append(limit)

        # ✅ FIX: Calcular edad correctamente
        query = f"""
            SELECT
                id,
                numero_documento,
                CONCAT(primer_nombre, ' ', primer_apellido) as nombre_completo,
                DATE_PART('year', AGE(fecha_nacimiento))::INTEGER as edad,
                sexo,
                tipo_atencion,
                fecha_atencion,
                nombre_profesional
            FROM public.pacientes
            WHERE {' AND '.join(conditions)}
            ORDER BY fecha_registro DESC
            LIMIT %s
        """

        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()

        return [PacienteResumen(**dict(row)) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")
    finally:
        if conn:
            conn.close()


# ==================== FIX 3: EXPORTACIÓN PDF CORREGIDA ====================
from app.pdf_generator import generar_pdf_paciente

@app.get(
    "/pacientes/{numero_documento}/pdf",
    tags=["📄 Exportación"],
    summary="Exportar historia clínica a PDF",
    response_class=StreamingResponse
)
def exportar_pdf(
    numero_documento: str,
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Genera un PDF con la historia clínica completa del paciente.

    **Control de acceso**:
    - Staff (médico/admisionista/resultados/admin): cualquier paciente
    - Paciente: solo su propia historia

    **Retorna**: Archivo PDF para descarga

    **FIX**: Sintaxis correcta de WeasyPrint
    """
    # Verificar permisos
    if not user_can_access_patient(current_user, numero_documento):
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para exportar este paciente"
        )

    conn = None
    try:
        # Obtener datos completos del paciente
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM public.pacientes
            WHERE numero_documento = %s
            ORDER BY id DESC
            LIMIT 1
        """, (numero_documento,))

        row = cur.fetchone()
        cur.close()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Paciente con documento {numero_documento} no encontrado"
            )

        # Convertir a diccionario y preparar datos
        paciente_dict = dict(row)

        # Convertir fechas a string para el template
        if paciente_dict.get('fecha_nacimiento'):
            paciente_dict['fecha_nacimiento'] = str(paciente_dict['fecha_nacimiento'])
        if paciente_dict.get('fecha_atencion'):
            paciente_dict['fecha_atencion'] = str(paciente_dict['fecha_atencion'])
        if paciente_dict.get('fecha_cierre'):
            paciente_dict['fecha_cierre'] = str(paciente_dict['fecha_cierre'])

        # Calcular edad e IMC para el PDF
        if paciente_dict.get('fecha_nacimiento'):
            from datetime import date
            born = paciente_dict['fecha_nacimiento']
            if isinstance(born, str):
                from datetime import datetime
                born = datetime.strptime(born, '%Y-%m-%d').date()
            today = date.today()
            paciente_dict['edad'] = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        peso = paciente_dict.get('peso')
        talla = paciente_dict.get('talla')
        if peso and talla and talla > 0:
            paciente_dict['imc'] = round(peso / ((talla/100) ** 2), 2)
        else:
            paciente_dict['imc'] = None

        # ✅ FIX: Generar PDF con sintaxis correcta
        pdf_content = generar_pdf_paciente(paciente_dict)

        # Crear stream de respuesta
        pdf_stream = io.BytesIO(pdf_content)
        pdf_stream.seek(0)

        # Nombre del archivo
        nombre_archivo = f"HC_{numero_documento}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{nombre_archivo}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar PDF: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


# ==================== ESTADÍSTICAS (Admin) ====================

@app.get(
    "/estadisticas",
    tags=["📊 Estadísticas"],
    summary="Estadísticas del sistema (Admin)"
)
def obtener_estadisticas(
    current_user: Usuario = Depends(require_admin())
):
    """
    Obtiene estadísticas generales del sistema.

    **Requiere rol**: Admin
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Total de pacientes
        cur.execute("SELECT COUNT(*) as total FROM public.pacientes WHERE activo = TRUE")
        total_pacientes = cur.fetchone()['total']

        # Total de usuarios
        cur.execute("SELECT COUNT(*) as total FROM public.usuarios WHERE activo = TRUE")
        total_usuarios = cur.fetchone()['total']

        # Distribución por tipo de atención
        cur.execute("""
            SELECT tipo_atencion, COUNT(*) as cantidad
            FROM public.pacientes
            WHERE activo = TRUE AND tipo_atencion IS NOT NULL
            GROUP BY tipo_atencion
            ORDER BY cantidad DESC
        """)
        tipos_atencion = cur.fetchall()

        # Distribución Citus
        cur.execute("SELECT * FROM citus_tables WHERE table_name::text = 'pacientes'")
        distribucion = cur.fetchone()

        cur.close()

        return {
            "total_pacientes": total_pacientes,
            "total_usuarios": total_usuarios,
            "tipos_atencion": [dict(row) for row in tipos_atencion],
            "distribucion_citus": {
                "shards": distribucion['shard_count'] if distribucion else 0,
                "columna_distribucion": distribucion['distribution_column'] if distribucion else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")
    finally:
        if conn:
            conn.close()
