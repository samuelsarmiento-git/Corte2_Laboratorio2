# backend/project/app/database.py
"""
Módulo de conexión a PostgreSQL/Citus
VERSIÓN CORREGIDA - Con mejor manejo de errores
"""

import os
from psycopg2 import connect, OperationalError
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(override=False)

# Configuración de PostgreSQL/Citus
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_DB = os.getenv("POSTGRES_DB", "historiaclinica")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

def get_db_connection():
    """
    Establece conexión con la base de datos Citus/PostgreSQL.
    Retorna una conexión con RealDictCursor por defecto.

    Raises:
        RuntimeError: Si no se puede conectar a la base de datos
    """
    try:
        conn = connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            cursor_factory=RealDictCursor,
            connect_timeout=5  # Timeout de 5 segundos
        )
        return conn
    except OperationalError as e:
        # Proporcionar información detallada del error
        error_msg = (
            f"Error conectando a PostgreSQL:\n"
            f"  Host: {POSTGRES_HOST}\n"
            f"  Port: {POSTGRES_PORT}\n"
            f"  Database: {POSTGRES_DB}\n"
            f"  User: {POSTGRES_USER}\n"
            f"  Error: {str(e)}"
        )
        raise RuntimeError(error_msg)
    except Exception as e:
        raise RuntimeError(f"Error inesperado al conectar: {str(e)}")

def test_connection():
    """
    Función de utilidad para probar la conexión.
    Retorna True si exitosa, False si falla.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()
        cur.close()
        conn.close()
        print(f"✅ Conexión exitosa")
        print(f"   PostgreSQL Version: {version['version'][:50]}...")
        return True
    except Exception as e:
        print(f"❌ Error de conexión:")
        print(f"   {str(e)}")
        return False

def get_connection_info():
    """
    Retorna información de configuración de conexión (para debugging)
    """
    return {
        "host": POSTGRES_HOST,
        "port": POSTGRES_PORT,
        "database": POSTGRES_DB,
        "user": POSTGRES_USER,
        "password_set": bool(POSTGRES_PASSWORD)
    }

if __name__ == "__main__":
    # Permite probar la conexión ejecutando: python -m app.database
    print("🔍 Probando conexión a PostgreSQL/Citus...")
    print(f"📊 Configuración: {get_connection_info()}")
    test_connection()
