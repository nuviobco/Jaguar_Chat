FROM python:3.8-slim

# Establecer un directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt al contenedor
COPY requirements.txt .

# Instalar las dependencias del proyecto
RUN python -m venv /opt/venv && /opt/venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt


# Copiar el resto del código del proyecto al contenedor
COPY . .

# Establecer la variable de entorno para el puerto
ENV PORT 8000

# Exponer el puerto en el contenedor
EXPOSE 8000

# Ejecutar el comando para iniciar la aplicación
CMD ["python", "app.py"]