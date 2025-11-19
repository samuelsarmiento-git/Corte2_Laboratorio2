#!/bin/bash
# ==============================================================================
# stop_network_access.sh - Detener Exposición a Red Local
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}  🛑 DETENIENDO ACCESO DE RED LOCAL${NC}"
echo -e "${CYAN}================================================================${NC}\n"

# Detener socat
echo -e "${YELLOW}[1/3]${NC} Deteniendo port forward..."
if [ -f /tmp/port_forward.pid ]; then
    PID=$(cat /tmp/port_forward.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID 2>/dev/null || sudo kill $PID
        echo -e "${GREEN}✓${NC} Port forward detenido (PID: $PID)"
    else
        echo -e "${YELLOW}⚠${NC} Proceso ya no existe"
    fi
    rm -f /tmp/port_forward.pid
else
    echo -e "${YELLOW}⚠${NC} No se encontró PID guardado"
fi

# Matar todos los procesos socat en puerto 8000
pkill -f "socat.*8000" 2>/dev/null && echo -e "${GREEN}✓${NC} Procesos socat detenidos" || true

# Limpiar iptables
echo -e "\n${YELLOW}[2/3]${NC} Limpiando reglas iptables..."
MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "192.168.49.2")
sudo iptables -t nat -D PREROUTING -p tcp --dport 8000 -j DNAT --to-destination ${MINIKUBE_IP}:30800 2>/dev/null || true
sudo iptables -t nat -D PREROUTING -p tcp --dport 8000 -j DNAT --to-destination ${MINIKUBE_IP}:30800 2>/dev/null || true
echo -e "${GREEN}✓${NC} Reglas eliminadas"

# Limpiar archivos temporales
echo -e "\n${YELLOW}[3/3]${NC} Limpiando archivos temporales..."
rm -f /tmp/port_forward_api.sh
rm -f /tmp/port_forward.log
rm -f /tmp/network_access_info.txt
echo -e "${GREEN}✓${NC} Archivos eliminados"

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ ACCESO DE RED DETENIDO${NC}"
echo -e "${GREEN}================================================================${NC}"

echo -e "\n${CYAN}El sistema ahora solo es accesible desde localhost${NC}"
echo -e "${CYAN}Para acceder localmente:${NC}"
echo -e "  kubectl port-forward -n citus service/middleware-citus-service 8000:8000 &\n"
