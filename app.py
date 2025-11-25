from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime
from functools import wraps
from datetime import datetime, timedelta
# Agrega estos imports al inicio del archivo app.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-key-very-secure")

MONGO_URI = os.environ.get(
    "MONGO_URI", "mongodb+srv://ecolearn-user:lopezjose29@cluster0.hoow10m.mongodb.net/EcoLearn1?retryWrites=true&w=majority&appName=Cluster0" )

try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsAllowInvalidCertificates=False,
        serverSelectionTimeoutMS=10000
    )
    db = client.get_default_database()
    print("Conexión segura establecida con MongoDB Atlas")
except Exception as e:
    print("Conexión segura falló, intentando modo escolar...")
try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10000
    )
    db = client.get_default_database()
    print(" Conexión establecida con MongoDB Atlas (modo escolar sin SSL)")
except Exception as e:
    db = None
    print(" No se pudo conectar con MongoDB Atlas:", e)

# ===== MIDDLEWARE DE AUTENTICACIÓN =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Debes iniciar sesión para acceder a esta página.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ===== RUTAS PÚBLICAS (sin autenticación) =====
@app.route("/")
def index():
    # La página principal es pública
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    # Si ya está logueado, redirigir al perfil
    if session.get('logged_in'):
        return redirect(url_for('perfil_index'))
    
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Completa todos los campos.", "danger")
            return render_template("login/login.html")

        if db is not None:
            try:
                usuario = db.usuarios.find_one({"email": email})
                if usuario:
                    # En una app real, usaríamos bcrypt para verificar la contraseña
                    if usuario.get('password') == password:
                        # Iniciar sesión
                        session['logged_in'] = True
                        session['user_id'] = str(usuario['_id'])
                        session['user_email'] = usuario['email']
                        session['user_name'] = usuario['nombre']
                        
                        flash(f"¡Bienvenido/a {usuario['nombre']}!", "success")
                        return redirect(url_for('perfil_index'))
                    else:
                        flash("Contraseña incorrecta.", "danger")
                else:
                    flash("Usuario no encontrado. Regístrate primero.", "warning")
                    return redirect(url_for('register'))
            except Exception as e:
                flash(f"Error al iniciar sesión: {e}", "danger")
        else:
            flash("Error: Base de datos no conectada.", "danger")

    return render_template("login/login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # Si ya está logueado, redirigir al perfil
    if session.get('logged_in'):
        return redirect(url_for('perfil_index'))
    
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not nombre or not email or not password or not confirm_password:
            flash("Completa todos los campos.", "danger")
            return render_template("login/register.html")

        if password != confirm_password:
            flash("Las contraseñas no coinciden.", "danger")
            return render_template("login/register.html")

        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "danger")
            return render_template("login/register.html")

        if db is not None:
            try:
                # Verificar si el usuario ya existe
                usuario_existente = db.usuarios.find_one({"email": email})
                if usuario_existente:
                    flash("Este correo electrónico ya está registrado.", "warning")
                    return render_template("login/register.html")

                # Crear nuevo usuario
                nuevo_usuario = {
                    "nombre": nombre,
                    "email": email,
                    "password": password,  # En una app real, esto debería estar hasheado
                    "nivel_sostenibilidad": "Principiante",
                    "fecha_creacion": datetime.now(),
                    "fecha_registro": datetime.now()
                }
                
                result = db.usuarios.insert_one(nuevo_usuario)
                
                # Iniciar sesión automáticamente después del registro
                session['logged_in'] = True
                session['user_id'] = str(result.inserted_id)
                session['user_email'] = email
                session['user_name'] = nombre
                
                flash("¡Registro exitoso! Bienvenido/a a EcoLearn.", "success")
                return redirect(url_for('perfil_index'))
                
            except Exception as e:
                flash(f"Error al registrar usuario: {e}", "danger")
        else:
            flash("Error: Base de datos no conectada.", "danger")

    return render_template("login/register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('index'))

# ===== RUTAS PROTEGIDAS (requieren autenticación) =====

@app.route("/perfil")
@login_required
def perfil_index():
    if db is None:
        flash("Base de datos no conectada.", "danger")
        return render_template("perfil/index.html", perfil={})
    
    try:
        perfil = db.usuarios.find_one({"_id": ObjectId(session['user_id'])})
    except:
        perfil = {}
    
    return render_template("perfil/index.html", perfil=perfil)

@app.route("/perfil/create", methods=["GET", "POST"])
@login_required
def perfil_create():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        biografia = request.form.get("biografia", "").strip()
        intereses = request.form.get("intereses", "").strip()
        avatar = request.form.get("avatar", "").strip()
        nivel_sostenibilidad = request.form.get("nivel_sostenibilidad", "").strip()

        if not nombre or not email or not nivel_sostenibilidad:
            flash("Completa todos los campos obligatorios.", "danger")
            return redirect(url_for("perfil_create"))

        if db is not None:
            try:
                update_data = {
                    "nombre": nombre,
                    "email": email,
                    "biografia": biografia,
                    "intereses": intereses,
                    "avatar": avatar,
                    "nivel_sostenibilidad": nivel_sostenibilidad,
                    "fecha_actualizacion": datetime.now()
                }
                
                db.usuarios.update_one(
                    {'_id': ObjectId(session['user_id'])}, 
                    {'$set': update_data}
                )
                
                # Actualizar sesión
                session['user_name'] = nombre
                session['user_email'] = email
                
                flash("Perfil actualizado correctamente.", "success")
            except Exception as e:
                flash(f"Error al actualizar perfil: {e}", "danger")
        else:
            flash("Error: Base de datos no conectada.", "danger")

        return redirect(url_for("perfil_index"))
    return render_template("perfil/create.html")

@app.route("/perfil/edit", methods=["GET", "POST"])
@login_required
def perfil_edit():
    if db is None:
        flash("Base de datos no conectada.", "danger")
        return redirect(url_for("perfil_index"))
    
    try:
        perfil = db.usuarios.find_one({"_id": ObjectId(session['user_id'])})
    except:
        perfil = {}

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        biografia = request.form.get("biografia", "").strip()
        intereses = request.form.get("intereses", "").strip()
        avatar = request.form.get("avatar", "").strip()
        nivel_sostenibilidad = request.form.get("nivel_sostenibilidad", "").strip()

        if not nombre or not email or not nivel_sostenibilidad:
            flash("Completa todos los campos obligatorios.", "danger")
            return redirect(url_for("perfil_edit"))

        update_data = {
            "nombre": nombre,
            "email": email,
            "biografia": biografia,
            "intereses": intereses,
            "avatar": avatar,
            "nivel_sostenibilidad": nivel_sostenibilidad,
            "fecha_actualizacion": datetime.now()
        }

        try:
            db.usuarios.update_one(
                {'_id': ObjectId(session['user_id'])}, 
                {'$set': update_data}
            )
            
            # Actualizar sesión
            session['user_name'] = nombre
            session['user_email'] = email
            
            flash("Perfil actualizado exitosamente.", "success")
        except Exception as e:
            flash(f"Error al actualizar perfil: {e}", "danger")
        
        return redirect(url_for("perfil_index"))

    return render_template("perfil/edit.html", perfil=perfil)

@app.route("/perfil/update-avatar", methods=["POST"])
@login_required
def perfil_update_avatar():
    if db is None:
        flash("Base de datos no conectada.", "danger")
        return redirect(url_for("perfil_index"))
    
    nuevo_avatar = request.form.get("nuevo_avatar", "").strip()
    
    if not nuevo_avatar:
        flash("Debes proporcionar una URL de imagen.", "danger")
        return redirect(url_for("perfil_index"))

    try:
        db.usuarios.update_one(
            {'_id': ObjectId(session['user_id'])}, 
            {'$set': {
                'avatar': nuevo_avatar,
                'fecha_actualizacion': datetime.now()
            }}
        )
        flash("Imagen de perfil actualizada exitosamente.", "success")
    except Exception as e:
        flash(f"Error al actualizar imagen: {e}", "danger")
    
    return redirect(url_for("perfil_index"))

# ===== RUTAS ORIGINALES PROTEGIDAS =====

@app.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        campo1 = request.form.get("campo1", "").strip()
        campo2 = request.form.get("campo2", "").strip()

        if not campo1 or not campo2:
            flash("Completa todos los campos.", "danger")
            return redirect(url_for("create"))

        if db is not None:
            db.registros.insert_one({
                "campo1": campo1,
                "campo2": campo2,
                "user_id": session['user_id']
            })
            flash("Registro creado correctamente.", "success")
        else:
            flash("Error: Base de datos no conectada.", "danger")

        return redirect(url_for("index"))
    return render_template("create.html")

@app.route("/view/<id>")
@login_required
def view(id):
    if db is None:
        flash("Base de datos no conectada.", "danger")
        return redirect(url_for("index"))
    dato = db.registros.find_one({"_id": ObjectId(id)})
    if not dato:
        flash("Registro no encontrado.", "warning")
        return redirect(url_for("index"))
    return render_template("view.html", dato=dato)

@app.route("/edit/<id>", methods=["GET", "POST"])
@login_required
def edit(id):
    if db is None:
        flash("Base de datos no conectada.", "danger")
        return redirect(url_for("index"))
    dato = db.registros.find_one({"_id": ObjectId(id)})
    if not dato:
        flash("Registro no encontrado.", "warning")
        return redirect(url_for("index"))

    if request.method == "POST":
        campo1 = request.form.get("campo1", "").strip()
        campo2 = request.form.get("campo2", "").strip()

        if not campo1 or not campo2:
            flash("Completa todos los campos.", "danger")
            return redirect(url_for("edit", id=id))

        db.registros.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"campo1": campo1, "campo2": campo2}}
        )
        flash("Registro actualizado.", "info")
        return redirect(url_for("index"))

    return render_template("edit.html", dato=dato)

