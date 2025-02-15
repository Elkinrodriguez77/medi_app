import os
import urllib.parse
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__, template_folder="templates")  # Asegurar que busca en "templates"
CORS(app)

# Configurar la conexión a Azure SQL
server = os.getenv("server")
database = os.getenv("database")
username = "useradmin"
password = os.getenv("password")

# 🔥 Codificar la conexión para SQLAlchemy
params = urllib.parse.quote_plus(
    f"DRIVER=ODBC Driver 17 for SQL Server;SERVER={server};DATABASE={database};UID={username};PWD={password}"
)

connection_string = f"mssql+pyodbc:///?odbc_connect={params}"

app.config["SQLALCHEMY_DATABASE_URI"] = connection_string
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# 📌 Modelo de datos con trimestre
class DatosEstrategicos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pilar_estrategico = db.Column(db.String(100))
    objetivo_estrategico = db.Column(db.String(100))
    real = db.Column(db.Float)
    periodo = db.Column(db.Date)
    trimestre = db.Column(db.String(10))  # Q1, Q2, Q3, Q4
    anio = db.Column(db.Integer)

# Crear la base de datos si no existe
with app.app_context():
    db.create_all()

# 📌 Función para determinar el trimestre
def obtener_trimestre(fecha):
    mes = fecha.month
    if mes in [1, 2, 3]:
        return "Q1"
    elif mes in [4, 5, 6]:
        return "Q2"
    elif mes in [7, 8, 9]:
        return "Q3"
    else:
        return "Q4"

# 📌 Ruta para renderizar la página principal (index.html)
@app.route('/')
def index():
    return render_template('index.html')

# 📌 API para obtener datos filtrados por Pilar y Objetivo
@app.route('/datos', methods=['GET'])
def obtener_datos():
    pilar = request.args.get('pilar')
    objetivo = request.args.get('objetivo')

    query = DatosEstrategicos.query.filter_by(pilar_estrategico=pilar, objetivo_estrategico=objetivo).all()
    
    return jsonify([
        {
            "id": d.id,
            "pilar_estrategico": d.pilar_estrategico,
            "objetivo_estrategico": d.objetivo_estrategico,
            "real": d.real,
            "periodo": d.periodo.strftime('%Y-%m-%d'),
            "trimestre": d.trimestre,
            "anio": d.anio
        } for d in query
    ])

# 📌 API para insertar o actualizar datos por trimestre
@app.route('/datos', methods=['POST'])
def agregar_dato():
    data = request.json
    fecha = datetime.strptime(data['periodo'], '%Y-%m-%d')  # Convertir a formato datetime
    trimestre = obtener_trimestre(fecha)
    anio = fecha.year

    # Buscar si ya existe un dato para ese Pilar-Objetivo-Trimestre-Año
    existente = DatosEstrategicos.query.filter_by(
        pilar_estrategico=data['pilar_estrategico'],
        objetivo_estrategico=data['objetivo_estrategico'],
        trimestre=trimestre,
        anio=anio
    ).first()

    if existente:
        # Si ya hay un dato en el mismo trimestre, lo actualizamos
        existente.real = data['real']
        existente.periodo = fecha
        db.session.commit()
        return jsonify({"mensaje": "Registro actualizado en el mismo trimestre"}), 200
    else:
        # Si no hay un dato en ese trimestre, creamos uno nuevo
        nuevo_dato = DatosEstrategicos(
            pilar_estrategico=data['pilar_estrategico'],
            objetivo_estrategico=data['objetivo_estrategico'],
            real=data['real'],
            periodo=fecha,
            trimestre=trimestre,
            anio=anio
        )
        db.session.add(nuevo_dato)
        db.session.commit()
        return jsonify({"mensaje": "Registro guardado para un nuevo trimestre"}), 201

if __name__ == '__main__':
    app.run(debug=True)
