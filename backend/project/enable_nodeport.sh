#!/bin/bash
# ==============================================================================
# enable_nodeport.sh - Habilitar Acceso desde Red Local
# ==============================================================================
# Script automatizado para configurar NodePort y habilitar acceso externo
# al Sistema de Historia Clínica desde cualquier dispositivo en la red local.
#
# Uso:
#   chmod +x enable_nodeport.sh
#   ./enable_nodeport.sh
#
# Lo que hace:
#   1. Verifica el estado del cluster
#   2. Aplica configuración NodePort
#   3. Obtiene la IP de Minikube
#   4. Proporciona URLs de acceso
#   5. Ejecuta pruebas de conectividad
# ==============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

NAMESPACE="citus"
NODE_PORT=30800

echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  🌐 HABILITANDO ACCESO DESDE RED LOCAL${NC}"
echo -e "${GREEN}  Sistema de Historia Clínica Distribuida${NC}"
echo -e "${GREEN}================================================================${NC}\n"

print_step() { echo -e "\n${YELLOW}[PASO $1/8]${NC} ${CYAN}$2${NC}"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; exit 1; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# ==================== PASO 1: Verificar Requisitos ====================
print_step 1 "Verificando requisitos previos"

if ! command -v minikube &> /dev/null; then
    print_error "Minikube no está instalado"
fi
print_success "Minikube instalado"

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl no está instalado"
fi
print_success "kubectl instalado"

if ! minikube status | grep -q "Running"; then
    print_error "Minikube no está corriendo. Ejecuta: minikube start"
fi
print_success "Minikube corriendo"

# ==================== PASO 2: Verificar Namespace ====================
print_step 2 "Verificando namespace y pods"

if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    print_error "Namespace '$NAMESPACE' no existe. Ejecuta setup.sh primero"
fi
print_success "Namespace verificado"

# Verificar pods
POD_COUNT=$(kubectl get pods -n $NAMESPACE -l app=middleware-citus --no-headers | wc -l)
if [ "$POD_COUNT" -eq 0 ]; then
    print_error "No hay pods del middleware. Ejecuta setup.sh primero"
fi
print_success "Pods del middleware: $POD_COUNT"

# ==================== PASO 3: Detener Port-Forward ====================
print_step 3 "Deteniendo port-forwards existentes"

pkill -f 'port-forward.*8000' 2>/dev/null || true
sleep 2
print_success "Port-forwards detenidos"

# ==================== PASO 4: Aplicar Configuración NodePort ====================
print_step 4 "Aplicando configuración NodePort"

# Detectar directorio
if [ -f "infra/app-deployment-nodeport.yaml" ]; then
    CONFIG_FILE="infra/app-deployment-nodeport.yaml"
elif [ -f "project/infra/app-deployment-nodeport.yaml" ]; then
    CONFIG_FILE="project/infra/app-deployment-nodeport.yaml"
else
    print_error "No se encuentra app-deployment-nodeport.yaml"
fi

print_info "Archivo: $CONFIG_FILE"

# Eliminar deployment actual
kubectl delete deployment middleware-citus -n $NAMESPACE 2>/dev/null || true
kubectl delete service middleware-citus-service -n $NAMESPACE 2>/dev/null || true
sleep 5

# Aplicar nueva configuración
kubectl apply -f $CONFIG_FILE
print_success "Configuración aplicada"

# ==================== PASO 5: Esperar Pods ====================
print_step 5 "Esperando a que los pods estén listos"

echo "⏳ Esperando pods (máximo 120 segundos)..."
kubectl wait --for=condition=ready pod -l app=middleware-citus -n $NAMESPACE --timeout=120s

print_success "Pods listos"

# ==================== PASO 6: Obtener Información de Acceso ====================
print_step 6 "Obteniendo información de acceso"

MINIKUBE_IP=$(minikube ip)
print_info "IP de Minikube: $MINIKUBE_IP"

# Verificar puerto
ACTUAL_NODE_PORT=$(kubectl get svc middleware-citus-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')
print_info "NodePort asignado: $ACTUAL_NODE_PORT"

if [ "$ACTUAL_NODE_PORT" != "$NODE_PORT" ]; then
    print_warning "NodePort esperado: $NODE_PORT, obtenido: $ACTUAL_NODE_PORT"
fi

# ==================== PASO 7: Probar Conectividad ====================
print_step 7 "Probando conectividad"

echo "⏳ Esperando 5 segundos para que el servicio esté listo..."
sleep 5

# Test 1: Health check
print_info "Test 1: Health check..."
if curl -s -f "http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/health" > /dev/null; then
    print_success "Health check OK"
else
    print_warning "Health check falló, pero el servicio puede estar iniciando"
fi

# Test 2: Root endpoint
print_info "Test 2: Root endpoint..."
if curl -s -f "http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/" > /dev/null; then
    print_success "Root endpoint OK"
else
    print_warning "Root endpoint no responde aún"
fi

# ==================== PASO 8: Información Final ====================
print_step 8 "Información de acceso"

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ NodePort CONFIGURADO EXITOSAMENTE${NC}"
echo -e "${GREEN}================================================================${NC}\n"

echo -e "${CYAN}📡 ACCESO DESDE RED LOCAL:${NC}"
echo -e "  ${MAGENTA}Base URL:${NC}     ${YELLOW}http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}${NC}"
echo -e "  ${MAGENTA}Health:${NC}       ${YELLOW}http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/health${NC}"
echo -e "  ${MAGENTA}Swagger UI:${NC}   ${YELLOW}http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/docs${NC}"
echo -e "  ${MAGENTA}ReDoc:${NC}        ${YELLOW}http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/redoc${NC}"

echo -e "\n${CYAN}🧪 PROBAR LA API:${NC}"
echo -e "  ${YELLOW}# Health check${NC}"
echo -e "  curl http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/health"
echo ""
echo -e "  ${YELLOW}# Obtener token${NC}"
echo -e "  curl -X POST http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/token \\"
echo -e "    -H 'Content-Type: application/json' \\"
echo -e "    -d '{\"username\":\"admin\",\"password\":\"admin\"}'"
echo ""
echo -e "  ${YELLOW}# Listar pacientes (requiere token)${NC}"
echo -e "  TOKEN=\"tu_token_aqui\""
echo -e "  curl http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/pacientes \\"
echo -e "    -H \"Authorization: Bearer \$TOKEN\""

echo -e "\n${CYAN}📱 ACCESO DESDE OTROS DISPOSITIVOS:${NC}"
echo -e "  ${MAGENTA}Smartphone:${NC}   Abre el navegador y ve a ${YELLOW}http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/docs${NC}"
echo -e "  ${MAGENTA}Tablet:${NC}       Misma URL desde cualquier dispositivo en la red"
echo -e "  ${MAGENTA}Otra PC:${NC}      Acceso directo sin configuración adicional"

echo -e "\n${CYAN}💡 IMPORTANTE:${NC}"
if [ "$(minikube docker-env | grep DOCKER_HOST)" ]; then
    echo -e "  ${YELLOW}⚠${NC}  Estás usando Docker driver. Si no puedes acceder:"
    echo -e "      ${MAGENTA}1.${NC} En otra terminal ejecuta: ${YELLOW}minikube tunnel${NC}"
    echo -e "      ${MAGENTA}2.${NC} Mantén esa terminal abierta mientras uses el sistema"
else
    echo -e "  ${GREEN}✓${NC}  Configuración lista. No se requieren pasos adicionales."
fi

echo -e "\n${CYAN}🔧 COMANDOS ÚTILES:${NC}"
echo -e "  ${YELLOW}Ver logs:${NC}        kubectl logs -n citus -l app=middleware-citus -f"
echo -e "  ${YELLOW}Ver pods:${NC}        kubectl get pods -n citus"
echo -e "  ${YELLOW}Ver servicios:${NC}   kubectl get svc -n citus"
echo -e "  ${YELLOW}Reiniciar pod:${NC}   kubectl delete pod -n citus -l app=middleware-citus"

echo -e "\n${CYAN}📖 USUARIOS DE PRUEBA:${NC}"
echo -e "  ${GREEN}Admin:${NC}       admin / admin"
echo -e "  ${GREEN}Médico:${NC}      dr_rodriguez / password123"
echo -e "  ${GREEN}Paciente:${NC}    paciente_juan / password123 (doc: 12345)"

echo -e "\n${GREEN}¡Sistema accesible desde toda la red local!${NC}\n"

# Guardar información en archivo
cat > nodeport_info.txt << EOF
Sistema de Historia Clínica - Información de Acceso NodePort
================================================================

URLs de Acceso:
- Base URL:     http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}
- Health Check: http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/health
- Swagger UI:   http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/docs
- ReDoc:        http://${MINIKUBE_IP}:${ACTUAL_NODE_PORT}/redoc

Usuarios de Prueba:
- Admin:    admin / admin
- Médico:   dr_rodriguez / password123
- Paciente: paciente_juan / password123

Fecha de configuración: $(date)
EOF

print_info "Información guardada en: ${YELLOW}nodeport_info.txt${NC}"
