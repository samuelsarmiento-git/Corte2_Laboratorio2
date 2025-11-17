-- 04_distribute_table.sql
-- Conectar a la base de datos historiaclinica
\\c historiaclinica

-- Crear la tabla distribuida correctamente por documento_id
-- Usar el esquema PUBLIC, no gestion_medica
SELECT create_distributed_table('public.pacientes', 'documento_id');

-- Verificar que la tabla se distribuyó correctamente
SELECT * FROM citus_tables;
