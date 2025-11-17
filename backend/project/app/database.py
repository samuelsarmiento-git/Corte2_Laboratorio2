# project/app/database.py
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
    """
    try:
        conn = connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except OperationalError as e:
        raise RuntimeError(f"Error conectando a la BD en {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}: {e}")

def test_connection():
    """Función de utilidad para probar la conexión"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()
        cur.close()
        conn.close()
        print(f"✅ Conexión exitosa: {version}")
        return True
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    # Permite probar la conexión ejecutando: python -m app.database
    test_connection()
