"""
Created on 2024
@Creator: Juan Bautista Gonzalez
@Position: Student electronic engineering and programmer part-time
@Contact:
    - Email: contacto@juangonzalez.com.ar
"""

# Importar librerías / Import libraries
import os
import requests
import bcrypt
import qrcode
import io
from flask import Flask, render_template, redirect, url_for, request, session, flash, send_file
from functools import wraps

# Crear una instancia de Flask / Create a Flask instance
app = Flask(__name__)
app.secret_key = os.urandom(12).hex()

# Configurar conexión a Supabase usando variables de entorno / Setup Supabase connection using environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
NAME_TABLE_USERS = os.getenv("NAME_TABLE_USERS")
NAME_TABLE_REDIRECT = os.getenv("NAME_TABLE_REDIRECT")

# El header para requests / The header for requests
headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

# Decorador para proteger rutas / Decorator to protect routes


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Función para obtener el contador de visitas desde Supabase


def get_visit_count():
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }
    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/visit_counter?id=eq.1', headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data[0]['count'] if data else 0
    else:
        return 0

# Función para incrementar el contador de visitas en Supabase


def increment_visit_count():
    current_count = get_visit_count()
    new_count = current_count + 1

    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'id': 1,
        'count': new_count
    }

    response = requests.patch(
        f'{SUPABASE_URL}/rest/v1/visit_counter?id=eq.1', headers=headers, json=data)


# Ruta de redirección desde "/" / Redirect route from "/"


@app.route('/')
def index():
    try:
        increment_visit_count()
    except Exception as e:
        print(e)
    # Consultar la URL de redirección en Supabase
    url = f'{SUPABASE_URL}/rest/v1/{NAME_TABLE_REDIRECT}?id=eq.1'
    response = requests.get(url, headers=headers)
    if response and response.json():
        redirect_url = response.json()[0]['redirect_url']
        return redirect(redirect_url)
    return "No se ha definido ninguna URL para redirigir."

# Ruta de login / Login route


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verificar las credenciales del usuario en Supabase
        url = f'{SUPABASE_URL}/rest/v1/{NAME_TABLE_USERS}?username=eq.{username}'
        response = requests.get(url, headers=headers)

        if response.status_code == 200 and response.json():
            stored_password = response.json()[0]['password']

            # Verificar la contraseña hashada usando bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                session['logged_in'] = True
                return redirect(url_for('admin_panel'))
            else:
                flash('Contraseña incorrecta')
        else:
            flash('Usuario no encontrado')

    return render_template('login.html')

# Ruta para el panel de administración


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_panel():
    if request.method == 'POST':
        redirect_url = request.form['redirect_url']

        # Actualizar la URL en Supabase
        url = f'{SUPABASE_URL}/rest/v1/{NAME_TABLE_REDIRECT}?id=eq.1'
        data = {
            'redirect_url': redirect_url
        }
        response = requests.patch(url, json=data, headers=headers)

        if response.status_code == 204:
            flash('URL actualizada con éxito.')
        else:
            flash('Error al actualizar la URL.')

    # Obtener la URL actual desde Supabase
    url = f'{SUPABASE_URL}/rest/v1/{NAME_TABLE_REDIRECT}?id=eq.1'
    response = requests.get(url, headers=headers)

    if response.status_code == 200 and response.json():
        current_url = response.json()[0]['redirect_url']
    else:
        current_url = ''
    visit_count = get_visit_count()

    return render_template('admin.html', current_url=current_url, visit_count=visit_count)

# Generar el código QR de la página principal


@app.route('/qr_code')
def generate_qr():
    # Crear un objeto QRCode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    # Definir el contenido del código QR (en este caso, la URL principal '/')
    # Usamos _external para obtener la URL completa
    data = url_for('index', _external=True)
    qr.add_data(data)
    qr.make(fit=True)

    # Crear la imagen del código QR
    img = qr.make_image(fill='black', back_color='white')

    # Guardar la imagen en un buffer de memoria
    buffer = io.BytesIO()
    img.save(buffer)  # Eliminar el argumento `format='PNG'`
    buffer.seek(0)

    # Retornar la imagen como una respuesta de archivo
    return send_file(buffer, mimetype='image/png')


@app.route('/gen_qr', methods=['GET', 'POST'])
def generate_qr_url():
    if request.method == 'POST':
        link = request.form.get('link')
        if link:
            # Crear un objeto QRCode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(link)
            qr.make(fit=True)

            # Crear la imagen del código QR
            img = qr.make_image(fill='black', back_color='white')

            # Guardar la imagen en un buffer de memoria
            buffer = io.BytesIO()
            img.save(buffer)
            buffer.seek(0)

            # Retornar la imagen como respuesta
            return send_file(buffer, mimetype='image/png')
    return render_template('generate_qr.html')


# Ruta para cerrar sesión


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
