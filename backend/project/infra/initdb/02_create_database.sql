-- 02_create_database.sql
\echo 'Creando base de datos historiaclinica si no existe...'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'historiaclinica') THEN
        PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE historiaclinica');
    END IF;
END $$;

