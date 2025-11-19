#!/bin/bash
# setup.sh - Script de configuración automática COMPLETO
# Sistema de Historia Clínica Distribuida - Versión Final
# Incluye: Usuarios, Roles, 57 campos, PDF

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  🏥 SISTEMA DE HISTORIA CLÍNICA DISTRIBUIDA${NC}"
echo -e "${GREEN}  📦 Instalación Completa - Versión Final${NC}"
echo -e "${GREEN}================================================================${NC}\n"

print_step() { echo -e "\n${YELLOW}[PASO $1]${NC} ${CYAN}$2${NC}"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

NAMESPACE="citus"

# Detectar directorio
if [ -f "citus-deployment.yaml" ]; then
    PROJECT_DIR="."
    echo -e "${YELLOW}📁 Ejecutando desde: project/${NC}"
elif [ -f "project/citus-deployment.yaml" ]; then
    PROJECT_DIR="project"
    echo -e "${YELLOW}📁 Ejecutando desde: raíz del repositorio${NC}"
else
    echo -e "${RED}Error: No se encuentra citus-deployment.yaml${NC}"
    exit 1
fi

# ==================== PASO 1: Verificar requisitos ====================
print_step 1 "Verificando requisitos previos"
command -v minikube >/dev/null 2>&1 && print_success "Minikube instalado" || print_error "Minikube NO instalado"
command -v kubectl >/dev/null 2>&1 && print_success "kubectl instalado" || print_error "kubectl NO instalado"
command -v docker >/dev/null 2>&1 && print_success "Docker instalado" || print_error "Docker NO instalado"
command -v python3 >/dev/null 2>&1 && print_success "Python3 instalado" || print_error "Python3 NO instalado"

# ==================== PASO 2: Iniciar Minikube ====================
print_step 2 "Iniciando Minikube"
if minikube status | grep -q "Running"; then
    print_success "Minikube ya está corriendo"
else
    minikube start --cpus=4 --memory=4096 --driver=docker
    print_success "Minikube iniciado"
fi

# ==================== PASO 3: Crear/Limpiar namespace ====================
print_step 3 "Configurando namespace"
if kubectl get namespace $NAMESPACE >/dev/null 2>&1; then
    print_warning "Namespace '$NAMESPACE' ya existe. ¿Desea eliminarlo y recrearlo? (y/N)"
    read -t 10 -n 1 respuesta || respuesta="n"
    echo
    if [[ "$respuesta" =~ ^[Yy]$ ]]; then
        kubectl delete namespace $NAMESPACE
        sleep 5
        kubectl create namespace $NAMESPACE
        print_success "Namespace '$NAMESPACE' recreado"
    else
        print_info "Continuando con namespace existente"
    fi
else
    kubectl create namespace $NAMESPACE
    print_success "Namespace '$NAMESPACE' creado"
fi

# ==================== PASO 4: Desplegar Citus ====================
print_step 4 "Desplegando Citus (coordinator + 2 workers)"
kubectl apply -f $PROJECT_DIR/citus-deployment.yaml
echo "⏳ Esperando a que los pods estén listos (puede tardar 1-2 minutos)..."
sleep 15
kubectl wait --for=condition=ready pod -l app=citus-coordinator -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=citus-worker -n $NAMESPACE --timeout=300s
print_success "Citus desplegado correctamente"

# ==================== PASO 5: Configurar base de datos ====================
print_step 5 "Configurando base de datos PostgreSQL + Citus"

COORDINATOR_POD=$(kubectl get pod -n $NAMESPACE -l app=citus-coordinator -o jsonpath="{.items[0].metadata.name}")
print_info "Pod coordinador: $COORDINATOR_POD"

echo "⏳ Esperando a que PostgreSQL esté listo..."
sleep 10

# Crear base de datos
echo -e "\n${BLUE}>>> Creando base de datos historiaclinica...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -c "CREATE DATABASE historiaclinica;" 2>&1 | grep -v "already exists" || true
print_success "Base de datos verificada"

# Crear extensiones
echo -e "\n${BLUE}>>> Instalando extensiones (citus, pgcrypto)...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "CREATE EXTENSION IF NOT EXISTS citus;"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
print_success "Extensiones instaladas"

# Crear tabla USUARIOS
echo -e "\n${BLUE}>>> Creando tabla de usuarios...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- bash -c 'cat > /tmp/create_usuarios.sql << "EOSQL"
\c historiaclinica

CREATE TABLE IF NOT EXISTS public.usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('"'"'paciente'"'"', '"'"'medico'"'"', '"'"'admisionista'"'"', '"'"'resultados'"'"', '"'"'admin'"'"')),
    nombres VARCHAR(200),
    apellidos VARCHAR(200),
    documento_vinculado VARCHAR(20),
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    ultimo_acceso TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usuarios_username ON public.usuarios(username);
CREATE INDEX IF NOT EXISTS idx_usuarios_rol ON public.usuarios(rol);
EOSQL'

kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -f /tmp/create_usuarios.sql
print_success "Tabla usuarios creada"

# Insertar usuarios de prueba
echo -e "\n${BLUE}>>> Insertando usuarios de prueba...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- bash -c 'cat > /tmp/insert_usuarios.sql << "EOSQL"
\c historiaclinica

INSERT INTO public.usuarios (username, password_hash, rol, nombres, apellidos, documento_vinculado)
VALUES
('"'"'admin'"'"', crypt('"'"'admin'"'"', gen_salt('"'"'bf'"'"')), '"'"'admin'"'"', '"'"'Administrador'"'"', '"'"'Sistema'"'"', NULL),
('"'"'dr_rodriguez'"'"', crypt('"'"'password123'"'"', gen_salt('"'"'bf'"'"')), '"'"'medico'"'"', '"'"'Carlos'"'"', '"'"'Rodríguez'"'"', NULL),
('"'"'dra_martinez'"'"', crypt('"'"'password123'"'"', gen_salt('"'"'bf'"'"')), '"'"'medico'"'"', '"'"'Ana'"'"', '"'"'Martínez'"'"', NULL),
('"'"'admisionista1'"'"', crypt('"'"'password123'"'"', gen_salt('"'"'bf'"'"')), '"'"'admisionista'"'"', '"'"'María'"'"', '"'"'González'"'"', NULL),
('"'"'resultados1'"'"', crypt('"'"'password123'"'"', gen_salt('"'"'bf'"'"')), '"'"'resultados'"'"', '"'"'Pedro'"'"', '"'"'López'"'"', NULL),
('"'"'paciente_juan'"'"', crypt('"'"'password123'"'"', gen_salt('"'"'bf'"'"')), '"'"'paciente'"'"', '"'"'Juan'"'"', '"'"'Pérez'"'"', '"'"'12345'"'"'),
('"'"'paciente_maria'"'"', crypt('"'"'password123'"'"', gen_salt('"'"'bf'"'"')), '"'"'paciente'"'"', '"'"'María'"'"', '"'"'Gómez'"'"', '"'"'67890'"'"')
ON CONFLICT (username) DO NOTHING;
EOSQL'

kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -f /tmp/insert_usuarios.sql
print_success "7 usuarios de prueba insertados"

# Crear tabla PACIENTES (57 campos)
echo -e "\n${BLUE}>>> Creando tabla pacientes (57 campos)...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- bash -c 'cat > /tmp/create_pacientes.sql << "EOSQL"
\c historiaclinica

DROP TABLE IF EXISTS public.pacientes CASCADE;

