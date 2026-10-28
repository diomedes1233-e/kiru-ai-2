import os
import json
from pathlib import Path

ROOT_DIR = Path(".")
SUPPORTED_EXTENSIONS = {".py", ".svelte", ".ts", ".js", ".yaml", ".yml", ".json"}

def generar_reporte():
    print("=" * 60)
    print(" 📑 GENERANDO REPORTE DETALLADO DE AUDITORÍA...")
    print("=" * 60)
    
    reporte_datos = {
        "directorio_raiz": str(ROOT_DIR.absolute()),
        "archivos_por_categoria": {ext: [] for ext in SUPPORTED_EXTENSIONS},
        "directorios_principales": []
    }
    
    # Recorrido recursivo
    for path in ROOT_DIR.rglob("*"):
        if any(part.startswith('.') or part in {"node_modules", "venv", "__pycache__", "dist", "build"} for part in path.parts):
            continue
            
        if path.is_file():
            ext = path.suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                reporte_datos["archivos_por_categoria"][ext].append(str(path))
                
    # Detectar carpetas principales del primer nivel
    for item in ROOT_DIR.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            reporte_datos["directorios_principales"].append(item.name)
            
    # Guardar en JSON
    output_file = "auditoria_resultado.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(reporte_datos, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ ¡Reporte generado con éxito!")
    print(f"💾 Archivo guardado como: {output_file}")
    print("=" * 60)

if __name__ == "__main__":
    generar_reporte()
