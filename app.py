import uuid
import openai
from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from gtts import gTTS
import os
import tempfile
import nltk
import spacy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from oauthlib.oauth2 import WebApplicationClient
import pymongo
import requests
import os
import bcrypt
from flask import Flask, request, session
import json
from datetime import datetime
from flask import render_template, request
from analisis import obtener_datos, analizar_temas_mas_consultados, contar_palabras, analizar_nivel_comprension, analizar_sentimientos, obtener_horario_mayor_actividad
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import pytz
from flask import request, redirect, url_for, render_template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "unsecretoaleatorio")
app.config["SESSION_PROTECTION"] = "strong"
scheduler = BackgroundScheduler()
scheduler.start()

api_key = os.getenv("OPENAI_API_KEY")

mongo_uri = os.environ.get("MONGO_URI")
mongo_client = pymongo.MongoClient(mongo_uri)

db = mongo_client["jaguar_chat"]
col_usuarios = db["usuarios"]
col_historial = db["historial"]

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

client_id = "836684526994-int362jsg2860o9nichmmglajn7ls2ik.apps.googleusercontent.com"
client_secret = "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"
client = WebApplicationClient(client_id)

class Usuario(UserMixin):
    def __init__(self, user_data):
        self.id = user_data["_id"]
        self.email = user_data["email"]
        self.name = user_data.get("name", "")  

class RegistrationForm(FlaskForm):
    first_name = StringField('Nombre', validators=[DataRequired()])
    last_name = StringField('Apellido', validators=[DataRequired()])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('password')])
    grade = SelectField('Grado de estudio', choices=[('1', 'Primero'), ('2', 'Segundo'), ('3', 'Tercero')], validators=[DataRequired()])
    school = StringField('Escuela', validators=[DataRequired()])
    teacher = StringField('Profesor', validators=[DataRequired()])
    accept_terms = BooleanField('Acepto los términos y condiciones', validators=[DataRequired()])
    submit = SubmitField('Registrarse')

def get_db_connection():
    mongodb_uri = os.environ.get('MONGO_URI')
    client = MongoClient(mongo_uri)
    db = client["jaguar_chat"]
    return db

def guardar_historial(user_id, prompt, response):
    fecha = datetime.now()
    conversacion = {
        "user_id": user_id,
        "prompt": prompt,
        "response": response,
        "timestamp": fecha,  
    }
    col_historial.insert_one(conversacion)

def limpiar_historial():
    print("Limpiando historial...")
    fecha_limite = datetime.now(pytz.utc) - timedelta(days=1)
    db.historial.delete_many({"timestamp": {"$lt": fecha_limite}})
    print("Historial limpiado.")
trigger = IntervalTrigger(days=1)
scheduler.add_job(limpiar_historial, trigger)

def enviar_email_mailgun(asunto, contenido, destinatario):
    mailgun_api_key = os.environ.get('MAILGUN_API_KEY')  
    mailgun_domain = os.environ.get('MAILGUN_DOMAIN')  

    url = f"https://api.mailgun.net/v3/{mailgun_domain}/messages"
    auth = ("api", mailgun_api_key)
    data = {
        'from': 'tu_email@example.com',
        'to': destinatario,
        'subject': asunto,
        'text': contenido
    }

    response = requests.post(url, auth=auth, data=data)

    return response

def get_db_connection():
    mongo_uri = os.environ.get("MONGO_URI")
    mongo_client = pymongo.MongoClient(mongo_uri)
    db = mongo_client["jaguar_chat"]
    return db

def obtener_usuario_por_email(email):
    db = get_db_connection()
    usuario = db.usuarios.find_one({"email": email})
    if usuario:
        return usuario
    return None

def guardar_token(_id, token):
    db = get_db_connection()
    db.usuarios.update_one({"_id": _id}, {"$set": {"token": token}})
 
def obtener_id_usuario_por_token(token):
    db = get_db_connection()
    usuario = db.usuarios.find_one({"token": token})
    if usuario:
        return usuario["user_id"]
    return None

def actualizar_contraseña(user_id, new_password):
    db = get_db_connection()
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    db.usuarios.update_one({"user_id": user_id}, {"$set": {"password": hashed_password}})

