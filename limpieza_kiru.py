import json
from pathlib import Path

def limpiar_proyecto():
    print("=" * 60)
    print(" 🧹 INICIANDO LIMPIEZA MODULAR DE KIRU AI")
    print("=" * 60)
    
    # Cargar el reporte generado previamente
    try:
        with open("auditoria_resultado.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ No se encontró 'auditoria_resultado.json'. Ejecuta primero el generador de reportes.")
        return

    # Directorios o archivos temporales candidatos a purgar de forma segura
    extensiones_basura = {".log", ".tmp", ".cache"}
    archivos_eliminados = 0

    # Limpieza de archivos temporales basados en extensiones innecesarias
    for ext, rutas in data.get("archivos_por_categoria", {}).items():
        if ext in extensiones_basura:
            for ruta in rutas:
                p = Path(ruta)
                if p.exists():
                    p.unlink()
                    print(f"  🗑️ Eliminado temporal: {p}")
                    archivos_eliminados += 1

    # Limpiar cachés de Python (__pycache__) recursivamente en el directorio actual
    root = Path(".")
    for pycache in root.rglob("__pycache__"):
        if pycache.is_dir():
            for sub in pycache.iterdir():
                sub.unlink()
            pycache.rmdir()
            print(f"  🗑️ Limpiado directorio caché: {pycache}")
            archivos_eliminados += 1

    print("\n" + "=" * 60)
    print(f"✅ ¡Limpieza completada con éxito!")
    print(f"📊 Total de elementos temporales purgados: {archivos_eliminados}")
    print("=" * 60)

if __name__ == "__main__":
    limpiar_proyecto()
