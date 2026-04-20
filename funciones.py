import os
import re
import pyodbc
import hashlib
from datetime import datetime


# Conexión a la base de datos
def conectar_bd():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 18 for SQL Server};'
        'SERVER=10.2.214.69;'
        'DATABASE=DB_base_conocimiento_2;'
        'UID=C3;'
        'Encrypt=yes;'
        'TrustServerCertificate=yes;'
        'PWD=R3s1l13nc14C0d1g02024.'
    )
    return conn


# =========================================================
# CONTROL DE DUPLICIDAD DE ARCHIVOS PROCESADOS
# =========================================================

def calcular_hash_archivo(ruta_archivo):
    sha256 = hashlib.sha256()

    with open(ruta_archivo, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            sha256.update(bloque)

    return sha256.hexdigest()


def archivo_ya_procesado(conn, hash_archivo):
    cursor = conn.cursor()

    sql = """
    SELECT 1
    FROM dbo.rpg_archivos_procesados
    WHERE hash_archivo = ?
    """

    cursor.execute(sql, (hash_archivo,))
    return cursor.fetchone() is not None


def registrar_archivo_procesado(conn, nombre_archivo, hash_archivo):
    cursor = conn.cursor()

    sql = """
    INSERT INTO dbo.rpg_archivos_procesados (nombre_archivo, hash_archivo, fecha_proceso)
    VALUES (?, ?, ?)
    """

    cursor.execute(sql, (nombre_archivo, hash_archivo, datetime.now()))
    conn.commit()


# =========================================================
# ANALISIS DEL ARCHIVO RPG
# =========================================================

def analizar_rpg(ruta_archivo):
    archivos = []
    colas = []
    llamadas = []

    nombre_archivo_rpg = os.path.basename(ruta_archivo)
    llamada_actual = None

    with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
        for numero_linea, linea in enumerate(f, start=1):
            linea_original = linea.rstrip("\n")
            linea_limpia = linea_original.strip()
            linea_upper = linea_limpia.upper()

            if not linea_limpia:
                continue

            # Ignorar comentarios simples
            if linea_limpia.startswith("*"):
                continue

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
            if "QRCVDTAQ" in linea_upper:
                colas.append({
                    "archivo_rpg": nombre_archivo_rpg,
                    "nombre_cola": "QRCVDTAQ",
                    "sentencia": linea_original.strip()
                })

            if "QSNDDTAQ" in linea_upper:
                colas.append({
                    "archivo_rpg": nombre_archivo_rpg,
                    "nombre_cola": "QSNDDTAQ",
                    "sentencia": linea_original.strip()
                })

            # Detectar CALL / CALLP
            match_call = re.search(
                r"\bCALLP?\b\s+['\"]?([A-Z0-9_]+)['\"]?",
                linea_limpia,
                re.IGNORECASE
            )

            if match_call:
                nombre_programa = match_call.group(1).upper()

                # Evitar guardar colas también como llamadas normales
                if nombre_programa in ("QRCVDTAQ", "QSNDDTAQ"):
                    if llamada_actual is not None:
                        llamadas.append(llamada_actual)

                    llamada_actual = {
                        "archivo_rpg": nombre_archivo_rpg,
                        "nombre_programa": nombre_programa,
                        "sentencia": linea_original.strip(),
                        "linea_call": numero_linea,
                        "parametros": []
                    }
                    continue

                if llamada_actual is not None:
                    llamadas.append(llamada_actual)

                llamada_actual = {
                    "archivo_rpg": nombre_archivo_rpg,
                    "nombre_programa": nombre_programa,
                    "sentencia": linea_original.strip(),
                    "linea_call": numero_linea,
                    "parametros": []
                }
                continue

            # Detectar PARM asociado a la llamada actual
            if llamada_actual is not None:
                match_parm = re.search(r"\bPARM\b", linea_limpia, re.IGNORECASE)

                if match_parm:
                    sentencia_param = linea_original.strip()

                    contenido = re.sub(
                        r"^.*?\bPARM\b",
                        "",
                        linea_limpia,
                        flags=re.IGNORECASE
                    ).strip()

                    partes = contenido.split()

                    nombre_parametro = None
                    valor_parametro = None

                    if len(partes) == 1:
                        nombre_parametro = partes[0]

                    elif len(partes) >= 2:
                        nombre_parametro = partes[0]
                        valor_parametro = partes[1]

                    # Guardar
                    llamada_actual["parametros"].append({
                        "orden": len(llamada_actual["parametros"]) + 1,
                        "nombre": nombre_parametro,
                        "valor": valor_parametro,
                        "sentencia": linea_original.strip(),
                        "linea_parametro": numero_linea
                    })
                    
                    continue

                # Si aparece otra línea distinta a PARM, cerramos llamada actual
                llamadas.append(llamada_actual)
                llamada_actual = None

        # Guardar la última llamada abierta
        if llamada_actual is not None:
            llamadas.append(llamada_actual)

    return {
        "archivo_rpg": nombre_archivo_rpg,
        "archivos": archivos,
        "colas": colas,
        "llamadas": llamadas
    }


# =========================================================
# INSERTS GENERALES
# =========================================================

def insertar_analisis(conn, fuente):
    cursor = conn.cursor()
    cursor.fast_executemany = True
    ahora = datetime.now()

    sql = """
    INSERT INTO dbo.rpg_analisis (fuente, fecha, hora)
    OUTPUT INSERTED.id_analisis
    VALUES (?, ?, ?)
    """

    cursor.execute(sql, fuente, ahora.date(), ahora.time())
    id_analisis = cursor.fetchone()[0]
    conn.commit()

    return id_analisis


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


# =========================================================
# INSERTS DE LLAMADAS Y PARAMETROS
# =========================================================

def insertar_llamada(conn, id_analisis, llamada):
    cursor = conn.cursor()

    sql = """
    INSERT INTO dbo.rpg_llamadas
    (id_analisis, archivo_rpg, nombre_programa, sentencia)
    OUTPUT INSERTED.id_llamada
    VALUES (?, ?, ?, ?)
    """

    cursor.execute(
        sql,
        (
            id_analisis,
            llamada["archivo_rpg"],
            llamada["nombre_programa"],
            llamada["sentencia"]
        )
    )

    id_llamada = cursor.fetchone()[0]
    conn.commit()
    return id_llamada


def insertar_parametros_llamada(conn, id_llamada, parametros):
    if not parametros:
        return

    cursor = conn.cursor()
    cursor.fast_executemany = True

    sql = """
    INSERT INTO dbo.rpg_llamadas_parametros
    (id_llamada, orden_parametro, valor_parametro, sentencia_parametro)
    VALUES (?, ?, ?, ?)
    """

    data = [
        (
            id_llamada,
            p["orden"],
            p.get("valor"),   # ← 10
            p.get("nombre")   # ← DTQI
        )
        for p in parametros
    ]

    cursor.executemany(sql, data)
    conn.commit()


def insertar_llamadas(conn, id_analisis, llamadas):
    if not llamadas:
        return

    for llamada in llamadas:
        id_llamada = insertar_llamada(conn, id_analisis, llamada)
        insertar_parametros_llamada(conn, id_llamada, llamada.get("parametros", []))


# =========================================================
# PROCESO PRINCIPAL
# =========================================================

def procesar_directorio(ruta_carpeta):
    conn = conectar_bd()

    try:
        id_analisis = insertar_analisis(conn, ruta_carpeta)
        print(f"Análisis creado con id: {id_analisis}")

        total_rpg = 0
        total_archivos = 0
        total_colas = 0
        total_llamadas = 0
        total_parametros = 0
        total_omitidos = 0

        for archivo in os.listdir(ruta_carpeta):
            if archivo.lower().endswith(".rpg"):
                ruta_archivo = os.path.join(ruta_carpeta, archivo)
                hash_archivo = calcular_hash_archivo(ruta_archivo)

                if archivo_ya_procesado(conn, hash_archivo):
                    print(f"[OMITIDO] El archivo ya fue analizado: {archivo}")
                    total_omitidos += 1
                    continue

                print(f"Procesando archivo: {ruta_archivo}")

                resultado = analizar_rpg(ruta_archivo)

                insertar_archivos(conn, id_analisis, resultado["archivos"])
                insertar_colas(conn, id_analisis, resultado["colas"])
                insertar_llamadas(conn, id_analisis, resultado["llamadas"])

                registrar_archivo_procesado(conn, archivo, hash_archivo)

                total_rpg += 1
                total_archivos += len(resultado["archivos"])
                total_colas += len(resultado["colas"])
                total_llamadas += len(resultado["llamadas"])
                total_parametros += sum(len(ll.get("parametros", [])) for ll in resultado["llamadas"])

        print("\n===== RESUMEN =====")
        print(f"Archivos RPG procesados: {total_rpg}")
        print(f"Archivos omitidos por duplicidad: {total_omitidos}")
        print(f"Archivos detectados en RPG: {total_archivos}")
        print(f"Colas detectadas: {total_colas}")
        print(f"Llamadas detectadas: {total_llamadas}")
        print(f"Parámetros detectados: {total_parametros}")

    except Exception as e:
        print(f"Error durante el proceso: {e}")
        conn.rollback()
    finally:
        conn.close()