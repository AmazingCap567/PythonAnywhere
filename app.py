from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_cors import CORS
from db import conectar_bd
from datetime import datetime
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
            cursor.execute("SELECT * FROM Usuarios WHERE nombre = %s AND contrasena = %s", (usuario, contrasena))
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
        WHERE nombre LIKE %s OR apellidos LIKE %s OR ruc LIKE %s
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
            cursor.execute("SELECT * FROM clientes WHERE id_cliente = %s", (id_cliente,))
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
            cursor.execute("SELECT nombre FROM productos WHERE id_producto = %s", (producto_id,))
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

            cursor.execute("INSERT INTO ventas (fecha, total, id_usuario, id_cliente) VALUES (%s, %s, %s, %s)",
                           (fecha_actual, total, id_usuario, id_cliente))
            id_venta = cursor.lastrowid

            for item in carrito:
                cursor.execute("""
                    INSERT INTO detalle_venta (id_venta, id_producto, cantidad, precio_unitario)
                    VALUES (%s, %s, %s, %s)
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
                flash("\u26a0\ufe0f Nombre, Apellidos y RUC son obligatorios.")
                return redirect(url_for("venta"))
            
            direccion = request.form.get('direccion') or None
            razon_social = request.form.get('razon_social') or None
            telefono = request.form.get('telefono') or None
            correo = request.form.get('correo') or None
            
            cursor.execute("""
                INSERT INTO clientes (nombre, apellidos, ruc, direccion, razon_social, telefono, correo)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (nombre, apellidos, ruc, direccion, razon_social, telefono, correo))
            conn.commit()

            cursor.execute("SELECT * FROM clientes WHERE ruc = %s ORDER BY id_cliente DESC LIMIT 1", (ruc,))
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
            flash("\u2705 Cliente registrado correctamente.")

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
            cursor.execute('SELECT * FROM clientes WHERE nombre = %s AND apellidos = %s', (nombre, apellidos))
            cliente = dictfetchone(cursor)
        else:
            cursor.execute('''
                UPDATE clientes SET
                    razon_social = %s,
                    ruc = %s,
                    direccion = %s,
                    telefono = %s,
                    correo = %s
                WHERE nombre = %s AND apellidos = %s
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
            flash("\u2705 Cliente actualizado correctamente.")
            return redirect(url_for("modificar_cliente"))

        cursor.close()
        conn.close()

    return render_template("Base_de_datos/Clientes/ModificarClientes.html", cliente=cliente)

#############################################################
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