def generar_token():
    return str(uuid.uuid4())

def enviar_email_recuperacion(email, token):
    link = f'https://web-production-7ac0e.up.railway.app/reset_password/{token}'
    subject = 'Recuperación de contraseña'
    html_content = f'<p>Para restablecer tu contraseña, por favor haz clic en el siguiente enlace:</p><p><a href="{link}">{link}</a></p>'
    
    mailgun_api_key = os.environ.get('MAILGUN_API_KEY') 
    mailgun_domain = os.environ.get('MAILGUN_DOMAIN')

    response = requests.post(
        f'https://api.mailgun.net/v3/{mailgun_domain}/messages',
        auth=('api', mailgun_api_key),
        data={
            'from': 'noreply@your_app_domain.com',
            'to': email,
            'subject': subject,
            'html': html_content
        }
    )

    if response.status_code == 200:
        print('Correo electrónico enviado')
    else:
        print('Error al enviar el correo electrónico:', response.status_code)
        print('Detalles del error:', response.text)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegistrationForm()

    if form.validate_on_submit():
        if form.accept_terms.data:
        
            email = form.email.data
            password = form.password.data

            user_data = col_usuarios.find_one({"email": email})
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            if not user_data:
                user_data = {
                    "_id": str(uuid.uuid4()),  
                    "email": email,
                    "password": hashed_password.decode("utf-8") 
                }
                col_usuarios.insert_one(user_data)
                flash("Usuario registrado exitosamente. Por favor, inicie sesión.", "success")
                return redirect(url_for("login"))
            else:
                flash("El correo electrónico ya está registrado. Por favor, inicie sesión.", "warning")
        else:
            flash("Debes aceptar los términos y condiciones para registrarte.", "danger")

    return render_template("signup.html", form=form)


@app.route("/terms_and_conditions")
def terms_and_conditions():
    return render_template("terms_and_conditions.html")

@login_manager.user_loader
def load_user(user_id):
    user_data = col_usuarios.find_one({"_id": user_id})
    if user_data:
        return Usuario(user_data)
    return None

def validar_credenciales(email, password):
    user_data = col_usuarios.find_one({"email": email})
    if user_data:
        hashed_password = user_data["password"].encode("utf-8")
        if bcrypt.checkpw(password.encode("utf-8"), hashed_password):
            user = Usuario(user_data)
            login_user(user)
            return True
    return False

def get_google_auth_url():
    google_auth_base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    redirect_uri = "https://web-production-7ac0e.up.railway.app/auth/callback"
    scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"

    auth_url = client.prepare_request_uri(
        google_auth_base_url,
        redirect_uri=redirect_uri,
        scope=scope,
    )
    return auth_url


@app.route("/login/google")
def login_google():
    auth_url = get_google_auth_url()
    return redirect(auth_url)


@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = "https://web-production-7ac0e.up.railway.app/auth/callback"


    token_response = client.prepare_token_request(
        token_url,
        authorization_response=request.url,
        redirect_url=redirect_uri,
        client_secret=client_secret,
    )
    token_response = requests.post(
        token_url,
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret

        }
    )

    session["token"] = token_response.json()["access_token"]
    print(f"Token de acceso: {session['token']}")  

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    headers = {"Authorization": f"Bearer {session['token']}"}
    userinfo_response = requests.get(userinfo_url, headers=headers)
    userinfo_data = userinfo_response.json()
    print(f"Información del usuario: {userinfo_data}")  


    user_data = col_usuarios.find_one({"email": userinfo_data["email"]})
    if not user_data:
        user_data = {
            "_id": userinfo_data["id"],
            "email": userinfo_data["email"],
            "name": userinfo_data["name"],
        }
        col_usuarios.insert_one(user_data)
    else:
        print(f"Usuario ya registrado: {user_data}") 

    user = Usuario(user_data)
    login_user(user)

    return redirect(url_for("home"))

nlp = spacy.load('es_core_news_sm')

texto = "Este es un ejemplo de texto para tokenizar."
doc = nlp(texto)

tokens = []
for token in doc:
    tokens.append(token.text)

print(tokens)

nltk.data.path.append("C:/Users/smart/desktop/chatgeo/nltk_data")

