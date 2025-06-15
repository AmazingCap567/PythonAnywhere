
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from db import conectar_bd

#importacion local
import webbrowser
import threading
import os



app = Flask(__name__)
app.secret_key = "clave_secreta"

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]
        try:
            conn = conectar_bd()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Usuarios WHERE nombre = ? AND contraseña = ?", (usuario, contraseña))
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

@app.route("/producto")
def producto():
    if "usuario" not in session:
        return redirect(url_for("login"))
    productos = [
        {"nombre": "Coca Cola", "cantidad": 20, "precio": 1.5, "descripcion": "2 litros", "iva": 0.18, "categoria": "bebidas"},
        {"nombre": "Pepsi", "cantidad": 10, "precio": 1.3, "descripcion": "1 litro", "iva": 0.16, "categoria": "bebidas"}
    ]
    return render_template("producto.html", productos=productos)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

#def local

def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    # Abrir el navegador automáticamente al iniciar la aplicación
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1, abrir_navegador).start()
    # Iniciar la aplicación Flask
    app.run(debug=True)
