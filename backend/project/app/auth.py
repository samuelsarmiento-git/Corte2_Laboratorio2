# project/app/auth.py - VERSIÓN CORREGIDA
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from dotenv import load_dotenv

load_dotenv(override=False)

SECRET_KEY = os.getenv("SECRET_KEY", "cambia_esto_en_produccion")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


class HTTPBearerCustom(HTTPBearer):
    """
    HTTPBearer personalizado que retorna 401 en lugar de 403
    cuando no se proporciona el header de autorización.

    CRÍTICO: __call__ debe ser una función SÍNCRONA, no async.
    """
    def __call__(self, request) -> Optional[HTTPAuthorizationCredentials]:
        """
        Método síncrono (sin async) para manejar la autenticación.

        IMPORTANTE: No usar 'async def' aquí, FastAPI espera una función síncrona.
        """
        try:
            # Llamar al método padre de forma síncrona
            from fastapi import Request
            from starlette.requests import Request as StarletteRequest

            # Obtener el header Authorization
            authorization = request.headers.get("Authorization")

            if not authorization:
                raise HTTPException(
                    status_code=401,
                    detail="Falta header Authorization",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            # Verificar formato "Bearer <token>"
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

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Error en autenticación: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )


# Instancia del manejador personalizado
security = HTTPBearerCustom()


def generar_jwt(data: dict) -> str:
    """
    Genera un token JWT con los datos proporcionados.

    Args:
        data: Diccionario con la información a incluir en el token

    Returns:
        str: Token JWT codificado
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def validar_jwt_token(token: str) -> dict:
    """
    Valida un token JWT y retorna el payload.

    Args:
        token: Token JWT a validar

    Returns:
        dict: Payload del token

    Raises:
        HTTPException: Si el token es inválido o ha expirado
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    Dependency para obtener el usuario actual desde el token JWT.

    Args:
        credentials: Credenciales HTTP Bearer extraídas del header

    Returns:
        dict: Payload del token validado

    Raises:
        HTTPException: Si el token es inválido
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Falta header Authorization",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    return validar_jwt_token(token)