texto = "Este es un ejemplo de texto para tokenizar."
tokens = nltk.word_tokenize(texto)

print(tokens)

import openai

load_dotenv()
openai.api_key = api_key


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        
        email = request.form['email']
        password = request.form['password']

        user_id = validar_credenciales(email, password)
        if user_id:
            session['user_id'] = user_id
            return redirect(url_for('home'))
        else:
            flash("Credenciales incorrectas. Por favor, inténtalo de nuevo.")
    return render_template("login.html")

@app.route("/")
def home():
    if current_user.is_authenticated:
        return render_template("index.html")
    else:
        return redirect(url_for("login"))

def es_saludo(texto):
    saludos = ["hola", "saludos", "buenos días", "buenas tardes", "buenas noches", "bienvenidos"]
    for saludo in saludos:
        if saludo in texto.lower():
            return True
    return False

def es_tema_educacion_basica(texto):
    palabras_clave_educacion_basica = ["explicar", "decir en qué consiste", "concepto", "ayudar", "qué es", "socializar", "teoremas", "matemáticas", "suma", "resta", "multiplicación", "división", "matemática general", "aritmética", "álgebra", "geometría", "trigonometría", "estadística", "probabilidad","lengua", "ciencias naturales", "sociales", "presidentes", "historia de Ecuador", "geografía de Ecuador", "cívica", "teorema", "valores", "literatura", "escritura", "gramática", "ortografía", "vocabulario", "fauna", "flora"]
    
    doc = nlp(texto.lower())
    tokens = [token.lemma_ for token in doc]

    for palabra_clave in palabras_clave_educacion_basica:
        if palabra_clave in tokens:
            return True
    return False

@app.route('/generate_response', methods=['POST'])
@login_required
def generate_response():
    print(f"Usuario autenticado: {current_user.is_authenticated}")

    if not current_user.is_authenticated:
        return jsonify({"error": "Usuario no autenticado"}), 401
    input_text = request.json.get('input_text', '')

    prompt = request.json["prompt"]
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"En el contexto de la educación básica en matemáticas (suma, resta, multiplicación, división, álgebra, geometría, etc.), lengua y literatura (gramática, ortografía, vocabulario, lectura, etc.), ciencias naturales (biología, física, química, etc.), estudios sociales (historia, geografía, civismo, etc.), y saludar, gracias, saludos y agradecimientos responde: {prompt}",
        max_tokens=300,
        n=1,
        stop=None,
        temperature=0.5,
    ).choices[0].text.strip()

    guardar_historial(current_user.id, prompt, response)
    intentos = 0
    while not es_tema_educacion_basica(response) and intentos < 1:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"En el contexto de la educación básica en matemáticas (suma, resta, multiplicación, división, álgebra, geometría, etc.), lengua y literatura (gramática, ortografía, vocabulario, lectura, etc.), ciencias naturales (biología, física, química, etc.), estudios sociales (historia, geografía, civismo, etc.), y saludar, gracias, saludos y agradecimientos responde: {prompt}",
            max_tokens=300,
            n=1,
            stop=None,
            temperature=0.5,
        ).choices[0].text.strip()
        guardar_historial(current_user.id, prompt, response)
        intentos += 1

    if es_saludo(response):
        return jsonify({"response": "¡Hola! Soy jaguar chat, un bot educativo. ¿En qué puedo ayudarte?"})
    elif "gracias" in response.lower():
        return jsonify({"response": "¡De nada! Estoy aquí para ayudarte en lo que necesites."})
    elif es_seguimiento(response):
        return jsonify({"response": "Claro, ¿qué otra duda tienes?"})
    elif es_tema_educacion_basica(response):
        return jsonify({"response": response})
    else:
        return jsonify({"response": "Lo siento, no entendí tu pregunta. ¿Podrías reformularla con respecto a la educación básica?"})

def es_seguimiento(texto):
    seguimientos = ["¿Algo más?", "¿Te ayudo en algo más?", "¿Necesitas algo más?", "¿En qué más te puedo ayudar?"]
    for seguimiento in seguimientos:
        if seguimiento in texto:
            return True
    return False

@app.route('/')
def index():
    return render_template('index.html')

from json import JSONDecodeError

