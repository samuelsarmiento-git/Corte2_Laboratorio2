#!/bin/bash
# clean_and_rebuild.sh - Limpieza total y reconstrucción

set -e

RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Limpieza Total y Reconstrucción${NC}"
echo -e "${GREEN}========================================${NC}\\n"

NAMESPACE="citus"

# 1. Eliminar todos los pods del middleware
echo -e "${YELLOW}[1/8]${NC} Eliminando pods del middleware..."
kubectl delete pod -n $NAMESPACE -l app=middleware-citus --force --grace-period=0 || true
sleep 5

# 2. Eliminar imagen local de Docker
echo -e "${YELLOW}[2/8]${NC} Eliminando imagen local..."
docker rmi middleware-citus:1.0 -f 2>/dev/null || true
docker rmi middleware-citus:2.0 -f 2>/dev/null || true

# 3. Eliminar imágenes de Minikube
echo -e "${YELLOW}[3/8]${NC} Eliminando imágenes de Minikube..."
minikube ssh "docker rmi -f middleware-citus:1.0 2>/dev/null || true"
minikube ssh "docker rmi -f middleware-citus:2.0 2>/dev/null || true"
sleep 2

# 4. Limpiar caché de Docker
echo -e "${YELLOW}[4/8]${NC} Limpiando caché de Docker..."
docker builder prune -f
sleep 2

# 5. Reconstruir imagen SIN caché
echo -e "${YELLOW}[5/8]${NC} Reconstruyendo imagen (esto puede tardar ~30s)..."
docker build --no-cache --pull -t middleware-citus:1.0 .

# 6. Verificar que se creó la imagen
echo -e "${YELLOW}[6/8]${NC} Verificando imagen creada..."
docker images | grep middleware-citus

# 7. Cargar en Minikube
echo -e "${YELLOW}[7/8]${NC} Cargando imagen en Minikube..."
minikube image load middleware-citus:1.0

# 8. Verificar imagen en Minikube
echo -e "${YELLOW}[8/8]${NC} Verificando imagen en Minikube..."
minikube ssh "docker images | grep middleware-citus"

echo -e "\\n${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Limpieza y reconstrucción completa${NC}"
echo -e "${GREEN}========================================${NC}\\n"

echo -e "${YELLOW}Siguiente paso:${NC}"
echo "  ./deploy_fresh.sh"
