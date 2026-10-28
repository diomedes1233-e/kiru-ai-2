import os
from pathlib import Path

ROOT_DIR = Path(".")
SUPPORTED_EXTENSIONS = {".py", ".svelte", ".ts", ".js", ".yaml", ".yml", ".json"}

def audit_project():
    print("=" * 60)
    print(" 🔍 INICIANDO AUDITORÍA MODULAR DE KIRU AI")
    print("=" * 60)
    
    total_files = 0
    file_stats = {ext: 0 for ext in SUPPORTED_EXTENSIONS}
    modules_found = set()
    
    for path in ROOT_DIR.rglob("*"):
        if any(part.startswith('.') or part in {"node_modules", "venv", "__pycache__", "dist", "build"} for part in path.parts):
            continue
            
        if path.is_file():
            ext = path.suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                total_files += 1
                file_stats[ext] += 1
                if len(path.parts) > 1:
                    modules_found.add(path.parts[0])

    print(f"\n📂 Directorio analizado: {path.absolute().parent}")
    print(f"📊 Archivos de código/configuración encontrados: {total_files}\n")
    
    print("--- Desglose por tipo de archivo ---")
    for ext, count in file_stats.items():
        if count > 0:
            print(f"  • {ext}: {count} archivo(s)")
            
    print("\n--- Principales directorios / módulos detectados ---")
    for mod in sorted(modules_found):
        if Path(mod).is_dir():
            print(f"  📁 [Módulo/Carpeta] -> {mod}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    audit_project()