CREATE TABLE public.pacientes (
    id SERIAL,
    tipo_documento VARCHAR(20) NOT NULL,
    numero_documento VARCHAR(20) NOT NULL UNIQUE,
    primer_apellido VARCHAR(100) NOT NULL,
    segundo_apellido VARCHAR(100),
    primer_nombre VARCHAR(100) NOT NULL,
    segundo_nombre VARCHAR(100),
    fecha_nacimiento DATE NOT NULL,
    sexo VARCHAR(10) NOT NULL CHECK (sexo IN ('"'"'M'"'"', '"'"'F'"'"', '"'"'Otro'"'"')),
    genero VARCHAR(50),
    grupo_sanguineo VARCHAR(5) CHECK (grupo_sanguineo IN ('"'"'A+'"'"', '"'"'A-'"'"', '"'"'B+'"'"', '"'"'B-'"'"', '"'"'AB+'"'"', '"'"'AB-'"'"', '"'"'O+'"'"', '"'"'O-'"'"')),
    factor_rh VARCHAR(10),
    estado_civil VARCHAR(20) CHECK (estado_civil IN ('"'"'Soltero'"'"', '"'"'Casado'"'"', '"'"'Union Libre'"'"', '"'"'Divorciado'"'"', '"'"'Viudo'"'"')),
    direccion_residencia TEXT,
    municipio VARCHAR(100),
    departamento VARCHAR(100),
    telefono VARCHAR(20),
    celular VARCHAR(20),
    correo_electronico VARCHAR(100),
    ocupacion VARCHAR(100),
    entidad VARCHAR(100),
    regimen_afiliacion VARCHAR(50) CHECK (regimen_afiliacion IN ('"'"'Contributivo'"'"', '"'"'Subsidiado'"'"', '"'"'Especial'"'"', '"'"'No afiliado'"'"')),
    tipo_usuario VARCHAR(50),
    fecha_atencion TIMESTAMP DEFAULT NOW(),
    tipo_atencion VARCHAR(50) CHECK (tipo_atencion IN ('"'"'Urgencias'"'"', '"'"'Consulta Externa'"'"', '"'"'Hospitalizacion'"'"', '"'"'Cirugia'"'"', '"'"'Procedimiento'"'"')),
    motivo_consulta TEXT,
    enfermedad_actual TEXT,
    antecedentes_personales TEXT,
    antecedentes_familiares TEXT,
    alergias_conocidas TEXT,
    habitos TEXT,
    medicamentos_actuales TEXT,
    tension_arterial VARCHAR(20),
    frecuencia_cardiaca INTEGER,
    frecuencia_respiratoria INTEGER,
    temperatura DECIMAL(4,2),
    saturacion_oxigeno INTEGER,
    peso DECIMAL(5,2),
    talla DECIMAL(5,2),
    examen_fisico_general TEXT,
    examen_fisico_sistemas TEXT,
    impresion_diagnostica TEXT,
    codigos_cie10 TEXT,
    conducta_plan TEXT,
    recomendaciones TEXT,
    medicos_interconsultados TEXT,
    procedimientos_realizados TEXT,
    resultados_examenes TEXT,
    diagnostico_definitivo TEXT,
    evolucion_medica TEXT,
    tratamiento_instaurado TEXT,
    formulacion_medica TEXT,
    educacion_paciente TEXT,
    referencia_contrarreferencia TEXT,
    estado_egreso VARCHAR(50) CHECK (estado_egreso IN ('"'"'Mejorado'"'"', '"'"'Igual'"'"', '"'"'Empeorado'"'"', '"'"'Fallecido'"'"', '"'"'Remitido'"'"')),
    nombre_profesional VARCHAR(200),
    tipo_profesional VARCHAR(50),
    registro_medico VARCHAR(50),
    cargo_servicio VARCHAR(100),
    firma_profesional TEXT,
    firma_paciente TEXT,
    fecha_cierre TIMESTAMP,
    responsable_registro VARCHAR(200),
    fecha_registro TIMESTAMP DEFAULT NOW(),
    ultima_actualizacion TIMESTAMP DEFAULT NOW(),
    activo BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (numero_documento, id)
);

CREATE INDEX idx_pacientes_nombres ON public.pacientes(primer_nombre, primer_apellido);
CREATE INDEX idx_pacientes_fecha_atencion ON public.pacientes(fecha_atencion);
CREATE INDEX idx_pacientes_tipo_atencion ON public.pacientes(tipo_atencion);
EOSQL'

kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -f /tmp/create_pacientes.sql
print_success "Tabla pacientes creada (57 campos)"

# Distribuir tabla pacientes
echo -e "\n${BLUE}>>> Distribuyendo tabla pacientes en Citus...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT create_distributed_table('public.pacientes', 'numero_documento');"
print_success "Tabla distribuida por numero_documento"

# Insertar pacientes de prueba
echo -e "\n${BLUE}>>> Insertando pacientes de prueba...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- bash -c 'cat > /tmp/insert_pacientes.sql << "EOSQL"
\c historiaclinica

