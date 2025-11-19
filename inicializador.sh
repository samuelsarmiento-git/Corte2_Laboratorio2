#!/bin/bash
# ==============================================================================
# inicializador.sh - Script Unificado de Despliegue y Lanzamiento
# ==============================================================================
# Este script combina los pasos de:
#   1. setup.sh: Configuración completa del backend en Minikube.
#   2. enable_nodeport.sh: Habilitación de acceso por NodePort.
#   3. expose_to_real_network.sh: Exposición a la red local.
#   4. frontend/prueba.py: Lanzamiento del servidor frontend.
# ==============================================================================

set -e

# --- Configuración Global ---
NAMESPACE="citus"
NODE_PORT=30800
HOST_PORT=8000
PROJECT_DIR="backend/project"
TOTAL_STEPS=16 # Número total de pasos principales

# --- Colores y Helpers ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

STEP_COUNT=1
print_step() { echo -e "\n${YELLOW}[PASO ${STEP_COUNT}/${TOTAL_STEPS}]${NC} ${CYAN}$1${NC}"; STEP_COUNT=$((STEP_COUNT+1)); }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; exit 1; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  🏥 INICIALIZADOR DEL SISTEMA DE HISTORIA CLÍNICA DISTRIBUIDA${NC}"
echo -e "${GREEN}================================================================${NC}\n"

# ==============================================================================
# PARTE 1: LÓGICA DE setup.sh
# ==============================================================================
print_step "Verificando requisitos previos"
command -v minikube >/dev/null 2>&1 && print_success "Minikube instalado" || print_error "Minikube NO instalado"
command -v kubectl >/dev/null 2>&1 && print_success "kubectl instalado" || print_error "kubectl NO instalado"
command -v docker >/dev/null 2>&1 && print_success "Docker instalado" || print_error "Docker NO instalado"
command -v python3 >/dev/null 2>&1 && print_success "Python3 instalado" || print_error "Python3 NO instalado"

print_step "Iniciando Minikube"
if minikube status | grep -q "Running"; then
    print_success "Minikube ya está corriendo"
else
    minikube start --cpus=4 --memory=4096 --driver=docker
    print_success "Minikube iniciado"
fi

print_step "Configurando namespace '$NAMESPACE'"
if kubectl get namespace $NAMESPACE >/dev/null 2>&1; then
    print_warning "Namespace '$NAMESPACE' ya existe. Reusando el namespace existente."
    print_info "Para una instalación limpia, elimina el namespace con: kubectl delete namespace $NAMESPACE"
else
    kubectl create namespace $NAMESPACE
    print_success "Namespace '$NAMESPACE' creado"
fi

print_step "Desplegando Citus (coordinator + 2 workers)"
kubectl apply -f $PROJECT_DIR/citus-deployment.yaml
echo "⏳ Esperando a que los pods de Citus estén listos (puede tardar 1-2 minutos)..."
sleep 15
kubectl wait --for=condition=ready pod -l app=citus-coordinator -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=citus-worker -n $NAMESPACE --timeout=300s
print_success "Citus desplegado correctamente"

print_step "Configurando base de datos PostgreSQL + Citus"
COORDINATOR_POD=$(kubectl get pod -n $NAMESPACE -l app=citus-coordinator -o jsonpath='{.items[0].metadata.name}')
print_info "Pod coordinador: $COORDINATOR_POD"
echo "⏳ Esperando a que PostgreSQL esté listo..."
sleep 10
print_info "Creando base de datos, tablas y usuarios..."
kubectl cp "$PROJECT_DIR/infra/initdb" "$COORDINATOR_POD:/tmp/" -n $NAMESPACE
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- bash -c "psql -U postgres -f /tmp/initdb/01_create_extension.sql"
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- bash -c "psql -U postgres -f /tmp/initdb/02_create_database.sql" || print_warning "La base de datos 'historiaclinica' podría existir ya."
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -f /tmp/initdb/03_create_schema_and_table.sql
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -f /tmp/initdb/04_distribute_table.sql
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -f /tmp/initdb/05_insert_sample_data.sql
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -f /tmp/initdb/06_create_usuarios.sql
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -f /tmp/initdb/07_create_pacientes_completo.sql
kubectl exec -n $NAMESPACE $COORDINATOR_POD -- psql -U postgres -d historiaclinica -f /tmp/initdb/08_insert_data_complete.sql
print_success "Base de datos configurada."

print_step "Construyendo y cargando imagen Docker del middleware"
docker build -t middleware-citus:1.0 $PROJECT_DIR
print_success "Imagen 'middleware-citus:1.0' construida"
minikube image load middleware-citus:1.0
print_success "Imagen cargada en Minikube"

print_step "Creando secrets de Kubernetes"
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

# ==============================================================================
# PARTE 2: LÓGICA DE enable_nodeport.sh
# ==============================================================================
print_step "Deteniendo port-forwards existentes para evitar conflictos"
pkill -f 'port-forward.*8000' 2>/dev/null || true
sleep 2
print_success "Port-forwards detenidos"

print_step "Aplicando configuración NodePort para el middleware"
CONFIG_FILE="$PROJECT_DIR/infra/app-deployment-nodeport.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "No se encuentra el archivo de configuración NodePort: $CONFIG_FILE"
fi
kubectl delete deployment middleware-citus -n $NAMESPACE --ignore-not-found=true
kubectl delete service middleware-citus-service -n $NAMESPACE --ignore-not-found=true
sleep 5
kubectl apply -f $CONFIG_FILE
print_success "Configuración NodePort aplicada"

