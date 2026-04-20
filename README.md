# 📊 Análisis de Programas RPG (AS400)

## 🧠 Descripción

Este proyecto permite analizar archivos RPG (AS400 - IBM i) para extraer información estructurada sobre:

- Archivos utilizados (`F`)
- Colas (`QRCVDTAQ`, `QSNDDTAQ`)
- Llamadas a programas (`CALL`, `CALLP`)
- Parámetros asociados a cada llamada (`PARM`)

Los datos son almacenados en SQL Server, permitiendo análisis posterior, auditoría y trazabilidad.

Además, el sistema evita reprocesar archivos duplicados mediante un hash SHA-256.

---

## 🚀 Funcionalidades

✔ Procesamiento masivo de archivos `.rpg`  
✔ Detección de archivos físicos/lógicos (líneas `F`)  
✔ Identificación de colas (`QRCVDTAQ`, `QSNDDTAQ`)  
✔ Extracción de llamadas (`CALL`, `CALLP`)  
✔ Asociación de parámetros (`PARM`) a cada llamada  
✔ Persistencia en base de datos SQL Server  
✔ Control de duplicidad mediante hash  
✔ Relación 1:N entre llamadas y parámetros  

---

## 📁 Estructura del proyecto


project/
│
├── main.py
├── funciones.py
├── README.md
└── /archivos_rpg


---

## ⚙️ Requisitos

- Python 3.10+
- SQL Server
- ODBC Driver 18 for SQL Server

---

## 📦 Instalación

### 1. Clonar repositorio
git clone <repo>
cd proyecto
2. Instalar dependencias
pip install pyodbc
3. Configurar conexión a base de datos

Editar en funciones.py:

def conectar_bd():
    conn = pyodbc.connect(...)
▶️ Uso

Ejecutar:

python main.py

El sistema:

Recorre archivos .rpg
Analiza contenido línea por línea
Extrae información estructurada
Inserta datos en SQL Server
Evita reprocesar archivos ya analizados
🗄️ Modelo de Base de Datos
🔹 Tabla: rpg_analisis

Registro de cada ejecución

Campo	Descripción
id_analisis	Identificador del análisis
fuente	Carpeta procesada
fecha	Fecha
hora	Hora
🔹 Tabla: rpg_archivos

Archivos detectados dentro del RPG

🔹 Tabla: rpg_colas

Colas detectadas en el código

🔹 Tabla: rpg_llamadas

Llamadas a programas

Campo	Descripción
id_llamada	ID
id_analisis	Relación
archivo_rpg	Archivo fuente
nombre_programa	Programa llamado
sentencia	Línea original
linea_call	Número de línea
🔹 Tabla: rpg_llamadas_parametros

Parámetros asociados a cada llamada

Campo	Descripción
id_parametro	ID
id_llamada	Relación
orden_parametro	Orden del parámetro
sentencia_parametro	Nombre (ej: DTQI)
valor_parametro	Valor (ej: 10)
🔹 Tabla: rpg_archivos_procesados

Control de duplicidad

Campo	Descripción
nombre_archivo	Nombre del archivo
hash_archivo	Hash SHA-256
fecha_proceso	Fecha de carga

🧩 Ejemplo de extracción
Entrada RPG:
C CALL 'QRCVDTAQ'
C PARM DTQI 10
C PARM PARBIQ 50
Salida en base de datos:
Programa	Parámetro	Valor
QRCVDTAQ	DTQI	10
QRCVDTAQ	PARBIQ	50

🔍 Consultas útiles
🔹 Ver llamadas con parámetros
SELECT 
    l.archivo_rpg,
    l.nombre_programa,
    p.orden_parametro,
    p.sentencia_parametro,
    p.valor_parametro
FROM dbo.rpg_llamadas l
LEFT JOIN dbo.rpg_llamadas_parametros p
    ON l.id_llamada = p.id_llamada
ORDER BY l.archivo_rpg, p.orden_parametro;

🔹 Ver parámetros agrupados

SELECT 
    l.nombre_programa,
    STRING_AGG(
        CONCAT(p.sentencia_parametro, '(', p.valor_parametro, ')'),
        ', '
    ) AS parametros
FROM dbo.rpg_llamadas l
LEFT JOIN dbo.rpg_llamadas_parametros p
    ON l.id_llamada = p.id_llamada
GROUP BY l.nombre_programa;

🔹 Buscar llamadas por parámetro

SELECT 
    l.nombre_programa,
    p.sentencia_parametro,
    p.valor_parametro
FROM dbo.rpg_llamadas l
JOIN dbo.rpg_llamadas_parametros p
    ON l.id_llamada = p.id_llamada
WHERE p.sentencia_parametro = 'DTQI';

⚠️ Consideraciones
El parser está adaptado a RPG fixed format
Se ignoran líneas comentadas simples (*)
Los parámetros se interpretan como:
sentencia_parametro → nombre
valor_parametro → longitud/valor
El sistema asocia PARM al CALL más cercano

🔐 Control de duplicidad

Antes de procesar un archivo:

Se calcula su hash SHA-256
Se valida en la tabla rpg_archivos_procesados
Si existe → se omite
Si no existe → se procesa y registra

🔮 Mejoras futuras
Parser por columnas (RPG fixed format real)
Identificación de tipos de parámetros
Análisis de dependencias entre programas
Visualización gráfica (grafo de llamadas)
Exportación a Excel / Power BI

👨‍💻 Autor
Proyecto desarrollado para análisis de código RPG legacy en entornos empresariales/bancarios.