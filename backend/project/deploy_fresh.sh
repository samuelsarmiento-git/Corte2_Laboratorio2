#!/bin/bash
# deploy_fresh.sh - Despliegue fresh del middleware

set -e

RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Despliegue Fresh del Middleware${NC}"
echo -e "${GREEN}========================================${NC}\\n"

NAMESPACE="citus"

# 1. Eliminar deployment actual
echo -e "${YELLOW}[1/5]${NC} Eliminando deployment actual..."
kubectl delete deployment middleware-citus -n $NAMESPACE 2>/dev/null || true
sleep 5

# 2. Aplicar nuevo deployment
echo -e "${YELLOW}[2/5]${NC} Aplicando nuevo deployment..."
kubectl apply -f infra/app-deployment.yaml

# 3. Esperar a que el pod esté listo
echo -e "${YELLOW}[3/5]${NC} Esperando a que el pod esté listo (máx 60s)..."
kubectl wait --for=condition=ready pod -l app=middleware-citus -n $NAMESPACE --timeout=60s

# 4. Verificar que el pod usa la imagen correcta
echo -e "${YELLOW}[4/5]${NC} Verificando imagen del pod..."
POD_NAME=$(kubectl get pod -n $NAMESPACE -l app=middleware-citus -o jsonpath="{.items[0].metadata.name}")
kubectl describe pod -n $NAMESPACE $POD_NAME | grep -A 5 "Image:"

# 5. Ver logs del nuevo pod
echo -e "${YELLOW}[5/5]${NC} Primeras líneas del log (CTRL+C para salir)..."
sleep 3
kubectl logs -n $NAMESPACE -l app=middleware-citus --tail=20

echo -e "\\n${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Despliegue completado${NC}"
echo -e "${GREEN}========================================${NC}\\n"

echo -e "${YELLOW}Siguiente paso:${NC}"
echo "  # Iniciar port-forward"
echo "  pkill -f 'port-forward.*8000' || true"
echo "  kubectl port-forward -n citus service/middleware-citus-service 8000:8000 &"
echo "  sleep 3"
echo ""
echo "  # Ejecutar tests"
echo "  ./test_api.sh"
