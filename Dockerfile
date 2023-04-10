FROM python:3.8

# Establecer un directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt al contenedor
COPY requirements.txt .

# Instalar las dependencias del proyecto
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar el resto del código del proyecto al contenedor
COPY . .

# Establecer la variable de entorno para el puerto
ENV PORT 5000

# Exponer el puerto en el contenedor
EXPOSE 5000

# Ejecutar el comando para iniciar la aplicación
CMD ["python", "app.py"]
