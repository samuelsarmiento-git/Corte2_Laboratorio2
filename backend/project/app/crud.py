# project/app/crud.py
import os
from app.database import get_db_connection
from app.models import Paciente
from fastapi import HTTPException

def obtener_paciente_por_id(paciente_id: int):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, documento_id, nombre, apellido, fecha_nacimiento, telefono, direccion, correo FROM pacientes WHERE id = %s",
            (paciente_id,)
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return Paciente(
            id=row['id'],
            documento_id=row['documento_id'],
            nombre=row['nombre'],
            apellido=row['apellido'],
            fecha_nacimiento=str(row['fecha_nacimiento']) if row['fecha_nacimiento'] else None,
            telefono=row.get('telefono'),
            direccion=row.get('direccion'),
            correo=row.get('correo')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en DB: {e}")
    finally:
        if conn:
            conn.close()

