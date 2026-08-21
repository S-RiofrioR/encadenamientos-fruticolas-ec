"""
setup_project.py

Script para crear automáticamente la estructura de carpetas y archivos
base del proyecto:

"Encadenamientos Frutícolas de Alto Valor y Reducción del Desempleo Rural en Ecuador"

Ejecutar desde la raíz del proyecto:

    python setup_project.py
"""

from pathlib import Path


def crear_carpetas():
    """
    Crea la estructura principal de carpetas del proyecto.
    """
    carpetas = [
        ".vscode",
        "data",
        "data/raw",
        "data/processed",
        "notebooks",
        "src",
        "outputs",
        "outputs/figures",
        "outputs/models",
        "outputs/tables",
    ]

    for carpeta in carpetas:
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        print(f"Carpeta creada/verificada: {carpeta}")


def crear_archivos_base():
    """
    Crea archivos mínimos para inicializar el proyecto.
    """
    archivos = {
        # Archivo README inicial
        "README.md": """# Encadenamientos Frutícolas de Alto Valor y Reducción del Desempleo Rural en Ecuador

Proyecto de análisis de datos y econometría para evaluar el impacto
de la reconversión productiva hacia frutas de alto valor sobre el
empleo rural en Ecuador.

## Estructura del proyecto

- `data/raw`: datos crudos INEC, BCE y MAG/SIPA.
- `data/processed`: datos limpios y procesados.
- `notebooks`: notebooks de exploración y análisis.
- `src`: módulos Python reutilizables.
- `outputs`: gráficos, modelos y tablas.
""",

        # Archivo de dependencias
        "requirements.txt": """pandas
numpy
pyreadstat
statsmodels
matplotlib
seaborn
openpyxl
jupyter
ipykernel
""",

        # Archivo para mantener carpetas vacías en Git
        "data/raw/.gitkeep": "",
        "data/processed/.gitkeep": "",
        "outputs/figures/.gitkeep": "",
        "outputs/models/.gitkeep": "",
        "outputs/tables/.gitkeep": "",

        # Inicializador del paquete Python
        "src/__init__.py": "",

        # Módulos principales vacíos por ahora
        "src/ingestion.py": '"""\nMódulo de ingesta y limpieza de datos INEC, BCE y MAG/SIPA.\n"""\n',
        "src/metrics.py": '"""\nMódulo de cálculo de métricas agrícolas, laborales y económicas.\n"""\n',
        "src/econometrics.py": '"""\nMódulo de modelos econométricos y simulaciones.\n"""\n',
        "src/visualization.py": '"""\nMódulo de generación de gráficos para informe y dashboard.\n"""\n',

        # Configuración básica de VS Code
        ".vscode/settings.json": """{
    "python.analysis.extraPaths": [
        "./src"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/.ipynb_checkpoints": true
    },
    "editor.formatOnSave": true,
    "notebook.formatOnSave.enabled": true
}
""",

        # Archivo .gitignore para no subir datos sensibles/pesados ni entornos
        ".gitignore": """# Entornos virtuales
.venv/
venv/
env/

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.ipynb_checkpoints/

# Datos crudos y procesados
data/raw/*
data/processed/*

# Mantener carpetas vacías
!data/raw/.gitkeep
!data/processed/.gitkeep

# Resultados generados
outputs/figures/*
outputs/models/*
outputs/tables/*

!outputs/figures/.gitkeep
!outputs/models/.gitkeep
!outputs/tables/.gitkeep

# Archivos temporales
*.tmp
*.log
.DS_Store
""",
    }

    for ruta, contenido in archivos.items():
        archivo = Path(ruta)

        # Crear carpeta padre si no existe
        archivo.parent.mkdir(parents=True, exist_ok=True)

        # No sobrescribir si el archivo ya existe
        if not archivo.exists():
            archivo.write_text(contenido, encoding="utf-8")
            print(f"Archivo creado: {ruta}")
        else:
            print(f"Archivo ya existe, no se sobrescribe: {ruta}")


def main():
    print("Creando estructura del proyecto...")
    crear_carpetas()
    crear_archivos_base()
    print("\nEstructura del proyecto creada correctamente.")


if __name__ == "__main__":
    main()