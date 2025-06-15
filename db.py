
import pyodbc

def conectar_bd():
    conexion = pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=DESKTOP-Q3BJI3U;'  # Cambiar por el servidor real en producción
        'DATABASE=FERREMAX;'
        'Trusted_Connection=yes;'
    )
    return conexion
