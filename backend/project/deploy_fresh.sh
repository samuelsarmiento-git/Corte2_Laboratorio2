#!/bin/bash
# ==============================================================================
# deploy_fresh.sh - Redespliegue del middleware
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Redespliegue del Middleware${NC}\n"

NAMESPACE="citus"

echo "1. Eliminando deployment actual..."
kubectl delete deployment middleware-citus -n $NAMESPACE 2>/dev/null || true
sleep 5

echo "2. Aplicando nuevo deployment..."
kubectl apply -f infra/app-deployment.yaml

echo "3. Esperando pods..."
kubectl wait --for=condition=ready pod -l app=middleware-citus -n $NAMESPACE --timeout=120s

echo "4. Verificando..."
kubectl get pods -n $NAMESPACE -l app=middleware-citus
kubectl logs -n $NAMESPACE -l app=middleware-citus --tail=20

echo -e "\n${GREEN}✓ Deployment completado${NC}"

# ==============================================================================
# clean_and_rebuild.sh - Limpieza y reconstrucción completa
# ==============================================================================

#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🧹 Limpieza y Reconstrucción${NC}\n"

NAMESPACE="citus"

echo "1. Deteniendo port-forwards..."
pkill -f 'port-forward.*8000' 2>/dev/null || true

echo "2. Eliminando pods..."
kubectl delete pod -n $NAMESPACE -l app=middleware-citus --grace-period=0 --force 2>/dev/null || true
sleep 5

echo "3. Eliminando deployment..."
kubectl delete deployment middleware-citus -n $NAMESPACE 2>/dev/null || true

echo "4. Limpiando imágenes Docker..."
docker rmi middleware-citus:1.0 -f 2>/dev/null || true
minikube ssh "docker rmi -f middleware-citus:1.0 2>/dev/null || true" 2>/dev/null || true

echo "5. Limpiando cache..."
docker builder prune -f

echo "6. Reconstruyendo imagen..."
docker build --no-cache -t middleware-citus:1.0 .

echo "7. Cargando en Minikube..."
minikube image load middleware-citus:1.0

echo "8. Verificando imagen..."
minikube ssh "docker images | grep middleware-citus"

echo -e "\n${GREEN}✓ Limpieza completa${NC}"
echo -e "${YELLOW}Siguiente paso: ./deploy_fresh.sh${NC}"

# ==============================================================================
# enable_network_access.sh - Habilitar acceso desde red local
# ==============================================================================

#!/bin/bash
set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🌐 Configurando Acceso desde Red Local${NC}\n"

NAMESPACE="citus"

echo "1. Aplicando configuración NodePort..."
kubectl apply -f infra/app-deployment-nodeport.yaml

echo "2. Esperando pods..."
sleep 10
kubectl wait --for=condition=ready pod -l app=middleware-citus -n $NAMESPACE --timeout=120s

echo "3. Obteniendo información de acceso..."
MINIKUBE_IP=$(minikube ip)
NODE_PORT=$(kubectl get svc middleware-citus-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')

echo -e "\n${GREEN}✓ Configuración completa${NC}\n"

echo -e "${CYAN}📡 ACCESO DESDE RED LOCAL:${NC}"
echo -e "  URL: ${YELLOW}http://${MINIKUBE_IP}:${NODE_PORT}${NC}"
echo -e "  Swagger: ${YELLOW}http://${MINIKUBE_IP}:${NODE_PORT}/docs${NC}"

echo -e "\n${CYAN}🧪 PROBAR:${NC}"
echo -e "  ${YELLOW}curl http://${MINIKUBE_IP}:${NODE_PORT}/health${NC}"

echo -e "\n${CYAN}💡 NOTA:${NC}"
echo -e "  Otros dispositivos en tu red pueden acceder usando la IP de Minikube"
echo -e "  Si usas Docker driver, necesitas: ${YELLOW}minikube tunnel${NC} en otra terminal\n"

# ==============================================================================
# stop_system.sh - Detener sistema completo
# ==============================================================================

#!/bin/bash
set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}🛑 Deteniendo Sistema${NC}\n"

echo "1. Deteniendo port-forwards..."
pkill -f 'port-forward' 2>/dev/null || true

echo "2. Eliminando namespace..."
kubectl delete namespace citus --timeout=60s

echo "3. Deteniendo Minikube..."
minikube stop

echo -e "\n${YELLOW}✓ Sistema detenido${NC}"
echo -e "${YELLOW}Para reiniciar: ./setup.sh${NC}\n"