@app.route('/update_session', methods=['POST'])
def update_session():
    try:
        data = json.loads(request.data)
    except JSONDecodeError:
        return 'Error al procesar datos JSON', 400

    pregunta = data['pregunta']
    respuesta = data['respuesta']

    if 'historial' not in session:
        session['historial'] = []

    session['historial'].append({
        
    'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'pregunta': pregunta,
    'respuesta': respuesta
})

    return '', 200

@app.route('/historial')
@login_required
def historial():
    user_id = str(current_user.get_id()) 
    historial_usuario = list(col_historial.find({"user_id": user_id}))

    historial = [
        {
            "fecha": item["timestamp"] if "timestamp" in item else "N/A",
            "pregunta": item["prompt"],
            "respuesta": item["response"],
        }
        for item in historial_usuario
    ]

    print("Objeto historial:", historial)

    return render_template('historial.html', historial=historial, user_id=user_id)  

@app.route("/speak/<text>")
def speak(text):
    tts = gTTS(text=text, lang="es")
    with tempfile.NamedTemporaryFile(delete=True) as fp:
        tts.save(fp.name)
        return send_file(fp.name, mimetype="audio/mpeg")

@app.route('/analisis/<user_id>')
def analisis(user_id):
    prompts = obtener_datos(user_id)

    temas_consultados = analizar_temas_mas_consultados(prompts)
    print("Temas consultados:", temas_consultados)

    palabras_contadas = list(contar_palabras(prompts).items())
    print("Palabras contadas:", palabras_contadas)

    horas_mayor_actividad = obtener_horario_mayor_actividad(prompts)
    print("Horas mayor actividad:", horas_mayor_actividad)

    nivel_comprension = analizar_nivel_comprension(prompts)
    print("Nivel comprensión:", nivel_comprension)

    sentimientos = analizar_sentimientos(prompts)
    print("Sentimientos:", sentimientos)

    return render_template('analisis.html',
                           temas_consultados=temas_consultados,
                           palabras_contadas=palabras_contadas,
                           horas_mayor_actividad=horas_mayor_actividad,
                           nivel_comprension=nivel_comprension,
                           sentimientos=sentimientos,
                           user_id=user_id)

def obtener_credenciales_email(user_id):
  
    mongo_uri = os.environ.get("MONGO_URI")
    mongo_client = pymongo.MongoClient(mongo_uri)
    db = mongo_client["jaguar_chat"]

    col_usuarios = db["usuarios"]

    usuario = col_usuarios.find_one({'user_id': user_id})

    if usuario:
        return usuario['email'], usuario['email_contrasena']
    else:
        return None, None

@app.route('/enviar_analisis', methods=['GET', 'POST'])
def enviar_analisis():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    if request.method == 'POST':
        profesor_email = request.form['correo_profesor']
    
        resultados_analisis = analisis(user_id)

        email_usuario, _ = obtener_credenciales_email(user_id)

        asunto = "Resultados del análisis"

        contenido = str(resultados_analisis)

        try:
            response = enviar_email_mailgun(asunto, contenido, profesor_email)
            if response.status_code == 200:
                return render_template('resultado_envio.html', enviado=True)
            else:
                print("Error al enviar el correo electrónico:", response.status_code)
                return render_template('resultado_envio.html', enviado=False)
        except Exception as e:
            print("Error al enviar el correo electrónico:", e)
            return render_template('resultado_envio.html', enviado=False)

    return render_template('enviar_analisis.html')

@app.route('/recuperar_contraseña', methods=['GET', 'POST'])
def recuperar_contraseña():
    if request.method == 'POST':
        email = request.form['email']
        user = obtener_usuario_por_email(email)
        if user:
            token = generar_token()
            guardar_token(user['_id'], token)
            enviar_email_recuperacion(email, token)
        return render_template('recuperar_contraseña.html', success=True)
    return render_template('recuperar_contraseña.html', success=False)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_id = obtener_id_usuario_por_token(token)
    if not user_id:
        return render_template('reset_password.html', error=True)

    if request.method == 'POST':
        new_password = request.form['new_password']
        actualizar_contraseña(user_id, new_password)
        return redirect(url_for('login'))

    return render_template('reset_password.html', error=False)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/<path:path>")
def catch_all(path):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)