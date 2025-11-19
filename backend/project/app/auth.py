# backend/project/app/auth.py
"""
Sistema de autenticación completo con JWT y roles
Incluye: Login con BD, validación de tokens, control de acceso por roles
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

from app.database import get_db_connection
from app.models import RolEnum, Usuario

load_dotenv(override=False)

# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY", "cambia_esto_en_produccion")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


# ==================== HTTP BEARER PERSONALIZADO ====================

class HTTPBearerFixed(HTTPBearer):
    """
    HTTPBearer personalizado que retorna 401 en lugar de 403
    cuando falta el header Authorization
    """

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        authorization = request.headers.get("Authorization")

        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Falta header Authorization",
                headers={"WWW-Authenticate": "Bearer"}
            )

        scheme, _, credentials = authorization.partition(" ")

        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Esquema de autenticación inválido. Use 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Token faltante",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


# Instancia global del manejador de seguridad
security = HTTPBearerFixed()


# ==================== AUTENTICACIÓN CON BASE DE DATOS ====================

def authenticate_user(username: str, password: str) -> Optional[Usuario]:
    """
    Autentica un usuario contra la base de datos.

    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano

    Returns:
        Usuario si las credenciales son válidas, None si no
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Buscar usuario y verificar contraseña usando crypt
        cur.execute("""
            SELECT
                id, username, rol, nombres, apellidos,
                documento_vinculado, activo, fecha_creacion, ultimo_acceso
            FROM public.usuarios
            WHERE username = %s
            AND password_hash = crypt(%s, password_hash)
            AND activo = TRUE
        """, (username, password))

        row = cur.fetchone()

        if not row:
            return None

        # Actualizar último acceso
        cur.execute("""
            UPDATE public.usuarios
            SET ultimo_acceso = NOW()
            WHERE id = %s
        """, (row['id'],))
        conn.commit()

        cur.close()

        # Convertir a modelo Usuario
        return Usuario(**dict(row))

    except Exception as e:
        print(f"Error en autenticación: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_by_username(username: str) -> Optional[Usuario]:
    """
    Obtiene un usuario por su username

    Args:
        username: Nombre de usuario

    Returns:
        Usuario si existe, None si no
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                id, username, rol, nombres, apellidos,
                documento_vinculado, activo, fecha_creacion, ultimo_acceso
            FROM public.usuarios
            WHERE username = %s AND activo = TRUE
        """, (username,))

        row = cur.fetchone()
        cur.close()

        if not row:
            return None

        return Usuario(**dict(row))

    except Exception as e:
        print(f"Error obteniendo usuario: {e}")
        return None
    finally:
        if conn:
            conn.close()


# ==================== GESTIÓN DE TOKENS JWT ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Genera un token JWT

    Args:
        data: Datos a incluir en el token (sub, rol, etc)
        expires_delta: Tiempo de expiración personalizado

    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT

    Args:
        token: Token JWT a validar

    Returns:
        Payload del token decodificado

    Raises:
        HTTPException: Si el token es inválido o expirado
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expirado. Por favor, inicie sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token inválido: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


# ==================== DEPENDENCIES PARA ENDPOINTS ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Usuario:
    """
    Dependency que obtiene el usuario actual desde el token JWT.
    Valida el token y retorna el usuario autenticado.

    Args:
        credentials: Credenciales HTTP Bearer del header

    Returns:
        Usuario autenticado

    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    token = credentials.credentials
    payload = decode_token(token)

    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=401,
            detail="Token inválido: falta información del usuario"
        )

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado o inactivo"
        )

    return user


async def get_current_active_user(
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    """
    Dependency que verifica que el usuario actual esté activo
    """
    if not current_user.activo:
        raise HTTPException(
            status_code=403,
            detail="Usuario inactivo"
        )
    return current_user


# ==================== CONTROL DE ACCESO POR ROLES ====================

class RoleChecker:
    """
    Clase para verificar roles de usuario.
    Uso: Depends(RoleChecker(["medico", "admin"]))
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
        """
        Verifica que el usuario tenga uno de los roles permitidos

        Args:
            current_user: Usuario actual autenticado

        Returns:
            Usuario si tiene permiso

        Raises:
            HTTPException 403: Si el usuario no tiene permiso
        """
        if current_user.rol not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Permiso denegado. Se requiere uno de estos roles: {', '.join(self.allowed_roles)}"
            )
        return current_user


# ==================== FUNCIONES DE CONVENIENCIA ====================

def require_role(*roles: str):
    """
    Función helper para requerir roles específicos.

    Uso en endpoints:
        @app.get("/medicos-only")
        def endpoint(user: Usuario = Depends(require_role("medico", "admin"))):
            pass

    Args:
        *roles: Roles permitidos

    Returns:
        Dependency de FastAPI
    """
    return RoleChecker(list(roles))


# Atajos para roles comunes
require_admin = lambda: require_role(RolEnum.ADMIN)
require_medico = lambda: require_role(RolEnum.MEDICO, RolEnum.ADMIN)
require_admisionista = lambda: require_role(RolEnum.ADMISIONISTA, RolEnum.ADMIN)
require_resultados = lambda: require_role(RolEnum.RESULTADOS, RolEnum.ADMIN)
require_staff = lambda: require_role(
    RolEnum.MEDICO,
    RolEnum.ADMISIONISTA,
    RolEnum.RESULTADOS,
    RolEnum.ADMIN
)


# ==================== VERIFICACIÓN DE PERMISOS ====================

def user_can_access_patient(user: Usuario, numero_documento: str) -> bool:
    """
    Verifica si un usuario puede acceder a un paciente específico.

    Reglas:
    - Admin: acceso total
    - Médico/Admisionista/Resultados: acceso a todos los pacientes
    - Paciente: solo acceso a su propia historia

    Args:
        user: Usuario que intenta acceder
        numero_documento: Documento del paciente

    Returns:
        True si tiene permiso, False si no
    """
    # Staff tiene acceso total
    if user.rol in [RolEnum.ADMIN, RolEnum.MEDICO, RolEnum.ADMISIONISTA, RolEnum.RESULTADOS]:
        return True

    # Paciente solo accede a su propia historia
    if user.rol == RolEnum.PACIENTE:
        return user.documento_vinculado == numero_documento

    return False


def verify_patient_access(
    numero_documento: str,
    current_user: Usuario = Depends(get_current_active_user)
) -> Usuario:
    """
    Dependency para verificar acceso a un paciente específico.

    Uso:
        @app.get("/paciente/{numero_documento}")
        def get_patient(
            numero_documento: str,
            user: Usuario = Depends(verify_patient_access)
        ):
            pass

    Args:
        numero_documento: Documento del paciente
        current_user: Usuario actual

    Returns:
        Usuario si tiene permiso

    Raises:
        HTTPException 403: Si no tiene permiso
    """
    if not user_can_access_patient(current_user, numero_documento):
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para acceder a este paciente"
        )
    return current_user


# ==================== UTILIDADES ====================

def get_token_expiration() -> int:
    """Retorna el tiempo de expiración del token en segundos"""
    return ACCESS_TOKEN_EXPIRE_MINUTES * 60