INSERT INTO public.pacientes (
    tipo_documento, numero_documento, primer_apellido, segundo_apellido, primer_nombre, segundo_nombre,
    fecha_nacimiento, sexo, genero, grupo_sanguineo, factor_rh, estado_civil,
    direccion_residencia, municipio, departamento, telefono, celular, correo_electronico,
    ocupacion, entidad, regimen_afiliacion, tipo_usuario, tipo_atencion, motivo_consulta, enfermedad_actual,
    tension_arterial, frecuencia_cardiaca, frecuencia_respiratoria, temperatura, saturacion_oxigeno, peso, talla,
    impresion_diagnostica, nombre_profesional, tipo_profesional
) VALUES
(
    '"'"'CC'"'"', '"'"'12345'"'"', '"'"'Pérez'"'"', '"'"'Gómez'"'"', '"'"'Juan'"'"', '"'"'Carlos'"'"',
    '"'"'1995-04-12'"'"', '"'"'M'"'"', '"'"'Masculino'"'"', '"'"'O+'"'"', '"'"'Positivo'"'"', '"'"'Soltero'"'"',
    '"'"'Calle 123 #45-67'"'"', '"'"'Sincelejo'"'"', '"'"'Sucre'"'"', '"'"'2774500'"'"', '"'"'3001234567'"'"', '"'"'juanp@example.com'"'"',
    '"'"'Ingeniero'"'"', '"'"'Nueva EPS'"'"', '"'"'Contributivo'"'"', '"'"'Afiliado'"'"', '"'"'Consulta Externa'"'"', '"'"'Control de rutina'"'"', '"'"'Paciente asintomático que acude a control médico preventivo'"'"',
    '"'"'120/80'"'"', 72, 16, 36.5, 98, 75.0, 175.0,
    '"'"'Paciente sano, control preventivo'"'"', '"'"'Dr. Carlos Rodríguez'"'"', '"'"'Médico General'"'"'
),
(
    '"'"'CC'"'"', '"'"'67890'"'"', '"'"'Gómez'"'"', '"'"'Martínez'"'"', '"'"'María'"'"', '"'"'Fernanda'"'"',
    '"'"'1989-09-30'"'"', '"'"'F'"'"', '"'"'Femenino'"'"', '"'"'A+'"'"', '"'"'Positivo'"'"', '"'"'Casado'"'"',
    '"'"'Carrera 45 #12-34'"'"', '"'"'Sincelejo'"'"', '"'"'Sucre'"'"', '"'"'2774501'"'"', '"'"'3109876543'"'"', '"'"'mariag@example.com'"'"',
    '"'"'Docente'"'"', '"'"'Sanitas EPS'"'"', '"'"'Contributivo'"'"', '"'"'Afiliado'"'"', '"'"'Consulta Externa'"'"', '"'"'Dolor abdominal'"'"', '"'"'Paciente refiere dolor abdominal de 2 días de evolución'"'"',
    '"'"'110/70'"'"', 78, 18, 36.8, 97, 62.0, 165.0,
    '"'"'Gastritis aguda'"'"', '"'"'Dra. Ana Martínez'"'"', '"'"'Médico General'"'"'
),
(
    '"'"'CC'"'"', '"'"'11111'"'"', '"'"'López'"'"', '"'"'Torres'"'"', '"'"'Pedro'"'"', '"'"'Antonio'"'"',
    '"'"'1992-06-15'"'"', '"'"'M'"'"', '"'"'Masculino'"'"', '"'"'B+'"'"', '"'"'Positivo'"'"', '"'"'Union Libre'"'"',
    '"'"'Avenida 80 #20-10'"'"', '"'"'Sincelejo'"'"', '"'"'Sucre'"'"', '"'"'2774502'"'"', '"'"'3201112233'"'"', '"'"'pedro@example.com'"'"',
    '"'"'Comerciante'"'"', '"'"'Coosalud'"'"', '"'"'Subsidiado'"'"', '"'"'Subsidiado'"'"', '"'"'Urgencias'"'"', '"'"'Trauma en pierna derecha'"'"', '"'"'Paciente con trauma en miembro inferior derecho por caída'"'"',
    '"'"'130/85'"'"', 88, 20, 37.0, 96, 80.0, 172.0,
    '"'"'Esguince grado II tobillo derecho'"'"', '"'"'Dr. Carlos Rodríguez'"'"', '"'"'Médico Urgencias'"'"'
)
ON CONFLICT (numero_documento) DO NOTHING;
EOSQL'

kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -f /tmp/insert_pacientes.sql
print_success "3 pacientes de prueba insertados"

