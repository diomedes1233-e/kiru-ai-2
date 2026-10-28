from pathlib import Path

def crear_carpetas_modulares():
    print("=" * 60)
    print(" 🏗️ CREANDO ESTRUCTURA MODULAR DEFINITIVA DE KIRU AI")
    print("=" * 60)
    
    # Definir los directorios clave de la arquitectura modular
    directorios = [
        "backend/app/api",          # Endpoints y rutas del API
        "backend/app/core",         # Configuraciones centrales y seguridad
        "backend/app/models",       # Modelos de base de datos (PostgreSQL)
        "backend/app/services",     # Lógica de negocio, agentes de IA y Redis
        "docker",                   # Configuraciones específicas para contenedores
        "scripts",                  # Scripts de automatización y mantenimiento
    ]
    
    for dir_path in directorios:
        p = Path(dir_path)
        p.mkdir(parents=True, exist_ok=True)
        print(f"  📁 Creado/Verificado: {p}")
        
    print("\n" + "=" * 60)
    print("✅ ¡Estructura modular creada con éxito!")
    print("=" * 60)

if __name__ == "__main__":
    crear_carpetas_modulares()
