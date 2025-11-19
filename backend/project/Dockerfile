# backend/project/Dockerfile
# Versión DEFINITIVA con dependencias correctas para WeasyPrint
# Compatible con Debian Trixie (base de python:3.10-slim)

FROM python:3.10-slim

# Configuración de Python sin buffer
ENV PYTHONUNBUFFERED=1

# Configurar directorio de trabajo
WORKDIR /app

# ============================================
# INSTALAR DEPENDENCIAS DEL SISTEMA
# Necesarias para WeasyPrint y generación de PDFs
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencias de Cairo (para renderizado gráfico)
    libcairo2 \
    libcairo2-dev \
    # Dependencias de Pango (para texto y fuentes)
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    # Dependencias de GDK-PixBuf (para imágenes) - NOMBRE CORREGIDO
    libgdk-pixbuf-2.0-0 \
    # Dependencias de GLib/GObject (core de GTK)
    libglib2.0-0 \
    libgobject-2.0-0 \
    libgirepository-1.0-1 \
    # Fuentes para PDF
    fontconfig \
    fonts-liberation \
    fonts-dejavu-core \
    # Herramientas de compilación (necesarias para algunas dependencias Python)
    gcc \
    g++ \
    make \
    pkg-config \
    # Limpieza de cache para reducir tamaño de imagen
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# INSTALAR DEPENDENCIAS PYTHON
# ============================================
# Copiar requirements primero (para aprovechar cache de Docker)
COPY requirements.txt /app/requirements.txt

# Instalar todas las dependencias Python
RUN pip install --no-cache-dir -r /app/requirements.txt

# ============================================
# COPIAR CÓDIGO DE LA APLICACIÓN
# ============================================
COPY app /app/app

# ============================================
# CONFIGURACIÓN FINAL
# ============================================
# Exponer puerto de la API
EXPOSE 8000

# Comando para iniciar el servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
