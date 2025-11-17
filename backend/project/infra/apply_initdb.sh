#!/usr/bin/env bash
#!/bin/bash
set -e

NAMESPACE="citus"
INITDB_DIR="project/infra/initdb"

POD=$(kubectl get pod -n $NAMESPACE -l app=citus-coordinator -o jsonpath="{.items[0].metadata.name}")

echo "📦 Copiando scripts initdb al pod $POD..."
kubectl cp $INITDB_DIR $NAMESPACE/$POD:/tmp/initdb

echo "🚀 Ejecutando scripts en el coordinador..."

for file in $(ls $INITDB_DIR | sort); do
  echo "⚙️ Ejecutando: /tmp/initdb/$file"
  kubectl exec -n $NAMESPACE -it $POD -- psql -U postgres -f /tmp/initdb/$file || true
done

echo "✅ InitDB completado."


