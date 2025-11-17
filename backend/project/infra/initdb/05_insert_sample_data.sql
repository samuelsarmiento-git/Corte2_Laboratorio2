-- 05_insert_sample_data.sql
\connect historiaclinica

INSERT INTO public.pacientes (documento_id, nombre, apellido, fecha_nacimiento, telefono, direccion, correo, genero, tipo_sangre)
VALUES
('12345', 'Juan', 'Pérez', '1995-04-12', '3001234567', 'Calle 123 #45-67', 'juanp@example.com', 'M', 'O+'),
('67890', 'María', 'Gómez', '1989-09-30', '3109876543', 'Carrera 45 #12-34', 'mariag@example.com', 'F', 'A+');
