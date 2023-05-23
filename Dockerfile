FROM python:3.8

# Establecer un directorio de trabajo
WORKDIR /jaguarchat

# Copiar el archivo requirements.txt al contenedor
COPY requirements.txt .

# Instalar las dependencias del proyecto
RUN pip install --upgrade pip && pip install -r requirements.txt 

RUN python -m nltk.downloader punkt

RUN pip install https://github.com/explosion/spacy-models/releases/download/es_core_news_lg-3.5.0/es_core_news_lg-3.5.0.tar.gz



# Copiar el resto del código del proyecto al contenedor
COPY . .

# Establecer la variable de entorno para el puerto
ENV PORT ${PORT}

# Exponer el puerto en el contenedor
EXPOSE ${PORT}

# Ejecutar el comando para iniciar la aplicación
CMD ["python", "app.py"]
