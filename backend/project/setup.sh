#!/bin/bash
# setup.sh - Script de configuración automática Semana 1
# VERSIÓN DEFINITIVA - Crea archivos SQL temporales para asegurar ejecución

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Historia Clínica Distribuida - Setup${NC}"
echo -e "${GREEN}  Semana 1: Infraestructura + Middleware${NC}"
echo -e "${GREEN}========================================${NC}\n"

print_step() { echo -e "\n${YELLOW}[PASO $1]${NC} $2"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

NAMESPACE="citus"

# Detectar directorio
if [ -f "citus-deployment.yaml" ]; then
    PROJECT_DIR="."
    echo -e "${YELLOW}Ejecutando desde: project/${NC}"
elif [ -f "project/citus-deployment.yaml" ]; then
    PROJECT_DIR="project"
    echo -e "${YELLOW}Ejecutando desde: raíz del repositorio${NC}"
else
    echo -e "${RED}Error: No se encuentra citus-deployment.yaml${NC}"
    exit 1
fi

# ==================== PASO 1: Verificar requisitos ====================
print_step 1 "Verificando requisitos previos..."
command -v minikube >/dev/null 2>&1 && print_success "Minikube instalado" || print_error "Minikube NO instalado"
command -v kubectl >/dev/null 2>&1 && print_success "kubectl instalado" || print_error "kubectl NO instalado"
command -v docker >/dev/null 2>&1 && print_success "Docker instalado" || print_error "Docker NO instalado"
command -v python3 >/dev/null 2>&1 && print_success "Python3 instalado" || print_error "Python3 NO instalado"

# ==================== PASO 2: Iniciar Minikube ====================
print_step 2 "Iniciando Minikube..."
if minikube status | grep -q "Running"; then
    print_success "Minikube ya está corriendo"
else
    minikube start --cpus=4 --memory=4096 --driver=docker
    print_success "Minikube iniciado"
fi

# ==================== PASO 3: Crear namespace ====================
print_step 3 "Creando namespace..."
if kubectl get namespace $NAMESPACE >/dev/null 2>&1; then
    print_success "Namespace '$NAMESPACE' ya existe"
else
    kubectl create namespace $NAMESPACE
    print_success "Namespace '$NAMESPACE' creado"
fi

# ==================== PASO 4: Desplegar Citus ====================
print_step 4 "Desplegando Citus..."
kubectl apply -f $PROJECT_DIR/citus-deployment.yaml
echo "Esperando a que los pods estén listos..."
sleep 10
kubectl wait --for=condition=ready pod -l app=citus-coordinator -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=citus-worker -n $NAMESPACE --timeout=300s
print_success "Citus desplegado correctamente"

# ==================== PASO 5: Configurar base de datos ====================
print_step 5 "Configurando base de datos..."

COORDINATOR_POD=$(kubectl get pod -n $NAMESPACE -l app=citus-coordinator -o jsonpath="{.items[0].metadata.name}")
echo "Pod coordinador: $COORDINATOR_POD"

echo "Esperando a que PostgreSQL esté listo..."
sleep 10

# Crear base de datos
echo -e "\n${BLUE}>>> Creando base de datos historiaclinica...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -c "CREATE DATABASE historiaclinica;" 2>&1 | grep -v "already exists" || true
print_success "BD verificada"

# Crear extensiones
echo -e "\n${BLUE}>>> Creando extensiones...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "CREATE EXTENSION IF NOT EXISTS citus;"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
print_success "Extensiones creadas"

# CRÍTICO: Crear tabla usando un archivo temporal en el pod
echo -e "\n${BLUE}>>> Creando tabla pacientes (método alternativo)...${NC}"

# Método 1: Crear archivo SQL en el pod
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- bash -c 'cat > /tmp/create_table.sql << "EOSQL"
\c historiaclinica

DROP TABLE IF EXISTS public.pacientes CASCADE;

CREATE TABLE public.pacientes (
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
EOSQL'

# Ejecutar el archivo SQL
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -f /tmp/create_table.sql

print_success "Tabla creada"

# Verificar que la tabla existe
echo -e "\n${BLUE}>>> Verificando tabla...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "\d public.pacientes"

# Distribuir tabla
echo -e "\n${BLUE}>>> Distribuyendo tabla...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT create_distributed_table('public.pacientes', 'documento_id');"
print_success "Tabla distribuida"

# Verificar distribución
echo -e "\n${BLUE}>>> Verificando distribución...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT * FROM citus_tables;"

# Insertar datos
echo -e "\n${BLUE}>>> Insertando datos...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- bash -c 'cat > /tmp/insert_data.sql << "EOSQL"
\c historiaclinica

INSERT INTO public.pacientes (documento_id, nombre, apellido, fecha_nacimiento, telefono, direccion, correo, genero, tipo_sangre)
VALUES
('\''12345'\'', '\''Juan'\'', '\''Pérez'\'', '\''1995-04-12'\'', '\''3001234567'\'', '\''Calle 123 #45-67'\'', '\''juanp@example.com'\'', '\''M'\'', '\''O+'\''),
('\''67890'\'', '\''María'\'', '\''Gómez'\'', '\''1989-09-30'\'', '\''3109876543'\'', '\''Carrera 45 #12-34'\'', '\''mariag@example.com'\'', '\''F'\'', '\''A+'\''),
('\''11111'\'', '\''Pedro'\'', '\''López'\'', '\''1992-06-15'\'', '\''3201112233'\'', '\''Avenida 80 #20-10'\'', '\''pedro@example.com'\'', '\''M'\'', '\''B+'\'')
ON CONFLICT (documento_id, id) DO NOTHING;
EOSQL'

kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -f /tmp/insert_data.sql
print_success "Datos insertados"

# Verificar datos
echo -e "\n${BLUE}>>> Verificando datos...${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT COUNT(*) as total FROM public.pacientes;"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT id, documento_id, nombre, apellido FROM public.pacientes;"

# ==================== PASO 6: Docker ====================
print_step 6 "Construyendo imagen Docker..."
if [ "$PROJECT_DIR" != "." ]; then cd $PROJECT_DIR; fi
docker build -t middleware-citus:1.0 .
if [ "$PROJECT_DIR" != "." ]; then cd ..; fi
print_success "Imagen construida"

minikube image load middleware-citus:1.0
print_success "Imagen cargada en Minikube"

# ==================== PASO 7: Secrets ====================
print_step 7 "Creando secrets..."
kubectl create secret generic app-secrets \
  --from-literal=POSTGRES_HOST=citus-coordinator \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_DB=historiaclinica \
  --from-literal=POSTGRES_USER=postgres \
  --from-literal=POSTGRES_PASSWORD=password \
  --from-literal=SECRET_KEY=20240902734 \
  -n $NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -
print_success "Secrets creados"

# ==================== PASO 8: Middleware ====================
print_step 8 "Desplegando middleware..."
kubectl apply -f $PROJECT_DIR/infra/app-deployment.yaml
sleep 15
kubectl wait --for=condition=ready pod -l app=middleware-citus -n $NAMESPACE --timeout=300s
print_success "Middleware desplegado"

# ==================== PASO 9: Verificación ====================
print_step 9 "Verificación final..."

echo -e "\n${YELLOW}Pods:${NC}"
kubectl get pods -n $NAMESPACE

echo -e "\n${YELLOW}Servicios:${NC}"
kubectl get svc -n $NAMESPACE

echo -e "\n${YELLOW}Base de datos:${NC}"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT * FROM citus_tables;"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -c "SELECT COUNT(*) as total_pacientes FROM public.pacientes;"

# ==================== PASO 10: Instrucciones ====================
print_step 10 "¡Instalación completa!"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ TODO LISTO${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Para acceder a la API:${NC}"
echo "  kubectl port-forward -n citus service/middleware-citus-service 8000:8000 &"
echo ""
echo -e "${YELLOW}Probar:${NC}"
echo "  curl http://localhost:8000/health"
echo ""
echo -e "${YELLOW}Token:${NC}"
echo '  curl -X POST http://localhost:8000/token -H "Content-Type: application/json" -d '"'"'{"username":"admin","password":"admin"}'"'"
echo ""
echo -e "${YELLOW}Pruebas:${NC}"
if [ "$PROJECT_DIR" = "." ]; then
    echo "  ./test_api.sh"
else
    echo "  ./project/test_api.sh"
fi
echo ""
echo -e "${GREEN}¡Sistema operativo!${NC}\n"
