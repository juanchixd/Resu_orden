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
import json
import fitz
from flask import Flask, render_template, redirect, url_for, request, session, flash, send_file
from functools import wraps
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Crear una instancia de Flask / Create a Flask instance
app = Flask(__name__)
app.secret_key = os.urandom(12).hex()

# Configurar conexión a Supabase usando variables de entorno / Setup Supabase connection using environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
NAME_TABLE_USERS = os.getenv("NAME_TABLE_USERS")
NAME_TABLE_REDIRECT = os.getenv("NAME_TABLE_REDIRECT")
FOLDER_ID = os.getenv('FOLDER_ID')
SERVICE_ACCOUNT_JSON = os.getenv('SERVICE_ACCOUNT_FILE')
SCOPES = ['https://www.googleapis.com/auth/drive.file']

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


def authenticate_google_service():
    # Cargar las credenciales desde la variable de entorno
    service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)
    return creds


def upload_file(file, filename):
    # Subir a Google Drive directamente sin guardar el archivo
    creds = authenticate_google_service()
    drive_service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': filename,
        'parents': [FOLDER_ID]
    }

    # Usar MediaIoBaseUpload para manejar flujos de bytes
    media = MediaIoBaseUpload(io.BytesIO(file.read()),
                              mimetype='application/pdf', resumable=True)

    # Subir archivo
    uploaded_file = drive_service.files().create(
        body=file_metadata, media_body=media, fields='id').execute()

    # Obtener el ID del archivo
    file_id = uploaded_file.get('id')

    # Hacer que el archivo sea público
    permission = {
        'role': 'reader',
        'type': 'anyone',
    }
    drive_service.permissions().create(fileId=file_id, body=permission).execute()

    # Obtener el enlace para compartir
    shared_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    return shared_link


def split_and_reorder_pdf(input_pdf_stream, output_pdf_stream, order=None):
    # Abre el PDF original desde el stream en memoria
    doc = fitz.open(stream=input_pdf_stream, filetype="pdf")
    output = fitz.open()  # Crea un nuevo PDF
    split_pages = []  # Lista para almacenar las páginas recortadas

    # Recorre todas las páginas del documento y divide en tres partes verticales
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        rect = page.rect
        width = rect.width / 3

        # Agrega las tres partes recortadas a la lista
        split_pages.extend([(page_num, fitz.Rect(
            i * width, 0, (i + 1) * width, rect.height)) for i in range(3)])

     # Si no se proporciona un orden, usar el orden original
    if order is None:
        order = list(range(len(split_pages)))

    # Guardar las páginas reorganizadas en el archivo de salida
    for i in order:
        page_num, sub_rect = split_pages[i]
        page = doc.load_page(page_num)
        new_page = output.new_page(
            width=sub_rect.width, height=sub_rect.height)
        new_page.show_pdf_page(new_page.rect, doc, page_num, clip=sub_rect)

    # Guardar el PDF en el stream de salida
    output.save(output_pdf_stream)
    output.close()


@app.route('/split_upload_drive', methods=['GET', 'POST'])
@login_required
def split_upload_drive():
    if request.method == 'POST':
        # Obtener el archivo PDF subido
        pdf_file = request.files['pdf']

        # Obtener el nombre del archivo original
        original_filename = pdf_file.filename
        base_name, _ = original_filename.rsplit(
            '.', 1)  # Obtener el nombre sin la extensión

        # Buffer para el archivo PDF resultante en memoria
        output_pdf_buffer = io.BytesIO()

        # Dividir las páginas del PDF y reordenarlas
        split_and_reorder_pdf(
            pdf_file.read(), output_pdf_buffer, order=[2, 3, 4, 5, 0, 1])

        # Enviar el archivo resultante al usuario
        output_pdf_buffer.seek(0)

        shared_link = upload_file(output_pdf_buffer, f'{base_name}.pdf')

        # Actualizar la URL en Supabase
        url = f'{SUPABASE_URL}/rest/v1/{NAME_TABLE_REDIRECT}?id=eq.1'
        data = {
            'redirect_url': shared_link
        }
        response = requests.patch(url, json=data, headers=headers)

        if response.status_code == 204:
            flash('URL actualizada con éxito.')
        else:
            flash('Error al actualizar la URL.')

        return redirect(url_for('admin_panel'))


# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
