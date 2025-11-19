#!/bin/bash
# clean_and_rebuild.sh - Limpieza total y reconstrucción MEJORADA
# Versión 2.0 - Con verificaciones adicionales

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Limpieza Total y Reconstrucción${NC}"
echo -e "${GREEN}  Versión 2.0 - Mejorada${NC}"
echo -e "${GREEN}========================================${NC}\n"

NAMESPACE="citus"

print_step() { echo -e "\n${YELLOW}[PASO $1/10]${NC} $2"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }

# ==================== PASO 1: Matar Port-Forward ====================
print_step 1 "Deteniendo port-forward existentes..."
pkill -f 'port-forward.*8000' 2>/dev/null || true
print_success "Port-forward detenidos"
sleep 2

# ==================== PASO 2: Eliminar Pods ====================
print_step 2 "Eliminando pods del middleware..."
kubectl delete pod -n $NAMESPACE -l app=middleware-citus --force --grace-period=0 2>/dev/null || true
print_success "Pods eliminados"
sleep 5

# ==================== PASO 3: Eliminar Deployment ====================
print_step 3 "Eliminando deployment..."
kubectl delete deployment middleware-citus -n $NAMESPACE 2>/dev/null || true
print_success "Deployment eliminado"
sleep 3

# ==================== PASO 4: Limpiar Imágenes Docker Local ====================
print_step 4 "Limpiando imágenes Docker locales..."
docker rmi middleware-citus:1.0 -f 2>/dev/null || true
docker rmi middleware-citus:2.0 -f 2>/dev/null || true
docker rmi middleware-citus:latest -f 2>/dev/null || true
print_success "Imágenes locales eliminadas"

# ==================== PASO 5: Limpiar Imágenes Minikube ====================
print_step 5 "Limpiando imágenes en Minikube..."
minikube ssh "docker rmi -f middleware-citus:1.0 2>/dev/null || true" 2>/dev/null || true
minikube ssh "docker rmi -f middleware-citus:2.0 2>/dev/null || true" 2>/dev/null || true
minikube ssh "docker rmi -f middleware-citus:latest 2>/dev/null || true" 2>/dev/null || true
print_success "Imágenes en Minikube eliminadas"
sleep 2

# ==================== PASO 6: Limpiar Caché Docker ====================
print_step 6 "Limpiando caché de Docker..."
docker builder prune -f >/dev/null 2>&1
print_success "Caché limpiado"
sleep 2

# ==================== PASO 7: Verificar auth.py ====================
print_step 7 "Verificando app/auth.py..."
if grep -q "HTTPBearerFixed" app/auth.py; then
    print_success "auth.py tiene la clase personalizada"
else
    print_error "¡ADVERTENCIA! auth.py no tiene HTTPBearerFixed"
    echo -e "${YELLOW}Por favor actualiza app/auth.py con el código corregido${NC}"
fi

# ==================== PASO 8: Reconstruir Imagen ====================
print_step 8 "Reconstruyendo imagen (sin caché, ~30s)..."
echo -e "${BLUE}Construyendo...${NC}"
docker build --no-cache --pull -t middleware-citus:1.0 . 2>&1 | grep -E "CACHED|DONE|writing image" || true
print_success "Imagen reconstruida"

# ==================== PASO 9: Verificar Imagen ====================
print_step 9 "Verificando imagen creada..."
if docker images | grep -q "middleware-citus.*1.0"; then
    print_success "Imagen verificada en Docker"
    docker images | grep middleware-citus
else
    print_error "No se encontró la imagen"
    exit 1
fi

# ==================== PASO 10: Cargar en Minikube ====================
print_step 10 "Cargando imagen en Minikube..."
minikube image load middleware-citus:1.0
print_success "Imagen cargada en Minikube"

# Verificar en Minikube
echo -e "\n${BLUE}Verificando en Minikube:${NC}"
minikube ssh "docker images | grep middleware-citus" || true

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Limpieza y Reconstrucción Completa${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Siguiente paso:${NC}"
echo "  ./deploy_fresh.sh"
echo ""
echo -e "${BLUE}O redesplegar manualmente:${NC}"
echo "  kubectl apply -f infra/app-deployment.yaml"
echo "  kubectl wait --for=condition=ready pod -l app=middleware-citus -n citus --timeout=60s"