# Verificación de datos
echo -e "\n${BLUE}>>> Verificando datos insertados...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT COUNT(*) as total_usuarios FROM public.usuarios;"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT COUNT(*) as total_pacientes FROM public.pacientes;"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT * FROM citus_tables WHERE table_name::text = 'pacientes';"

# ==================== PASO 6: Docker ====================
print_step 6 "Construyendo imagen Docker del middleware"
if [ "$PROJECT_DIR" != "." ]; then cd $PROJECT_DIR; fi
docker build -t middleware-citus:1.0 .
if [ "$PROJECT_DIR" != "." ]; then cd ..; fi
print_success "Imagen construida"

minikube image load middleware-citus:1.0
print_success "Imagen cargada en Minikube"

# ==================== PASO 7: Secrets ====================
print_step 7 "Creando secrets de Kubernetes"
kubectl create secret generic app-secrets \
  --from-literal=POSTGRES_HOST=citus-coordinator \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_DB=historiaclinica \
  --from-literal=POSTGRES_USER=postgres \
  --from-literal=POSTGRES_PASSWORD=password \
  --from-literal=SECRET_KEY=20240902734 \
  --from-literal=ALGORITHM=HS256 \
  --from-literal=ACCESS_TOKEN_EXPIRE_MINUTES=30 \
  -n $NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -
print_success "Secrets configurados"

# ==================== PASO 8: Middleware ====================
print_step 8 "Desplegando middleware FastAPI"
kubectl apply -f $PROJECT_DIR/infra/app-deployment.yaml
sleep 15
kubectl wait --for=condition=ready pod -l app=middleware-citus -n $NAMESPACE --timeout=300s
print_success "Middleware desplegado"

# ==================== PASO 9: Verificación Final ====================
print_step 9 "Verificación final del sistema"

echo -e "\n${CYAN}📊 Estado de Pods:${NC}"
kubectl get pods -n $NAMESPACE

echo -e "\n${CYAN}📊 Estado de Servicios:${NC}"
kubectl get svc -n $NAMESPACE

echo -e "\n${CYAN}📊 Tablas en Base de Datos:${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"

# ==================== PASO 10: Instrucciones ====================
print_step 10 "¡Instalación Completa!"

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ SISTEMA COMPLETAMENTE OPERATIVO${NC}"
echo -e "${GREEN}================================================================${NC}\n"

echo -e "${CYAN}📝 USUARIOS DE PRUEBA:${NC}"
echo -e "  ${GREEN}Admin:${NC}       admin / admin"
echo -e "  ${GREEN}Médico 1:${NC}    dr_rodriguez / password123"
echo -e "  ${GREEN}Médico 2:${NC}    dra_martinez / password123"
echo -e "  ${GREEN}Admisionista:${NC} admisionista1 / password123"
echo -e "  ${GREEN}Resultados:${NC}  resultados1 / password123"
echo -e "  ${GREEN}Paciente 1:${NC}  paciente_juan / password123 (doc: 12345)"
echo -e "  ${GREEN}Paciente 2:${NC}  paciente_maria / password123 (doc: 67890)"

echo -e "\n${CYAN}🚀 PARA ACCEDER A LA API:${NC}"
echo -e "  ${YELLOW}kubectl port-forward -n citus service/middleware-citus-service 8000:8000 &${NC}"

echo -e "\n${CYAN}🧪 PROBAR LA API:${NC}"
echo -e "  ${YELLOW}curl http://localhost:8000/health${NC}"

echo -e "\n${CYAN}🔐 OBTENER TOKEN:${NC}"
echo -e "  ${YELLOW}curl -X POST http://localhost:8000/token \\"
echo -e "    -H 'Content-Type: application/json' \\"
echo -e "    -d '{\"username\":\"admin\",\"password\":\"admin\"}'${NC}"

echo -e "\n${CYAN}📚 DOCUMENTACIÓN:${NC}"
echo -e "  Swagger UI: ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "  ReDoc:      ${YELLOW}http://localhost:8000/redoc${NC}"

echo -e "\n${CYAN}✅ EJECUTAR TESTS:${NC}"
if [ "$PROJECT_DIR" = "." ]; then
    echo -e "  ${YELLOW}./test_api.sh${NC}"
else
    echo -e "  ${YELLOW}./project/test_api.sh${NC}"
fi

echo -e "\n${GREEN}¡Sistema listo para usar!${NC}\n"
