import mysql.connector

def conectar_bd():
    return mysql.connector.connect(
        host='NewProyect567.mysql.pythonanywhere-services.com',
        user='NewProyect567',
        password='FNAFa_121',
        database='NewProyect567$RETROLAX567'
    )