@app.route("/delete/<id>", methods=["POST"])
@login_required
def delete(id):
    if db is None:
        flash("Base de datos no conectada.", "danger")
        return redirect(url_for("index"))
    db.registros.delete_one({"_id": ObjectId(id)})
    flash("Registro eliminado.", "secondary")
    return redirect(url_for("index"))

# ===== RUTAS DE PRODUCTOS PROTEGIDAS =====

@app.route("/productos")
@login_required
def productos_index():
    if db is None:
        flash("Error al obtener datos: la base de datos no está conectada.", "danger")
        return render_template("productos/index.html", productos=[])
    try:
        productos = list(db.productos.find())
    except Exception as e:
        flash(f"Error al obtener productos: {e}", "danger")
        productos = []
    return render_template("productos/index.html", productos=productos)

@app.route("/productos/create", methods=["GET", "POST"])
@login_required
def productos_create():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        precio = request.form.get("precio", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        imagen = request.form.get("imagen", "").strip()
        sostenibilidad = request.form.get("sostenibilidad", "").strip()
        stock = request.form.get("stock", "0").strip()
        materiales = request.form.get("materiales", "").strip()
        
        # Nuevos campos para características
        caracteristica1 = request.form.get("caracteristica1", "").strip()
        caracteristica2 = request.form.get("caracteristica2", "").strip()
        caracteristica3 = request.form.get("caracteristica3", "").strip()

        if not nombre or not categoria or not precio or not descripcion or not sostenibilidad:
            flash("Completa todos los campos obligatorios.", "danger")
            return redirect(url_for("productos_create"))

        if db is not None:
            try:
                # Preparar características
                caracteristicas = []
                if caracteristica1:
                    caracteristicas.append(caracteristica1)
                if caracteristica2:
                    caracteristicas.append(caracteristica2)
                if caracteristica3:
                    caracteristicas.append(caracteristica3)
                
                # Preparar materiales
                lista_materiales = [material.strip() for material in materiales.split(',')] if materiales else []
                
                # Insertar producto con todos los campos
                db.productos.insert_one({
                    "nombre": nombre,
                    "categoria": categoria,
                    "precio": float(precio),
                    "descripcion": descripcion,
                    "imagen": imagen,
                    "sostenibilidad": sostenibilidad,
                    "stock": int(stock),
                    "materiales": lista_materiales,
                    "caracteristicas": caracteristicas,
                    "user_id": session['user_id'],
                    "estado": "activo",
                    "fecha_creacion": datetime.now()
                })
                flash("Producto creado correctamente y publicado en la tienda.", "success")
            except Exception as e:
                flash(f"Error al crear producto: {e}", "danger")
        else:
            flash("Error: Base de datos no conectada.", "danger")

        return redirect(url_for("productos_index"))
    return render_template("productos/create.html")

@app.route("/productos/<id>/edit", methods=["GET", "POST"])
@login_required
def productos_edit(id):
    if db is None:
        flash("Base de datos no conectada.", "danger")
        return redirect(url_for("productos_index"))
    
    producto = db.productos.find_one({"_id": ObjectId(id)})
    if not producto:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("productos_index"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        categoria = request.form.get("categoria", "").strip()
        precio = request.form.get("precio", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        imagen = request.form.get("imagen", "").strip()
        sostenibilidad = request.form.get("sostenibilidad", "").strip()
        stock = request.form.get("stock", "0").strip()
        materiales = request.form.get("materiales", "").strip()
        estado = request.form.get("estado", "activo").strip()

        if not nombre or not categoria or not precio or not descripcion or not sostenibilidad:
            flash("Completa todos los campos obligatorios.", "danger")
            return redirect(url_for("productos_edit", id=id))

        try:
            # Preparar materiales
            lista_materiales = [material.strip() for material in materiales.split(',')] if materiales else []
            
            update_data = {
                "nombre": nombre,
                "categoria": categoria,
                "precio": float(precio),
                "descripcion": descripcion,
                "imagen": imagen,
                "sostenibilidad": sostenibilidad,
                "stock": int(stock),
                "materiales": lista_materiales,
                "estado": estado,
                "fecha_actualizacion": datetime.now()
            }
            
            db.productos.update_one(
                {"_id": ObjectId(id)},
                {"$set": update_data}
            )
            flash("Producto actualizado correctamente.", "info")
        except Exception as e:
            flash(f"Error al actualizar producto: {e}", "danger")
        
        return redirect(url_for("productos_index"))

    return render_template("productos/edit.html", producto=producto)

@app.route("/productos/<id>/delete", methods=["POST"])
@login_required
def productos_delete(id):
    if db is None:
        flash("Base de datos no conectada.", "danger")
        return redirect(url_for("productos_index"))
    
    db.productos.delete_one({"_id": ObjectId(id)})
    flash("Producto eliminado.", "secondary")
    return redirect(url_for("productos_index"))

# ===== RUTAS PARA CURSOS =====
@app.route("/cursos/sostenibilidad-basica")
@login_required
def curso_sostenibilidad():
    return render_template("cursos/sostenibilidad_basica.html")

@app.route("/cursos/consumo-responsable")
@login_required
def curso_consumo():
    return render_template("cursos/consumo_responsable.html")

@app.route("/cursos/energias-limpias")
@login_required
def curso_energias():
    return render_template("cursos/energias_limpias.html")

# Ruta para procesar pagos (ejemplo básico)
@app.route("/procesar-pago", methods=["POST"])
@login_required
def procesar_pago():
    curso_id = request.form.get("curso_id")
    monto = request.form.get("monto")
    
    # Aquí iría la lógica real de procesamiento de pago
    # Por ahora es solo un ejemplo
    
    flash("¡Pago procesado exitosamente! Ahora tienes acceso al curso.", "success")
    return redirect(url_for('perfil_index'))

# ===== RUTAS PARA RECUPERACIÓN DE CONTRASEÑA =====

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        
        if not email:
            flash("Por favor ingresa tu correo electrónico.", "danger")
            return render_template("login/forgot_password.html")
        
        if db is not None:
            try:
                usuario = db.usuarios.find_one({"email": email})
                if usuario:
                    # Generar token único
                    import secrets
                    token = secrets.token_urlsafe(32)
                    expiration = datetime.now() + timedelta(hours=1)  # Token válido por 1 hora
                    
                    # Guardar token en la base de datos
                    db.password_resets.insert_one({
                        "email": email,
                        "token": token,
                        "expiration": expiration,
                        "used": False
                    })
                    
                    # En una aplicación real, aquí enviarías el correo
                    # Por ahora solo mostramos el token en desarrollo
                    if app.debug:
                        flash(f"Token de recuperación (solo en desarrollo): {token}", "info")
                    
                    flash("Se ha enviado un enlace de recuperación a tu correo electrónico.", "success")
                    return redirect(url_for('login'))
                else:
                    flash("No existe una cuenta con ese correo electrónico.", "warning")
            except Exception as e:
                flash(f"Error al procesar la solicitud: {e}", "danger")
        else:
            flash("Error: Base de datos no conectada.", "danger")
    
    return render_template("login/forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if db is None:
        flash("Error: Base de datos no conectada.", "danger")
        return redirect(url_for('login'))
    
    try:
        # Verificar token válido
        reset_request = db.password_resets.find_one({
            "token": token,
            "used": False,
            "expiration": {"$gt": datetime.now()}
        })
        
        if not reset_request:
            flash("El enlace de recuperación es inválido o ha expirado.", "danger")
            return redirect(url_for('forgot_password'))
        
        if request.method == "POST":
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()
            
            if not new_password or not confirm_password:
                flash("Completa todos los campos.", "danger")
                return render_template("login/reset_password.html", token=token)
            
            if len(new_password) < 6:
                flash("La contraseña debe tener al menos 6 caracteres.", "danger")
                return render_template("login/reset_password.html", token=token)
            
            if new_password != confirm_password:
                flash("Las contraseñas no coinciden.", "danger")
                return render_template("login/reset_password.html", token=token)
            
            # Actualizar contraseña del usuario
            db.usuarios.update_one(
                {"email": reset_request["email"]},
                {"$set": {"password": new_password}}  # En una app real, aquí hashearías la contraseña
            )
            
            # Marcar token como usado
            db.password_resets.update_one(
                {"_id": reset_request["_id"]},
                {"$set": {"used": True}}
            )
            
            flash("¡Contraseña actualizada exitosamente! Ahora puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
        
        return render_template("login/reset_password.html", token=token)
        
    except Exception as e:
        flash(f"Error al procesar la solicitud: {e}", "danger")
        return redirect(url_for('login'))

# ===== CONFIGURACIÓN DE CORREO ELECTRÓNICO =====
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USERNAME = os.environ.get("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "noreply@ecolearn.com")

def send_password_reset_email(email, token):
    """
    Envía un correo electrónico con el enlace para restablecer la contraseña
    """
    try:
        # Crear el mensaje
        subject = "Restablecer tu contraseña - EcoLearn"
        
        # En producción, usa tu dominio real
        reset_url = f"http://localhost:5000/reset-password/{token}"  # Cambiar en producción
        
        # Crear contenido HTML del correo
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #198754 0%, #0d6efd 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #198754; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌱 EcoLearn</h1>
                    <p>Plataforma de Aprendizaje Sostenible</p>
                </div>
                <div class="content">
                    <h2>Restablecer Contraseña</h2>
                    <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en EcoLearn.</p>
                    <p>Para crear una nueva contraseña, haz clic en el siguiente botón:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" class="button">Restablecer Contraseña</a>
                    </div>
                    
                    <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
                    <p style="word-break: break-all; background: white; padding: 10px; border-radius: 5px; font-size: 12px;">
                        {reset_url}
                    </p>
                    
                    <p><strong>Importante:</strong> Este enlace expirará en 1 hora por seguridad.</p>
                    <p>Si no solicitaste este restablecimiento, puedes ignorar este mensaje.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 EcoLearn. Todos los derechos reservados.</p>
                    <p>Este es un mensaje automático, por favor no respondas a este correo.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Crear mensaje MIME
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = EMAIL_FROM
        message["To"] = email
        
        # Versión HTML
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Configurar servidor SMTP y enviar
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()  # Seguridad TLS
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(message)
            
        print(f"Correo de recuperación enviado a: {email}")
        return True
        
    except Exception as e:
        print(f"Error enviando correo a {email}: {e}")
        return False

# ===== RUTAS PARA CARRITO, FAVORITOS Y TARJETAS =====

@app.route("/cart")
@login_required
def cart():
    try:
        # Obtener todos los items del carrito
        carrito_items = list(db.carrito.find({"user_id": session['user_id']}))
        
        # Separar por tipo
        cursos_carrito = [item for item in carrito_items if item.get('tipo') == 'curso']
        productos_carrito = [item for item in carrito_items if item.get('tipo') == 'producto']
        
        # Calcular totales
        total_cursos = sum(item['precio'] for item in cursos_carrito)
        total_productos = sum(item['precio'] * item.get('cantidad', 1) for item in productos_carrito)
        total_general = total_cursos + total_productos
        
    except:
        carrito_items = []
        cursos_carrito = []
        productos_carrito = []
        total_cursos = 0
        total_productos = 0
        total_general = 0
    
    return render_template("cart/cart.html", 
                         carrito_items=carrito_items,
                         cursos_carrito=cursos_carrito,
                         productos_carrito=productos_carrito,
                         total_cursos=total_cursos,
                         total_productos=total_productos,
                         total_general=total_general)

@app.route("/add-to-cart/<curso_id>")
@login_required
def add_to_cart(curso_id):
    cursos = {
        "sostenibilidad-basica": {
            "nombre": "Curso Sostenibilidad Básica",
            "precio": 49.00,
            "imagen": "/static/img/curso-sostenibilidad.jpg"
        },
        "consumo-responsable": {
            "nombre": "Curso Consumo Responsable", 
            "precio": 79.00,
            "imagen": "/static/img/curso-consumo.jpg"
        },
        "energias-limpias": {
            "nombre": "Curso Energías Limpias",
            "precio": 129.00,
            "imagen": "/static/img/curso-energias.jpg"
        }
    }
    
    if curso_id in cursos:
        curso_info = cursos[curso_id]
        
        # Verificar si ya está en el carrito
        existing_item = db.carrito.find_one({
            "user_id": session['user_id'],
            "item_id": curso_id,
            "tipo": "curso"  # ← Añadir tipo
        })
        
        if not existing_item:
            db.carrito.insert_one({
                "user_id": session['user_id'],
                "item_id": curso_id,
                "tipo": "curso",  # ← Añadir tipo
                "nombre": curso_info["nombre"],
                "precio": curso_info["precio"],
                "imagen": curso_info["imagen"],
                "cantidad": 1,  # ← Los cursos siempre son 1
                "fecha_agregado": datetime.now()
            })
            flash(f"'{curso_info['nombre']}' agregado al carrito", "success")
        else:
            flash("Este curso ya está en tu carrito", "info")
    
    return redirect(request.referrer or url_for('index'))

@app.route("/remove-from-cart/<item_id>")
@login_required
def remove_from_cart(item_id):
    db.carrito.delete_one({
        "_id": ObjectId(item_id),
        "user_id": session['user_id']
    })
    flash("Item removido del carrito", "info")
    return redirect(url_for('cart'))

@app.route("/favorites")
@login_required
def favorites():
    try:
        # Obtener todos los favoritos (cursos y productos)
        favoritos = list(db.favoritos.find({"user_id": session['user_id']}))
        
        # Separar por tipo para la plantilla
        cursos_favoritos = [fav for fav in favoritos if fav.get('tipo') == 'curso']
        productos_favoritos = [fav for fav in favoritos if fav.get('tipo') == 'producto']
        
    except:
        favoritos = []
        cursos_favoritos = []
        productos_favoritos = []
    
    return render_template("favorites/favorites.html", 
                         favoritos=favoritos,
                         cursos_favoritos=cursos_favoritos,
                         productos_favoritos=productos_favoritos)

@app.route("/add-to-favorites/<curso_id>")
@login_required
def add_to_favorites(curso_id):
    cursos = {
        "sostenibilidad-basica": {
            "nombre": "Curso Sostenibilidad Básica",
            "precio": 49.00,
            "imagen": "/static/img/curso-sostenibilidad.jpg",
            "url": url_for('curso_sostenibilidad')
        },
        "consumo-responsable": {
            "nombre": "Curso consumo Responsable",
            "precio": 79.00, 
            "imagen": "/static/img/curso-consumo.jpg",
            "url": url_for('curso_consumo')
        },
        "energias-limpias": {
            "nombre": "Curso Energías Limpias",
            "precio": 129.00,
            "imagen": "/static/img/curso-energias.jpg",
            "url": url_for('curso_energias')
        }
    }
    
    if curso_id in cursos:
        curso_info = cursos[curso_id]
        
        existing_fav = db.favoritos.find_one({
            "user_id": session['user_id'],
            "item_id": curso_id,
            "tipo": "curso"  # ← Añadir tipo
        })
        
        if not existing_fav:
            db.favoritos.insert_one({
                "user_id": session['user_id'],
                "item_id": curso_id,
                "tipo": "curso",  # ← Añadir tipo
                "nombre": curso_info["nombre"],
                "precio": curso_info["precio"],
                "imagen": curso_info["imagen"],
                "url": curso_info["url"],
                "fecha_agregado": datetime.now()
            })
            flash(f"'{curso_info['nombre']}' agregado a favoritos", "success")
        else:
            flash("Este curso ya está en tus favoritos", "info")
    
    return redirect(request.referrer or url_for('index'))

@app.route("/remove-from-favorites/<item_id>")
@login_required
def remove_from_favorites(item_id):
    db.favoritos.delete_one({
        "_id": ObjectId(item_id),
        "user_id": session['user_id']
    })
    flash("Elemento removido de favoritos", "info")
    return redirect(url_for('favorites'))

@app.route("/payment-methods")
@login_required
def payment_methods():
    try:
        tarjetas = list(db.tarjetas.find({"user_id": session['user_id']}))
    except:
        tarjetas = []
    
    return render_template("payment/payment_methods.html", tarjetas=tarjetas)

@app.route("/add-payment-method", methods=["POST"])
@login_required
def add_payment_method():
    nombre_titular = request.form.get("nombre_titular", "").strip()
    numero_tarjeta = request.form.get("numero_tarjeta", "").strip()
    fecha_expiracion = request.form.get("fecha_expiracion", "").strip()
    cvv = request.form.get("cvv", "").strip()
    
    if not all([nombre_titular, numero_tarjeta, fecha_expiracion, cvv]):
        flash("Completa todos los campos", "danger")
        return redirect(url_for('payment_methods'))
    
    # Enmascarar número de tarjeta para seguridad
    numero_enmascarado = f"**** **** **** {numero_tarjeta[-4:]}"
    
    db.tarjetas.insert_one({
        "user_id": session['user_id'],
        "nombre_titular": nombre_titular,
        "numero_tarjeta": numero_enmascarado,
        "numero_completo": numero_tarjeta,  # En producción, esto debería estar encriptado
        "fecha_expiracion": fecha_expiracion,
        "tipo": "Visa" if numero_tarjeta.startswith('4') else "Mastercard",
        "fecha_agregada": datetime.now()
    })
    
    flash("Tarjeta agregada exitosamente", "success")
    return redirect(url_for('payment_methods'))

@app.route("/remove-payment-method/<card_id>")
@login_required
def remove_payment_method(card_id):
    db.tarjetas.delete_one({
        "_id": ObjectId(card_id),
        "user_id": session['user_id']
    })
    flash("Tarjeta removida", "info")
    return redirect(url_for('payment_methods'))

# ===== NUEVO SISTEMA DE CHECKOUT =====

@app.route("/checkout")
@login_required
def checkout():
    try:
        carrito = list(db.carrito.find({"user_id": session['user_id']}))
        tarjetas = list(db.tarjetas.find({"user_id": session['user_id']}))
        total = sum(item['precio'] for item in carrito)
        
        if not carrito:
            flash("Tu carrito está vacío", "warning")
            return redirect(url_for('cart'))
            
    except Exception as e:
        carrito = []
        tarjetas = []
        total = 0
        flash(f"Error al cargar el checkout: {e}", "danger")
    
    return render_template("cart/checkout.html", carrito=carrito, tarjetas=tarjetas, total=total)

@app.route("/process-payment", methods=["POST"])
@login_required
def process_payment():
    try:
        carrito = list(db.carrito.find({"user_id": session['user_id']}))
        if not carrito:
            flash("Tu carrito está vacío", "warning")
            return redirect(url_for('cart'))
        
        total = sum(item['precio'] for item in carrito)
        tarjeta_id = request.form.get("tarjeta_id")
        
        if not tarjeta_id:
            flash("Selecciona un método de pago", "danger")
            return redirect(url_for('checkout'))
        
        # Verificar que la tarjeta pertenece al usuario
        tarjeta = db.tarjetas.find_one({
            "_id": ObjectId(tarjeta_id),
            "user_id": session['user_id']
        })
        
        if not tarjeta:
            flash("Método de pago no válido", "danger")
            return redirect(url_for('checkout'))
        
        # Crear orden de compra
        orden_id = db.ordenes.insert_one({
            "user_id": session['user_id'],
            "items": carrito,
            "total": total,
            "tarjeta_usada": tarjeta['numero_tarjeta'],
            "estado": "completado",
            "fecha_compra": datetime.now()
        }).inserted_id
        
        # Vaciar carrito
        db.carrito.delete_many({"user_id": session['user_id']})
        
        # Redirigir a página de confirmación
        return redirect(url_for('order_confirmation', order_id=orden_id))
        
    except Exception as e:
        flash(f"Error en el proceso de pago: {e}", "danger")
        return redirect(url_for('checkout'))

@app.route("/order-confirmation/<order_id>")
@login_required
def order_confirmation(order_id):
    try:
        orden = db.ordenes.find_one({
            "_id": ObjectId(order_id),
            "user_id": session['user_id']
        })
        
        if not orden:
            flash("Orden no encontrada", "danger")
            return redirect(url_for('index'))
            
    except:
        orden = None
        flash("Error al cargar la confirmación", "danger")
        return redirect(url_for('index'))
    
    return render_template("cart/order_confirmation.html", orden=orden)

# ===== RUTAS PARA WEBINARS =====

@app.route("/webinars")
@login_required
def webinars_index():
    try:
        webinars = list(db.webinars.find({
            "fecha_hora": {"$gte": datetime.now()}
        }).sort("fecha_hora", 1))
        
        # Obtener webinars en los que el usuario está registrado
        registros_usuario = list(db.registros_webinar.find({
            "user_id": session['user_id']
        }))
        webinars_registrados = [reg['webinar_id'] for reg in registros_usuario]
        
    except Exception as e:
        webinars = []
        webinars_registrados = []
        flash(f"Error al cargar webinars: {e}", "danger")
    
    return render_template("webinars/webinars.html", 
                         webinars=webinars, 
                         webinars_registrados=webinars_registrados)

@app.route("/webinar/<webinar_id>")
@login_required
def webinar_detail(webinar_id):
    try:
        webinar = db.webinars.find_one({"_id": ObjectId(webinar_id)})
        if not webinar:
            flash("Webinar no encontrado", "danger")
            return redirect(url_for('webinars_index'))
        
        # Verificar si el usuario está registrado
        registro = db.registros_webinar.find_one({
            "user_id": session['user_id'],
            "webinar_id": webinar_id
        })
        
        # Obtener información del experto
        experto = db.expertos.find_one({"_id": ObjectId(webinar['experto_id'])})
        
    except Exception as e:
        flash(f"Error al cargar el webinar: {e}", "danger")
        return redirect(url_for('webinars_index'))
    
    return render_template("webinars/webinar_detail.html", 
                         webinar=webinar, 
                         experto=experto,
                         registrado=bool(registro))

@app.route("/register-webinar/<webinar_id>")
@login_required
def register_webinar(webinar_id):
    try:
        webinar = db.webinars.find_one({"_id": ObjectId(webinar_id)})
        if not webinar:
            flash("Webinar no encontrado", "danger")
            return redirect(url_for('webinars_index'))
        
        # Verificar si ya está registrado
        existing_reg = db.registros_webinar.find_one({
            "user_id": session['user_id'],
            "webinar_id": webinar_id
        })
        
        if existing_reg:
            flash("Ya estás registrado en este webinar", "info")
            return redirect(url_for('webinar_detail', webinar_id=webinar_id))
        
        # Verificar cupos disponibles
        if webinar.get('cupos_disponibles', 0) <= 0:
            flash("Lo sentimos, no hay cupos disponibles para este webinar", "warning")
            return redirect(url_for('webinar_detail', webinar_id=webinar_id))
        
        # Registrar usuario
        db.registros_webinar.insert_one({
            "user_id": session['user_id'],
            "webinar_id": webinar_id,
            "fecha_registro": datetime.now(),
            "estado": "confirmado"
        })
        
        # Actualizar cupos disponibles
        db.webinars.update_one(
            {"_id": ObjectId(webinar_id)},
            {"$inc": {"cupos_disponibles": -1}}
        )
        
        flash(f"¡Te has registrado exitosamente al webinar '{webinar['titulo']}'!", "success")
        
    except Exception as e:
        flash(f"Error al registrar en el webinar: {e}", "danger")
    
    return redirect(url_for('webinar_detail', webinar_id=webinar_id))

@app.route("/my-webinars")
@login_required
def my_webinars():
    try:
        # Obtener webinars del usuario
        registros = list(db.registros_webinar.find({
            "user_id": session['user_id']
        }))
        
        webinars = []
        for registro in registros:
            webinar = db.webinars.find_one({"_id": ObjectId(registro['webinar_id'])})
            if webinar:
                webinars.append({
                    **webinar,
                    'fecha_registro': registro['fecha_registro'],
                    'estado_registro': registro['estado']
                })
        
    except Exception as e:
        webinars = []
        flash(f"Error al cargar tus webinars: {e}", "danger")
    
    # CORRECCIÓN: Pasar la fecha actual a la plantilla
    ahora = datetime.now()
    
    return render_template("webinars/my_webinars.html", 
                         webinars=webinars,
                         ahora=ahora)  # ← Añade esta línea

@app.route("/cancel-webinar-registration/<webinar_id>")
@login_required
def cancel_webinar_registration(webinar_id):
    try:
        # Eliminar registro
        result = db.registros_webinar.delete_one({
            "user_id": session['user_id'],
            "webinar_id": webinar_id
        })
        
        if result.deleted_count > 0:
            # Liberar cupo
            db.webinars.update_one(
                {"_id": ObjectId(webinar_id)},
                {"$inc": {"cupos_disponibles": 1}}
            )
            flash("Registro al webinar cancelado exitosamente", "success")
        else:
            flash("No se encontró tu registro para este webinar", "warning")
            
    except Exception as e:
        flash(f"Error al cancelar el registro: {e}", "danger")
    
    return redirect(url_for('my_webinars'))

# Ruta para poblar datos de ejemplo (solo en desarrollo)
@app.route("/populate-webinars")
def populate_webinars():
    if not app.debug:
        flash("Esta función solo está disponible en modo desarrollo", "danger")
        return redirect(url_for('index'))
    
    try:
        # Crear expertos de ejemplo
        expertos = [
            {
                "nombre": "Dra. María González",
                "especialidad": "Sostenibilidad Corporativa",
                "biografia": "PhD en Ciencias Ambientales con 15 años de experiencia en consultoría de sostenibilidad para empresas Fortune 500.",
                "imagen": "/static/img/experto1.jpg",
                "linkedin": "https://linkedin.com"
            },
            {
                "nombre": "Ing. Carlos Lopez",
                "especialidad": "Energías Renovables", 
                "biografia": "Ingeniero civil especializado en proyectos de energía solar y eólica. Ha liderado más de 50 proyectos sostenibles.",
                "imagen": "/static/img/experto2.png",
                "linkedin": "https://linkedin.com"
            },
            {
                "nombre": "Lic. Andrea Martínez",
                "especialidad": "Economía Circular",
                "biografia": "Especialista en modelos de negocio circulares y reducción de residuos. Consultora para gobiernos y ONGs.",
                "imagen": "/static/img/experto3.jpg", 
                "linkedin": "https://linkedin.com"
            }
        ]
        
        # Insertar expertos
        expertos_ids = []
        for experto in expertos:
            result = db.expertos.insert_one(experto)
            expertos_ids.append(result.inserted_id)
        
        # Crear webinars de ejemplo
        webinars = [
            {
                "titulo": "Transición Energética: Oportunidades y Desafíos",
                "descripcion": "Un análisis profundo sobre la transición hacia energías limpias y las oportunidades de negocio que presenta.",
                "fecha_hora": datetime.now() + timedelta(days=7),
                "duracion": 90,
                "formato": "En vivo",
                "precio": 0.00,
                "cupos_disponibles": 100,
                "cupos_totales": 100,
                "categoria": "Energías Limpias",
                "nivel": "Intermedio",
                "experto_id": expertos_ids[1],
                "imagen": "/static/img/webinar-energia.jpg",
                "enlace_zoom": "https://zoom.com",
                "requisitos": ["Conocimientos básicos de sostenibilidad", "Conexión a internet estable"],
                "materiales_incluidos": ["Presentación PDF", "Grabación del webinar", "Certificado de participación"]
            },
            {
                "titulo": "Economía Circular para Emprendedores",
                "descripcion": "Aprende cómo implementar principios de economía circular en tu emprendimiento y crear valor sostenible.",
                "fecha_hora": datetime.now() + timedelta(days=14),
                "duracion": 120,
                "formato": "En vivo + Q&A",
                "precio": 0.00,
                "cupos_disponibles": 75,
                "cupos_totales": 75,
                "categoria": "Economía Circular", 
                "nivel": "Principiante",
                "experto_id": expertos_ids[2],
                "imagen": "/static/img/webinar-economia.jpg",
                "enlace_zoom": "https://zoom.com",
                "requisitos": ["Interés en emprendimiento sostenible"],
                "materiales_incluidos": ["Plantillas de negocio", "Grabación del webinar", "Certificado de participación"]
            },
            {
                "titulo": "ESG: El Nuevo Paradigma Empresarial",
                "descripcion": "Descubre cómo las métricas ESG están transformando la forma de hacer negocios y cómo preparar tu empresa.",
                "fecha_hora": datetime.now() + timedelta(days=21),
                "duracion": 90,
                "formato": "En vivo",
                "precio": 0.00,
                "cupos_disponibles": 50,
                "cupos_totales": 50,
                "categoria": "Sostenibilidad Corporativa",
                "nivel": "Avanzado",
                "experto_id": expertos_ids[0],
                "imagen": "/static/img/webinar-esg.jpg",
                "enlace_zoom": "https://zoom.com",
                "requisitos": ["Experiencia en gestión empresarial", "Conocimientos de sostenibilidad"],
                "materiales_incluidos": ["Reporte ESG ejemplo", "Grabación del webinar", "Certificado de participación"]
            }
        ]
        
        # Insertar webinars
        for webinar in webinars:
            db.webinars.insert_one(webinar)
        
        flash("Datos de webinars creados exitosamente", "success")
        
    except Exception as e:
        flash(f"Error al crear datos de ejemplo: {e}", "danger")
    
    return redirect(url_for('webinars_index'))

# ===== RUTAS PARA E-COMMERCE DE PRODUCTOS =====

@app.route("/tienda")
@login_required
def tienda():
    try:
        # CONSULTA CORREGIDA - Obtener productos activos
        productos = list(db.productos.find({"estado": "activo"}))
        
        # Obtener categorías únicas para los filtros
        categorias = db.productos.distinct("categoria", {"estado": "activo"})
        
    except Exception as e:
        productos = []
        categorias = []
        flash(f"Error al cargar productos: {e}", "danger")
    
    return render_template("tienda/tienda.html", 
                         productos=productos, 
                         categorias=categorias)

@app.route("/producto/<producto_id>")
@login_required
def producto_detail(producto_id):
    try:
        producto = db.productos.find_one({"_id": ObjectId(producto_id)})
        if not producto:
            flash("Producto no encontrado", "danger")
            return redirect(url_for('tienda'))
            
        # Productos relacionados
        productos_relacionados = list(db.productos.find({
            "categoria": producto["categoria"],
            "_id": {"$ne": ObjectId(producto_id)},
            "estado": "activo"
        }).limit(4))
        
    except Exception as e:
        flash(f"Error al cargar el producto: {e}", "danger")
        return redirect(url_for('tienda'))
    
    return render_template("tienda/producto_detail.html", 
                         producto=producto,
                         productos_relacionados=productos_relacionados)

@app.route("/add-to-cart-producto/<producto_id>")
@login_required
def add_to_cart_producto(producto_id):
    try:
        producto = db.productos.find_one({"_id": ObjectId(producto_id)})
        if not producto:
            flash("Producto no encontrado", "danger")
            return redirect(url_for('tienda'))
        
        # Verificar stock
        if producto.get('stock', 0) <= 0:
            flash("Lo sentimos, este producto está agotado", "warning")
            return redirect(url_for('producto_detail', producto_id=producto_id))
        
        # Verificar si ya está en el carrito
        existing_item = db.carrito.find_one({  # ← Cambiar a la misma colección
            "user_id": session['user_id'],
            "item_id": producto_id,
            "tipo": "producto"  # ← Añadir tipo
        })
        
        if existing_item:
            # Incrementar cantidad
            db.carrito.update_one(
                {"_id": existing_item["_id"]},
                {"$inc": {"cantidad": 1}}
            )
            flash(f"Se agregó otra unidad de '{producto['nombre']}' al carrito", "info")
        else:
            # Agregar nuevo item al carrito
            db.carrito.insert_one({  # ← Cambiar a la misma colección
                "user_id": session['user_id'],
                "item_id": producto_id,
                "tipo": "producto",  # ← Añadir tipo
                "nombre": producto["nombre"],
                "precio": producto["precio"],
                "imagen": producto["imagen"],
                "categoria": producto["categoria"],
                "cantidad": 1,
                "fecha_agregado": datetime.now()
            })
            flash(f"'{producto['nombre']}' agregado al carrito", "success")
    
    except Exception as e:
        flash(f"Error al agregar al carrito: {e}", "danger")
    
    return redirect(request.referrer or url_for('tienda'))

@app.route("/update-cart-item/<item_id>", methods=["POST"])
@login_required
def update_cart_item(item_id):
    try:
        cantidad = int(request.form.get("cantidad", 1))
        
        if cantidad <= 0:
            # Eliminar item si la cantidad es 0 o menos
            db.carrito_productos.delete_one({
                "_id": ObjectId(item_id),
                "user_id": session['user_id']
            })
            flash("Producto removido del carrito", "info")
        else:
            # Actualizar cantidad
            db.carrito_productos.update_one(
                {
                    "_id": ObjectId(item_id),
                    "user_id": session['user_id']
                },
                {"$set": {"cantidad": cantidad}}
            )
            flash("Carrito actualizado", "success")
            
    except Exception as e:
        flash(f"Error al actualizar el carrito: {e}", "danger")
    
    return redirect(url_for('cart_productos'))

@app.route("/remove-from-cart-producto/<item_id>")
@login_required
def remove_from_cart_producto(item_id):
    try:
        db.carrito_productos.delete_one({
            "_id": ObjectId(item_id),
            "user_id": session['user_id']
        })
        flash("Producto removido del carrito", "info")
    except Exception as e:
        flash(f"Error al remover del carrito: {e}", "danger")
    
    return redirect(url_for('cart_productos'))

@app.route("/cart-productos")
@login_required
def cart_productos():
    # REDIRECCIÓN AL CARRITO UNIFICADO
    return redirect(url_for('cart'))
    try:
        carrito = list(db.carrito_productos.find({
            "user_id": session['user_id'],
            "estado": "activo"
        }))
        
        # Calcular totales
        subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
        envio = 50.00 if subtotal > 0 else 0  # Costo de envío fijo
        total = subtotal + envio
        
    except Exception as e:
        carrito = []
        subtotal = 0
        envio = 0
        total = 0
        flash(f"Error al cargar el carrito: {e}", "danger")
    
    return render_template("tienda/cart_productos.html", 
                         carrito=carrito, 
                         subtotal=subtotal,
                         envio=envio,
                         total=total)

@app.route("/checkout-productos")
@login_required
def checkout_productos():
    try:
        carrito = list(db.carrito_productos.find({
            "user_id": session['user_id'],
            "estado": "activo"
        }))
        
        if not carrito:
            flash("Tu carrito está vacío", "warning")
            return redirect(url_for('cart_productos'))
        
        # Obtener dirección del usuario
        direccion = db.direcciones.find_one({
            "user_id": session['user_id'],
            "principal": True
        })
        
        tarjetas = list(db.tarjetas.find({"user_id": session['user_id']}))
        
        # Calcular totales
        subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
        envio = 50.00 if subtotal > 0 else 0
        total = subtotal + envio
        
    except Exception as e:
        flash(f"Error al cargar checkout: {e}", "danger")
        return redirect(url_for('cart_productos'))
    
    return render_template("tienda/checkout_productos.html",
                         carrito=carrito,
                         direccion=direccion,
                         tarjetas=tarjetas,
                         subtotal=subtotal,
                         envio=envio,
                         total=total)

@app.route("/add-direccion", methods=["POST"])
@login_required
def add_direccion():
    try:
        # Marcar otras direcciones como no principales
        db.direcciones.update_many(
            {"user_id": session['user_id']},
            {"$set": {"principal": False}}
        )
        
        # Insertar nueva dirección principal
        db.direcciones.insert_one({
            "user_id": session['user_id'],
            "nombre_completo": request.form.get("nombre_completo", "").strip(),
            "calle": request.form.get("calle", "").strip(),
            "numero_exterior": request.form.get("numero_exterior", "").strip(),
            "numero_interior": request.form.get("numero_interior", "").strip(),
            "colonia": request.form.get("colonia", "").strip(),
            "ciudad": request.form.get("ciudad", "").strip(),
            "estado": request.form.get("estado", "").strip(),
            "codigo_postal": request.form.get("codigo_postal", "").strip(),
            "telefono": request.form.get("telefono", "").strip(),
            "instrucciones": request.form.get("instrucciones", "").strip(),
            "principal": True,
            "fecha_creacion": datetime.now()
        })
        
        flash("Dirección guardada exitosamente", "success")
        
    except Exception as e:
        flash(f"Error al guardar la dirección: {e}", "danger")
    
    return redirect(url_for('checkout_productos'))

@app.route("/process-pedido", methods=["POST"])
@login_required
def process_pedido():
    try:
        carrito = list(db.carrito_productos.find({
            "user_id": session['user_id'],
            "estado": "activo"
        }))
        
        if not carrito:
            flash("Tu carrito está vacío", "warning")
            return redirect(url_for('cart_productos'))
        
        # Verificar stock y disponibilidad
        for item in carrito:
            producto = db.productos.find_one({"_id": ObjectId(item['producto_id'])})
            if not producto or producto.get('stock', 0) < item['cantidad']:
                flash(f"Lo sentimos, '{item['nombre']}' no tiene suficiente stock", "danger")
                return redirect(url_for('cart_productos'))
        
        # Obtener datos del formulario
        tarjeta_id = request.form.get("tarjeta_id")
        direccion_id = request.form.get("direccion_id")
        
        if not tarjeta_id or not direccion_id:
            flash("Completa todos los campos requeridos", "danger")
            return redirect(url_for('checkout_productos'))
        
        # Verificar tarjeta
        tarjeta = db.tarjetas.find_one({
            "_id": ObjectId(tarjeta_id),
            "user_id": session['user_id']
        })
        
        if not tarjeta:
            flash("Método de pago no válido", "danger")
            return redirect(url_for('checkout_productos'))
        
        # Verificar dirección
        direccion = db.direcciones.find_one({
            "_id": ObjectId(direccion_id),
            "user_id": session['user_id']
        })
        
        if not direccion:
            flash("Dirección no válida", "danger")
            return redirect(url_for('checkout_productos'))
        
        # Calcular totales
        subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
        envio = 50.00 if subtotal > 0 else 0
        total = subtotal + envio
        
        # Crear pedido
        pedido_id = db.pedidos.insert_one({
            "user_id": session['user_id'],
            "items": carrito,
            "subtotal": subtotal,
            "costo_envio": envio,
            "total": total,
            "direccion_entrega": direccion,
            "metodo_pago": {
                "tipo": tarjeta['tipo'],
                "ultimos_digitos": tarjeta['numero_tarjeta'][-4:]
            },
            "estado": "confirmado",
            "fecha_pedido": datetime.now(),
            "numero_seguimiento": f"ECO{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }).inserted_id
        
        # Actualizar stock y marcar productos como vendidos
        for item in carrito:
            # Reducir stock
            db.productos.update_one(
                {"_id": ObjectId(item['producto_id'])},
                {"$inc": {"stock": -item['cantidad']}}
            )
            
            # Registrar venta en el producto
            db.ventas_productos.insert_one({
                "producto_id": item['producto_id'],
                "user_id": session['user_id'],
                "pedido_id": pedido_id,
                "cantidad": item['cantidad'],
                "precio_unitario": item['precio'],
                "total": item['precio'] * item['cantidad'],
                "fecha_venta": datetime.now(),
                "direccion_entrega": direccion
            })
        
        # Vaciar carrito
        db.carrito_productos.delete_many({
            "user_id": session['user_id'],
            "estado": "activo"
        })
        
        # Redirigir a confirmación
        return redirect(url_for('order_confirmation_productos', pedido_id=pedido_id))
        
    except Exception as e:
        flash(f"Error al procesar el pedido: {e}", "danger")
        return redirect(url_for('checkout_productos'))

@app.route("/order-confirmation-productos/<pedido_id>")
@login_required
def order_confirmation_productos(pedido_id):
    try:
        pedido = db.pedidos.find_one({
            "_id": ObjectId(pedido_id),
            "user_id": session['user_id']
        })
        
        if not pedido:
            flash("Pedido no encontrado", "danger")
            return redirect(url_for('tienda'))
            
    except Exception as e:
        flash(f"Error al cargar la confirmación: {e}", "danger")
        return redirect(url_for('tienda'))
    
    return render_template("tienda/order_confirmation_productos.html", pedido=pedido)

@app.route("/mis-pedidos")
@login_required
def mis_pedidos():
    try:
        pedidos = list(db.pedidos.find({
            "user_id": session['user_id']
        }).sort("fecha_pedido", -1))
        
    except Exception as e:
        pedidos = []
        flash(f"Error al cargar tus pedidos: {e}", "danger")
    
    return render_template("tienda/mis_pedidos.html", pedidos=pedidos)

@app.route("/add-to-favorites-producto/<producto_id>")
@login_required
def add_to_favorites_producto(producto_id):
    try:
        producto = db.productos.find_one({"_id": ObjectId(producto_id)})
        if not producto:
            flash("Producto no encontrado", "danger")
            return redirect(url_for('tienda'))
        
        existing_fav = db.favoritos.find_one({  # ← Cambiar a la misma colección
            "user_id": session['user_id'],
            "item_id": producto_id,
            "tipo": "producto"  # ← Añadir tipo
        })
        
        if not existing_fav:
            db.favoritos.insert_one({  # ← Cambiar a la misma colección
                "user_id": session['user_id'],
                "item_id": producto_id,
                "tipo": "producto",  # ← Añadir tipo
                "nombre": producto["nombre"],
                "precio": producto["precio"],
                "imagen": producto["imagen"],
                "categoria": producto["categoria"],
                "fecha_agregado": datetime.now()
            })
            flash(f"'{producto['nombre']}' agregado a favoritos", "success")
        else:
            flash("Este producto ya está en tus favoritos", "info")
    
    except Exception as e:
        flash(f"Error al agregar a favoritos: {e}", "danger")
    
    return redirect(request.referrer or url_for('tienda'))

@app.route("/favorites")
@login_required
def favorites_productos():
    try:
        favoritos = list(db.favoritos_productos.find({"user_id": session['user_id']}))
    except:
        favoritos = []
    
    # Cambia esta línea para usar una plantilla existente:
    return render_template("favorites/favorites.html", favoritos=favoritos)

# ===== RUTAS PARA GESTIÓN DE PRODUCTOS (Vendedor) =====
@app.context_processor
def inject_cart_count():
    def get_cart_count():
        if 'user_id' in session and db is not None:
            try:
                return db.carrito.count_documents({
                    "user_id": session['user_id']
                })
            except:
                return 0
        return 0
    return dict(cart_count=get_cart_count)
@app.route("/productos/ventas")
@login_required
def productos_ventas():
    try:
        # Obtener productos del usuario (vendedor)
        productos = list(db.productos.find({"user_id": session['user_id']}))
        
        # Obtener ventas de cada producto y asegurar campos
        for producto in productos:
            ventas = list(db.ventas_productos.find({"producto_id": str(producto['_id'])}))
            producto['total_ventas'] = len(ventas)
            producto['ingresos_totales'] = sum(venta['total'] for venta in ventas)
            producto['detalles_ventas'] = ventas
            
            # ASEGURAR QUE EXISTA EL CAMPO STOCK
            if 'stock' not in producto:
                producto['stock'] = 0
            
    except Exception as e:
        productos = []
        flash(f"Error al cargar ventas: {e}", "danger")
    
    return render_template("productos/ventas.html", productos=productos)

@app.route("/producto/ventas-detalle/<producto_id>")
@login_required
def producto_ventas_detalle(producto_id):
    try:
        producto = db.productos.find_one({
            "_id": ObjectId(producto_id),
            "user_id": session['user_id']
        })
        
        if not producto:
            flash("Producto no encontrado", "danger")
            return redirect(url_for('productos_ventas'))
        
        ventas = list(db.ventas_productos.find({"producto_id": producto_id}))
        
        # Obtener información de compradores
        for venta in ventas:
            usuario = db.usuarios.find_one({"_id": ObjectId(venta['user_id'])})
            venta['usuario_info'] = usuario
        
    except Exception as e:
        ventas = []
        flash(f"Error al cargar detalles de ventas: {e}", "danger")
    
    return render_template("productos/ventas_detalle.html", 
                         producto=producto, 
                         ventas=ventas)

# Ruta para poblar productos de ejemplo
@app.route("/populate-productos-tienda")
def populate_productos_tienda():
    if not app.debug:
        flash("Esta función solo está disponible en modo desarrollo", "danger")
        return redirect(url_for('index'))
    
    try:
        productos_ejemplo = [
            {
                "nombre": "Kit Inicial Zero Waste",
                "descripcion": "Kit completo para comenzar tu transición hacia un estilo de vida sin residuos. Incluye 5 productos esenciales.",
                "precio": 45.00,
                "categoria": "Hogar",
                "stock": 50,
                "imagen": "/static/img/producto-zero-waste.jpg",
                "sostenibilidad": "Avanzado",
                "materiales": ["Bambú", "Algodón orgánico", "Acero inoxidable"],
                "caracteristicas": [
                    "100% libre de plástico",
                    "Materiales biodegradables",
                    "Empaque compostable"
                ],
                "user_id": session['user_id'],
                "estado": "activo",
                "fecha_creacion": datetime.now()
            },
            {
                "nombre": "Bicicleta Urbana Plegable Eco-Fold",
                "descripcion": "Bicicleta plegable ideal para ciudad, fabricada con 80% aluminio reciclado.",
                "precio": 299.00,
                "categoria": "Movilidad",
                "stock": 15,
                "imagen": "/static/img/producto-bicicleta.jpg",
                "sostenibilidad": "Premium",
                "materiales": ["Aluminio reciclado", "Acero", "Caucho natural"],
                "caracteristicas": [
                    "80% materiales reciclados",
                    "Sistema de plegado rápido",
                    "Diseño Atractivo"
                ],
                "user_id": session['user_id'],
                "estado": "activo",
                "fecha_creacion": datetime.now()
            },
            {
                "nombre": "Set Belleza Sólida Viajero",
                "descripcion": "Kit completo de belleza en formato sólido: shampoo, acondicionador, jabón facial y desodorante.",
                "precio": 28.50,
                "categoria": "Cuidado Personal",
                "stock": 100,
                "imagen": "/static/img/producto-belleza.jpg",
                "sostenibilidad": "Intermedio",
                "materiales": ["Ingredientes naturales", "Aceites esenciales"],
                "caracteristicas": [
                    "Ahorra 4 botellas de plástico",
                    "Ingredientes 100% naturales",
                    "Certificación cruelty-free"
                ],
                "user_id": session['user_id'],
                "estado": "activo",
                "fecha_creacion": datetime.now()
            }
        ]
        
        for producto in productos_ejemplo:
            db.productos.insert_one(producto)
        
        flash("Productos de ejemplo creados exitosamente", "success")
        
    except Exception as e:
        flash(f"Error al crear productos de ejemplo: {e}", "danger")
    
    return redirect(url_for('tienda'))

if __name__ == "__main__":
    app.run(debug=True)