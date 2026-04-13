CREATE TABLE dbo.rpg_analisis (
    id_analisis INT IDENTITY(1,1) PRIMARY KEY,
    fuente VARCHAR(255) NOT NULL,
    fecha DATE NOT NULL,
    hora TIME NOT NULL
);

CREATE TABLE dbo.rpg_archivos (
    id_archivo INT IDENTITY(1,1) PRIMARY KEY,
    id_analisis INT NOT NULL,
    archivo_rpg VARCHAR(255) NOT NULL,
    nombre_objeto VARCHAR(255) NOT NULL,
    FOREIGN KEY (id_analisis) REFERENCES dbo.rpg_analisis(id_analisis)
);

CREATE TABLE dbo.rpg_colas (
    id_cola INT IDENTITY(1,1) PRIMARY KEY,
    id_analisis INT NOT NULL,
    archivo_rpg VARCHAR(255) NOT NULL,
    nombre_cola VARCHAR(255) NOT NULL,
    sentencia VARCHAR(1000) NULL,
    FOREIGN KEY (id_analisis) REFERENCES dbo.rpg_analisis(id_analisis)
);

CREATE TABLE dbo.rpg_llamadas (
    id_llamada INT IDENTITY(1,1) PRIMARY KEY,
    id_analisis INT NOT NULL,
    archivo_rpg VARCHAR(255) NOT NULL,
    nombre_programa VARCHAR(255) NOT NULL,
    sentencia VARCHAR(1000) NULL,
    FOREIGN KEY (id_analisis) REFERENCES dbo.rpg_analisis(id_analisis)
);

CREATE TABLE rpg_archivos_procesados (
    id_archivo INT IDENTITY(1,1) PRIMARY KEY,
    nombre_archivo VARCHAR(255) NOT NULL,
    hash_archivo VARCHAR(64) NOT NULL,
    fecha_proceso DATETIME NOT NULL DEFAULT GETDATE(),
    UNIQUE(hash_archivo)
);

CREATE UNIQUE INDEX UX_archivos_nombre_fecha
ON rpg_archivos_procesados(nombre_archivo);