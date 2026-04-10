import os
import re
import pyodbc
from datetime import datetime


# Conexión a la base de datos
def conectar_bd():
    conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};' \
    'SERVER=10.2.214.69;' \
    'DATABASE=DB_base_conocimiento_2;' \
    'UID=C3;' \
    'Encrypt=yes;' \
    'TrustServerCertificate=yes;' \
    'PWD=R3s1l13nc14C0d1g02024.')
    return conn


# Función para analizar un archivo RPG
def analizar_rpg(ruta_archivo):
    archivos = []
    colas = []
    llamadas = []

    nombre_archivo_rpg = os.path.basename(ruta_archivo)

    with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
        for linea in f:
            linea_original = linea.rstrip("\n")
            linea_limpia = linea_original.strip()

            # Detectar archivos RPG (líneas F)
            if linea_limpia.startswith("F"):
                match = re.match(r"F([A-Z0-9_]+)", linea_limpia, re.IGNORECASE)
                if match:
                    nombre_objeto = match.group(1)
                    archivos.append({
                        "archivo_rpg": nombre_archivo_rpg,
                        "nombre_objeto": nombre_objeto
                    })

            # Detectar colas
            if "QRCVDTAQ" in linea_limpia.upper():
                colas.append({
                    "archivo_rpg": nombre_archivo_rpg,
                    "nombre_cola": "QRCVDTAQ",
                    "sentencia": linea_original.strip()
                })

            if "QSNDDTAQ" in linea_limpia.upper():
                colas.append({
                    "archivo_rpg": nombre_archivo_rpg,
                    "nombre_cola": "QSNDDTAQ",
                    "sentencia": linea_original.strip()
                })

            # Detectar llamadas CALL / CALLP
            if "CALL" in linea_limpia.upper():
                match = re.search(r"\bCALLP?\b\s+['\"]?([A-Z0-9_]+)['\"]?", linea_limpia, re.IGNORECASE)
                if match:
                    nombre_programa = match.group(1).upper()

                    # Evitar guardar colas también como llamadas normales
                    if nombre_programa not in ("QRCVDTAQ", "QSNDDTAQ"):
                        llamadas.append({
                            "archivo_rpg": nombre_archivo_rpg,
                            "nombre_programa": nombre_programa,
                            "sentencia": linea_original.strip()
                        })

    return {
        "archivo_rpg": nombre_archivo_rpg,
        "archivos": archivos,
        "colas": colas,
        "llamadas": llamadas
    }


# Funciones para insertar datos en la base de datos
def insertar_analisis(conn, fuente):
    cursor = conn.cursor()
    cursor.fast_executemany = True
    ahora = datetime.now()

    sql = """
    INSERT INTO rpg_analisis (fuente, fecha, hora)
    OUTPUT INSERTED.id_analisis
    VALUES (?, ?, ?)
    """

    cursor.execute(sql, fuente, ahora.date(), ahora.time())
    id_analisis = cursor.fetchone()[0]
    conn.commit()

    return id_analisis


# Funciones para insertar archivos, colas y llamadas en la base de datos
def insertar_archivos(conn, id_analisis, archivos):
    if not archivos:
        return

    cursor = conn.cursor()
    cursor.fast_executemany = True

    sql = """
    INSERT INTO dbo.rpg_archivos (id_analisis, archivo_rpg, nombre_objeto)
    VALUES (?, ?, ?)
    """

    data = [
        (id_analisis, item["archivo_rpg"], item["nombre_objeto"])
        for item in archivos
    ]

    cursor.executemany(sql, data)
    conn.commit()


# Función para insertar colas en la base de datos
def insertar_colas(conn, id_analisis, colas):
    if not colas:
        return

    cursor = conn.cursor()
    cursor.fast_executemany = True

    sql = """
    INSERT INTO dbo.rpg_colas (id_analisis, archivo_rpg, nombre_cola, sentencia)
    VALUES (?, ?, ?, ?)
    """

    data = [
        (
            id_analisis,
            item["archivo_rpg"],
            item["nombre_cola"],
            item["sentencia"]
        )
        for item in colas
    ]

    cursor.executemany(sql, data)
    conn.commit()


# Función para insertar llamadas en la base de datos
def insertar_llamadas(conn, id_analisis, llamadas):
    if not llamadas:
        return

    cursor = conn.cursor()
    cursor.fast_executemany = True
    
    sql = """
    INSERT INTO dbo.rpg_llamadas (id_analisis, archivo_rpg, nombre_programa, sentencia)
    VALUES (?, ?, ?, ?)
    """

    data = [
        (
            id_analisis,
            item["archivo_rpg"],
            item["nombre_programa"],
            item["sentencia"]
        )
        for item in llamadas
    ]

    cursor.executemany(sql, data)
    conn.commit()


# Función principal para procesar la carpeta de archivos RPG
def procesar_directorio(ruta_carpeta):
    conn = conectar_bd()

    try:
        id_analisis = insertar_analisis(conn, ruta_carpeta)
        print(f"Análisis creado con id: {id_analisis}")

        total_rpg = 0
        total_archivos = 0
        total_colas = 0
        total_llamadas = 0

        for archivo in os.listdir(ruta_carpeta):
            if archivo.lower().endswith(".rpg"):
                ruta_archivo = os.path.join(ruta_carpeta, archivo)
                print(f"Procesando archivo: {ruta_archivo}")

                resultado = analizar_rpg(ruta_archivo)

                insertar_archivos(conn, id_analisis, resultado["archivos"])
                insertar_colas(conn, id_analisis, resultado["colas"])
                insertar_llamadas(conn, id_analisis, resultado["llamadas"])

                total_rpg += 1
                total_archivos += len(resultado["archivos"])
                total_colas += len(resultado["colas"])
                total_llamadas += len(resultado["llamadas"])

        print("\n===== RESUMEN =====")
        print(f"Archivos RPG procesados: {total_rpg}")
        print(f"Archivos detectados en RPG: {total_archivos}")
        print(f"Colas detectadas: {total_colas}")
        print(f"Llamadas detectadas: {total_llamadas}")

    except Exception as e:
        print(f"Error durante el proceso: {e}")
        conn.rollback()
    finally:
        conn.close()