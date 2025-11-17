-- 03_create_schema_and_table.sql
\connect historiaclinica

CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS public.pacientes (
    id SERIAL,
    documento_id VARCHAR(20) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100),
    fecha_nacimiento DATE,
    telefono VARCHAR(20),
    direccion TEXT,
    correo VARCHAR(100),
    genero VARCHAR(10),
    tipo_sangre VARCHAR(5),
    fecha_registro TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (documento_id, id)
);

