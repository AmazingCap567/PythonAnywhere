from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_cors import CORS
from db import conectar_bd
import pyodbc
from datetime import datetime
import webbrowser
import threading
import os

app = Flask(__name__)
app.secret_key = "clave_secreta"

# Convertir fila a diccionario (1 resultado)
def dictfetchone(cursor):
    row = cursor.fetchone()
    if row:
        return dict(zip([column[0] for column in cursor.description], row))
    return None

# Convertir múltiples filas a lista de diccionarios
def dictfetchall(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

#############################################################
# Usuario
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contrasena = request.form["contrasena"]
        try:
            conn = conectar_bd()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Usuarios WHERE nombre = ? AND contrasena = ?", (usuario, contrasena))
            if cursor.fetchone():
                session["usuario"] = usuario
                return redirect(url_for("menu"))
            else:
                flash("Usuario o contraseña incorrectos")
        except Exception as e:
            flash("Error de conexión: " + str(e))
    return render_template("login.html")

@app.route("/menu")
def menu():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("menu.html")

#############################################################
# Búsqueda de clientes (CORREGIDA)
@app.route("/buscar_clientes")
def buscar_clientes():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    conn = conectar_bd()
    cursor = conn.cursor()
    sql = """
        SELECT id_cliente, nombre, apellidos, ruc, direccion, razon_social
        FROM clientes
        WHERE nombre LIKE ? OR apellidos LIKE ? OR ruc LIKE ?
    """
    like_query = f"%{query}%"
    cursor.execute(sql, (like_query, like_query, like_query))

    resultados = [
        {
            "id": row[0],
            "nombre": row[1],
            "apellidos": row[2],
            "ruc": row[3],
            "direccion": row[4],
            "razon_social": row[5]
        } for row in cursor.fetchall()
    ]
    return jsonify(resultados)

#############################################################
# Venta
@app.route("/venta", methods=["GET", "POST"])
def venta():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = conectar_bd()
    cursor = conn.cursor()

    carrito = session.get("carrito", [])
    cliente = None

    if request.method == "POST":
        if "buscar_cliente" in request.form:
            id_cliente = request.form.get("cod_cliente")
            cursor.execute("SELECT * FROM clientes WHERE id_cliente = ?", (id_cliente,))
            row = cursor.fetchone()
            if row:
                cliente = {
                    "id": row[0], "nombre": row[1], "apellidos": row[2],
                    "direccion": row[3], "ruc": row[4], "razon_social": row[5]
                }
            else:
                flash("Cliente no encontrado")

        elif "agregar" in request.form:
            producto_id = int(request.form["producto"])
            cantidad = int(request.form["cantidad"])
            precio_unitario = float(request.form["precio"])
            nombre = ""
            cursor.execute("SELECT nombre FROM productos WHERE id_producto = ?", (producto_id,))
            row = cursor.fetchone()
            if row:
                nombre = row[0]
            item = {
                "id_producto": producto_id,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "nombre": nombre,
                "subtotal": cantidad * precio_unitario
            }
            carrito.append(item)
            session["carrito"] = carrito
            return redirect(url_for("venta"))

        elif "confirmar" in request.form:
            if not carrito:
                flash("No hay productos en el carrito")
                return redirect(url_for("venta"))

            id_cliente = request.form.get("cod_cliente")
            id_usuario = 1  # fijo porque solo hay un usuario registrado
            total = sum(item["subtotal"] for item in carrito) * 1.18
            fecha_actual = datetime.now().strftime("%Y-%m-%d")

            cursor.execute("INSERT INTO ventas (fecha, total, id_usuario, id_cliente) VALUES (?, ?, ?, ?)",
                           (fecha_actual, total, id_usuario, id_cliente))
            cursor.execute("SELECT SCOPE_IDENTITY()")
            id_venta = cursor.fetchone()[0]

            for item in carrito:
                cursor.execute("""
                    INSERT INTO detalle_venta (id_venta, id_producto, cantidad, precio_unitario)
                    VALUES (?, ?, ?, ?)
                """, (id_venta, item["id_producto"], item["cantidad"], item["precio_unitario"]))

            conn.commit()
            session["carrito"] = []
            flash("Venta registrada con éxito")
            return redirect(url_for("venta"))

        elif "registrar_cliente" in request.form:
            nombre = request.form.get('nombre', '').strip()
            apellidos = request.form.get('apellidos', '').strip()
            ruc = request.form.get('ruc', '').strip()

            if not nombre or not apellidos or not ruc:
                flash("⚠️ Nombre, Apellidos y RUC son obligatorios.")
                return redirect(url_for("venta"))
            
            direccion = request.form.get('direccion') or None
            razon_social = request.form.get('razon_social') or None
            telefono = request.form.get('telefono') or None
            correo = request.form.get('correo') or None
            
            cursor.execute("""
                INSERT INTO clientes (nombre, apellidos, ruc, direccion, razon_social, telefono, correo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nombre, apellidos, ruc, direccion, razon_social, telefono, correo))
            conn.commit()

            cursor.execute("SELECT TOP 1 * FROM clientes WHERE ruc = ? ORDER BY id_cliente DESC", ruc)
            row = cursor.fetchone()
            if row:
                cliente = {
                    "id": row[0],
                    "nombre": row[1],
                    "apellidos": row[2],
                    "ruc": row[3],
                    "direccion": row[4],
                    "razon_social": row[5]
                }
            flash("✅ Cliente registrado correctamente.")

    cursor.execute("SELECT id_producto, nombre, '', precio_unitario FROM productos")
    productos = cursor.fetchall()
    conn.close()

    return render_template("venta.html", productos=productos, carrito=carrito, cliente=cliente)

#############################################################
@app.route("/agregar_cliente")
def agregar_cliente():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("Base_de_datos/Clientes/AgregarClientes.html")

@app.route("/modificar_cliente", methods=["GET", "POST"])
def modificar_cliente():
    cliente = None
    if request.method == "POST":
        nombre = request.form["nombre"]
        apellidos = request.form["apellidos"]

        conn = conectar_bd()
        cursor = conn.cursor()

        if 'razon' not in request.form:
            cursor.execute('SELECT * FROM clientes WHERE nombre = ? AND apellidos = ?', (nombre, apellidos))
            cliente = dictfetchone(cursor)
        else:
            cursor.execute('''
                UPDATE clientes SET
                    razon_social = ?,
                    ruc = ?,
                    direccion = ?,
                    telefono = ?,
                    correo = ?
                WHERE nombre = ? AND apellidos = ?
            ''', (
                request.form['razon'],
                request.form['ruc'],
                request.form['direccion'],
                request.form['telefono'],
                request.form['correo'],
                nombre,
                apellidos
            ))
            conn.commit()
            flash("✅ Cliente actualizado correctamente.")
            return redirect(url_for("modificar_cliente"))

        cursor.close()
        conn.close()

    return render_template("Base_de_datos/Clientes/ModificarClientes.html", cliente=cliente)

#############################################################
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1, abrir_navegador).start()
    app.run(debug=True)