print_step "Esperando a que los pods del middleware con NodePort estén listos"
echo "⏳ Esperando pods (máximo 120 segundos)..."
kubectl wait --for=condition=ready pod -l app=middleware-citus -n $NAMESPACE --timeout=120s
print_success "Pods del middleware listos"

print_step "Obteniendo información de acceso NodePort"
MINIKUBE_IP=$(minikube ip)
ACTUAL_NODE_PORT=$(kubectl get svc middleware-citus-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')
print_info "IP de Minikube: $MINIKUBE_IP"
print_info "NodePort asignado: $ACTUAL_NODE_PORT"
if [ "$ACTUAL_NODE_PORT" != "$NODE_PORT" ]; then
    print_warning "El NodePort esperado ($NODE_PORT) es diferente al asignado ($ACTUAL_NODE_PORT)."
fi

print_step "Mostrando log de configuración de NodePort"
if [ -f "backend/project/nodeport_setup.log" ]; then
    echo -e "${BLUE}--- Contenido de backend/project/nodeport_setup.log ---${NC}"
    cat "backend/project/nodeport_setup.log"
    echo -e "${BLUE}--------------------------------------------------${NC}"
else
    print_warning "No se encontró el archivo 'backend/project/nodeport_setup.log'"
fi


# ==============================================================================
# PARTE 3: LÓGICA DE expose_to_real_network.sh
# ==============================================================================
print_step "Detectando IP de red local real"
REAL_IP=$(ip addr show | grep "inet " | \
    grep -v "127.0.0.1" | \
    grep -v "172." | \
    grep -v "192.168.49" | \
    grep -oP '(?<=inet\s)\d+\.\d+\.\d+\.\d+' | \
    head -1 || true)
if [ -z "$REAL_IP" ]; then
    print_warning "No se pudo detectar IP de red local automáticamente. Se usará la IP de Minikube."
    REAL_IP=$MINIKUBE_IP
else
    print_success "IP de red local detectada: ${YELLOW}${REAL_IP}${NC}"
fi

print_step "Configurando exposición a la red local"
pkill -f "socat.*8000" 2>/dev/null && print_info "Procesos 'socat' anteriores detenidos." || true
rm -f /tmp/socat_real.pid /tmp/socat_real_network.log
if ! command -v socat &> /dev/null; then
    print_info "Instalando socat..."
    sudo pacman -S --noconfirm socat 2>/dev/null || sudo apt-get install -y socat 2>/dev/null || sudo yum install -y socat 2>/dev/null || print_error "No se pudo instalar socat. Por favor, instálalo manualmente."
fi
print_info "Configurando firewall para permitir el puerto $HOST_PORT..."
sudo iptables -D INPUT -p tcp --dport ${HOST_PORT} -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT -p tcp --dport ${HOST_PORT} -j ACCEPT
print_success "Puerto ${HOST_PORT} abierto en el firewall."

print_step "Creando port forwarding: ${REAL_IP}:${HOST_PORT} -> ${MINIKUBE_IP}:${ACTUAL_NODE_PORT}"
nohup sudo socat \
    TCP4-LISTEN:${HOST_PORT},bind=${REAL_IP},fork,reuseaddr \
    TCP4:${MINIKUBE_IP}:${ACTUAL_NODE_PORT} \
    > /tmp/socat_real_network.log 2>&1 &
SOCAT_PID=$!
echo $SOCAT_PID > /tmp/socat_real.pid
sleep 3
if ! ps -p $SOCAT_PID > /dev/null 2>&1; then
    print_error "socat no pudo iniciar. Revisa /tmp/socat_real_network.log"
fi
print_success "Port forwarding activo (PID: ${SOCAT_PID})"


# ==============================================================================
# PARTE 4: Lanzamiento del Frontend
# ==============================================================================
print_step "Verificando y configurando entorno Python para el frontend"

VENV_DIR="frontend/.venv"
FRONTEND_REQ="frontend/requirements.txt"

# Crear o verificar el entorno virtual
if [ ! -d "$VENV_DIR" ]; then
    print_info "Creando entorno virtual en $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    print_success "Entorno virtual creado."
else
    print_info "Entorno virtual '$VENV_DIR' ya existe."
fi

# Instalar dependencias
if [ -f "$FRONTEND_REQ" ]; then
    print_info "Instalando dependencias de Python para el frontend..."
    "$VENV_DIR/bin/pip" install -r "$FRONTEND_REQ"
    print_success "Dependencias de Python para el frontend instaladas."
else
    print_warning "No se encontró '$FRONTEND_REQ'. Asumiendo que las dependencias están instaladas."
fi


print_step "¡Lanzando servidor del frontend!"
echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ Backend listo y expuesto en ${YELLOW}http://${REAL_IP}:${HOST_PORT}${NC}${GREEN}${NC}"
echo -e "${GREEN}  🚀 El frontend se lanzará a continuación en ${YELLOW}http://localhost:5000${NC}${GREEN}${NC}"
echo -e "${GREEN}================================================================${NC}\n"
echo -e "${CYAN}Presiona Ctrl+C en cualquier momento para detener el servidor frontend.${NC}"
sleep 5

# Lanzar el servidor Python del frontend
# Use the python executable directly from the venv
"$VENV_DIR/bin/python3" frontend/prueba.py

echo -e "\n${GREEN}Script finalizado.${NC}"
