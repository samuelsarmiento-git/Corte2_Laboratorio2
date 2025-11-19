#!/bin/bash
# quick_fix.sh - Solución rápida de problemas de conexión
# Guarda este archivo en: backend/project/quick_fix.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

NAMESPACE="citus"

echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}  🔧 SOLUCIÓN RÁPIDA - Historia Clínica${NC}"
echo -e "${GREEN}================================================================${NC}\n"

# ==================== PASO 1: VERIFICAR SECRETS ====================
echo -e "${YELLOW}[PASO 1/6]${NC} Verificando y recreando secrets..."

# Eliminar secret antiguo
kubectl delete secret app-secrets -n $NAMESPACE 2>/dev/null || true

# Crear secret nuevo con valores correctos
kubectl create secret generic app-secrets \
  --from-literal=POSTGRES_HOST=citus-coordinator \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_DB=historiaclinica \
  --from-literal=POSTGRES_USER=postgres \
  --from-literal=POSTGRES_PASSWORD=password \
  --from-literal=SECRET_KEY=20240902734 \
  --from-literal=ALGORITHM=HS256 \
  --from-literal=ACCESS_TOKEN_EXPIRE_MINUTES=30 \
  -n $NAMESPACE

echo -e "${GREEN}✓${NC} Secrets recreados"
sleep 2

# ==================== PASO 2: VERIFICAR ARCHIVOS ====================
echo -e "\n${YELLOW}[PASO 2/6]${NC} Copiando archivos corregidos..."

# Verificar que existan los archivos corregidos
if [ ! -f "app/database.py" ]; then
    echo -e "${RED}✗ Error: app/database.py no encontrado${NC}"
    exit 1
fi

if [ ! -f "app/main.py" ]; then
    echo -e "${RED}✗ Error: app/main.py no encontrado${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Archivos verificados"

# ==================== PASO 3: LIMPIAR IMÁGENES ====================
echo -e "\n${YELLOW}[PASO 3/6]${NC} Limpiando imágenes antiguas..."

# Limpiar imagen local
docker rmi middleware-citus:1.0 -f 2>/dev/null || true

# Limpiar imagen en Minikube
minikube ssh "docker rmi -f middleware-citus:1.0 2>/dev/null || true" 2>/dev/null || true

echo -e "${GREEN}✓${NC} Imágenes limpiadas"
sleep 2

# ==================== PASO 4: RECONSTRUIR IMAGEN ====================
echo -e "\n${YELLOW}[PASO 4/6]${NC} Reconstruyendo imagen Docker..."

docker build --no-cache -t middleware-citus:1.0 . 2>&1 | grep -E "CACHED|DONE|writing image|Successfully" || true

echo -e "${GREEN}✓${NC} Imagen reconstruida"

# Cargar en Minikube
minikube image load middleware-citus:1.0
echo -e "${GREEN}✓${NC} Imagen cargada en Minikube"
sleep 2

# ==================== PASO 5: REDESPLEGAR MIDDLEWARE ====================
echo -e "\n${YELLOW}[PASO 5/6]${NC} Redesplegando middleware..."

# Eliminar deployment actual
kubectl delete deployment middleware-citus -n $NAMESPACE 2>/dev/null || true
sleep 5

# Aplicar deployment nuevo
kubectl apply -f infra/app-deployment.yaml

# Esperar a que esté listo
echo "Esperando a que el pod esté listo..."
kubectl wait --for=condition=ready pod -l app=middleware-citus -n $NAMESPACE --timeout=120s

MIDDLEWARE_POD=$(kubectl get pod -n $NAMESPACE -l app=middleware-citus -o jsonpath="{.items[0].metadata.name}")
echo -e "${GREEN}✓${NC} Middleware desplegado: $MIDDLEWARE_POD"
sleep 3

# ==================== PASO 6: VERIFICAR ====================
echo -e "\n${YELLOW}[PASO 6/6]${NC} Verificando solución..."

echo "Logs del middleware:"
kubectl logs -n $NAMESPACE $MIDDLEWARE_POD --tail=10

echo -e "\n${CYAN}Probando conexión a BD desde el pod:${NC}"
kubectl exec -n $NAMESPACE $MIDDLEWARE_POD -- python3 -m app.database 2>&1

# ==================== INSTRUCCIONES FINALES ====================
echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ SOLUCIÓN APLICADA${NC}"
echo -e "${GREEN}================================================================${NC}\n"

echo -e "${CYAN}Siguiente paso - Probar la API:${NC}"
echo ""
echo "1. Iniciar port-forward:"
echo -e "   ${YELLOW}kubectl port-forward -n citus service/middleware-citus-service 8000:8000 &${NC}"
echo ""
echo "2. Probar health check:"
echo -e "   ${YELLOW}curl http://localhost:8000/health${NC}"
echo ""
echo "3. Si sigue fallando, ejecuta el diagnóstico:"
echo -e "   ${YELLOW}./diagnose_connection.sh${NC}"
echo ""
echo "4. Ver logs en tiempo real:"
echo -e "   ${YELLOW}kubectl logs -n citus $MIDDLEWARE_POD -f${NC}"
echo ""
