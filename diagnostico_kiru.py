#!/usr/bin/env python3
"""Auditor no destructivo para Kiru OS. No compila, instala ni modifica el proyecto."""
import argparse, datetime, hashlib, json, os, platform, re, subprocess, sys
from pathlib import Path

HOME = Path.home()
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def run(cmd, cwd=None, timeout=15):
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout, check=False,
                           env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        return {"command": " ".join(cmd), "exit_code": p.returncode, "output": p.stdout.strip()[:10000]}
    except Exception as e:
        return {"command": " ".join(cmd), "exit_code": None, "output": f"{type(e).__name__}: {e}"}

def digest(p):
    h = hashlib.sha256()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024*1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def read(p, limit=1_000_000):
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except Exception:
        return ""

def main():
    ap = argparse.ArgumentParser(description="Auditoría no destructiva de Kiru OS")
    ap.add_argument("--project", default=str(HOME / "kiru_ai"), help="Ruta del proyecto")
    args = ap.parse_args()
    project = Path(args.project).expanduser().resolve()
    outdir = HOME / "kiru-os-backups" / "diagnosticos"
    outdir.mkdir(parents=True, exist_ok=True)
    txtpath = outdir / f"diagnostico-kiru-{STAMP}.txt"
    jsonpath = outdir / f"diagnostico-kiru-{STAMP}.json"
    data = {"fecha": datetime.datetime.now().astimezone().isoformat(),
            "proyecto": str(project), "modo": "solo lectura; no ejecuta compilaciones",
            "sistema": {}, "git": {}, "archivos": {}, "logs": [], "hallazgos": []}
    issues = data["hallazgos"]

    def issue(level, title, detail, next_step=""):
        issues.append({"prioridad": level, "hallazgo": title, "detalle": detail, "siguiente_paso": next_step})

    if not project.is_dir():
        issue("CRITICO", "No se encuentra la carpeta del proyecto", str(project),
              "Ejecuta el script con --project y la ruta correcta.")
    for key, cmd in {
        "macOS": ["sw_vers"], "node": ["node", "--version"], "node_path": ["which", "node"],
        "npm": ["npm", "--version"], "git_version": ["git", "--version"],
        "disk": ["df", "-h", str(project if project.exists() else HOME)],
        "memory": ["vm_stat"], "swap": ["sysctl", "vm.swapusage"],
        "docker": ["docker", "version", "--format", "{{.Client.Version}}"],
        "docker_info": ["docker", "info", "--format", "Containers={{.Containers}} Images={{.Images}}"]
    }.items():
        data["sistema"][key] = run(cmd, timeout=20)

    if project.is_dir():
        for key, cmd in {
            "status": ["git", "status", "--short", "--branch"],
            "branch": ["git", "branch", "--show-current"],
            "last_commit": ["git", "log", "-1", "--format=%h %ad %s", "--date=iso"],
            "diff_stat": ["git", "diff", "--stat"],
            "diff_names": ["git", "diff", "--name-only"],
            "untracked": ["git", "ls-files", "--others", "--exclude-standard"]
        }.items():
            data["git"][key] = run(cmd, project)

        pkgpath = project / "package.json"
        try:
            pkg = json.loads(read(pkgpath))
            data["archivos"]["package_json"] = {
                "name": pkg.get("name"), "version": pkg.get("version"),
                "engines": pkg.get("engines"), "scripts": pkg.get("scripts"),
                "relevant_dependencies": {
                    k: v for group in ("dependencies", "devDependencies")
                    for k, v in (pkg.get(group) or {}).items()
                    if any(s in k.lower() for s in ("svelte", "vite", "pyodide", "rollup", "typescript"))
                }
            }
            nodever = data["sistema"]["node"]["output"]
            req = (pkg.get("engines") or {}).get("node", "")
            if nodever.startswith("v24.") and ("22" in req or "<=22" in req):
                issue("ALTO", "Node está fuera del rango declarado",
                      f"Detectado {nodever}; package.json declara {req}.",
                      "Probar Node 22 en una sesión controlada antes de recompilar.")
            buildcmd = (pkg.get("scripts") or {}).get("build", "")
            if "pyodide:fetch" in buildcmd:
                issue("MEDIO", "El build ejecuta pyodide:fetch",
                      f"Script build: {buildcmd}",
                      "Inspeccionar prepare-pyodide.js antes de ejecutar build.")
        except Exception as e:
            issue("CRITICO", "No se pudo interpretar package.json", str(e))

        data["sistema"]["npm_ls"] = run(["npm", "ls", "--depth=0"], project, 30)
        data["sistema"]["vite_version"] = run(["npm", "exec", "vite", "--", "--version"], project, 20)
        data["sistema"]["svelte_check_version"] = run(["npm", "exec", "--", "svelte-check", "--version"], project, 20)

        targets = ["node_modules", ".svelte-kit", "build", "static/pyodide", "node_modules/pyodide"]
        sizes = {}
        for rel in targets:
            p = project / rel
            if not p.exists():
                sizes[rel] = {"exists": False}
                continue
            total, count = 0, 0
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d != ".git"]
                for name in files:
                    try:
                        total += (Path(root) / name).stat().st_size
                        count += 1
                    except OSError:
                        pass
            sizes[rel] = {"exists": True, "files": count, "bytes": total,
                          "size_mb": round(total / 1024**2, 2)}
        data["archivos"]["directories"] = sizes
        if not sizes["build"]["exists"]:
            issue("MEDIO", "No existe build/",
                  "No se encontró una salida de compilación de producción.",
                  "Investigar la causa del error de memoria antes de repetir el build.")

        for rel in ["package.json", "package-lock.json", "vite.config.ts", "svelte.config.js",
                    "tsconfig.json", "Dockerfile", "Dockerfile.backup",
                    "docker-compose.yaml", "docker-compose.yml",
                    "scripts/prepare-pyodide.js", "src/lib/workers/pyodide.worker.ts",
                    "src/lib/pyodide/createPyodideWorker.ts", "src/lib/pyodide/pyodideSandboxHost.ts"]:
            p = project / rel
            if p.is_file():
                data["archivos"].setdefault("file_fingerprints", {})[rel] = {
                    "bytes": p.stat().st_size, "sha256": digest(p),
                    "modified": datetime.datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat()
                }
        vite = read(project / "vite.config.ts")
        if "minify: false" in vite:
            issue("INFO", "Minificación desactivada", "vite.config.ts contiene minify: false.",
                  "No cambiar esta opción hasta tener una prueba controlada.")
        worker = read(project / "src/lib/workers/pyodide.worker.ts")
        if "from 'pyodide'" in worker or 'from "pyodide"' in worker:
            issue("INVESTIGAR", "El worker importa Pyodide directamente",
                  "El código del worker importa el paquete pyodide; los registros previos mostraron avisos node:* al empaquetarlo.",
                  "Aislar el empaquetado del worker sin tocar el archivo original.")
        for rel in ["Dockerfile", "Dockerfile.backup"]:
            p = project / rel
            if p.is_file():
                data["archivos"].setdefault("dockerfile_lines", {})[rel] = len(read(p).splitlines())
        dl = data["archivos"].get("dockerfile_lines", {})
        if dl.get("Dockerfile") and dl.get("Dockerfile.backup") and dl["Dockerfile"] < dl["Dockerfile.backup"]:
            issue("INVESTIGAR", "Dockerfile es más corto que Dockerfile.backup",
                  f"Dockerfile: {dl['Dockerfile']} líneas; backup: {dl['Dockerfile.backup']} líneas.",
                  "Comparar con Git antes de restaurar cualquier versión.")

    # Find and summarize existing logs; do not create new builds.
    backup = HOME / "kiru-os-backups"
    logfiles = []
    for pattern in ["kiru-vite-build-*.log", "svelte-check-*.log"]:
        logfiles.extend(backup.glob(pattern))
    logfiles = sorted(set(logfiles), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
    pat = re.compile(r"FATAL ERROR|heap out of memory|Reached heap limit|ERR!|Error:|error TS\d+|Cannot find|not found|Killed", re.I)
    for p in logfiles:
        content = read(p, 2_000_000)
        matches = []
        for n, line in enumerate(content.splitlines(), 1):
            if pat.search(line):
                matches.append({"line": n, "text": line[:500]})
                if len(matches) >= 30:
                    break
        data["logs"].append({"path": str(p), "size_bytes": p.stat().st_size,
                             "sha256": digest(p), "matches": matches})
        for m in matches:
            if "heap out of memory" in m["text"].lower() or "reached heap limit" in m["text"].lower():
                issue("CRITICO", "Un log anterior confirma agotamiento del heap",
                      f"{p.name}, línea {m['line']}: {m['text']}",
                      "No aumentar memoria a ciegas; probar primero compatibilidad de Node y aislar Rollup/worker.")
                break

    data["hallazgos"].sort(key=lambda x: {"CRITICO": 0, "ALTO": 1, "INVESTIGAR": 2, "MEDIO": 3, "INFO": 4}.get(x["prioridad"], 5))
    jsonpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "KIRU OS — DIAGNÓSTICO AUTOMÁTICO NO DESTRUCTIVO",
        "=" * 58, f"Fecha: {data['fecha']}", f"Proyecto: {project}",
        "No se ejecutó build ni se modificó el proyecto.", "",
        f"Hallazgos totales: {len(issues)}",
        f"Críticos: {sum(x['prioridad']=='CRITICO' for x in issues)} | Altos: {sum(x['prioridad']=='ALTO' for x in issues)} | "
        f"Investigar: {sum(x['prioridad']=='INVESTIGAR' for x in issues)} | Medios: {sum(x['prioridad']=='MEDIO' for x in issues)} | "
        f"Info: {sum(x['prioridad']=='INFO' for x in issues)}", "", "HALLAZGOS", "-" * 58
    ]
    for i, x in enumerate(issues, 1):
        lines += [f"{i}. [{x['prioridad']}] {x['hallazgo']}", f"   {x['detalle']}", f"   Acción: {x['siguiente_paso']}", ""]
    lines += ["ESTADO GIT", "-" * 58, data.get("git", {}).get("status", {}).get("output", "No disponible"),
              "", "VERSIONES", "-" * 58]
    for k in ["node", "node_path", "npm", "vite_version", "svelte_check_version", "npm_ls", "docker_info"]:
        x = data["sistema"].get(k)
        if x:
            lines += [f"{k}: {x['output'][:3000]}", ""]
    lines += ["TAMAÑOS DE DIRECTORIOS", "-" * 58,
              json.dumps(data.get("archivos", {}).get("directories", {}), ensure_ascii=False, indent=2),
              "", "ERRORES EN LOGS", "-" * 58]
    for log in data["logs"]:
        lines.append(f"\n{log['path']}")
        lines.extend(f"  Línea {m['line']}: {m['text']}" for m in log["matches"][:15])
    lines += ["", "INFORMES:", str(txtpath), str(jsonpath)]
    txtpath.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("DIAGNÓSTICO KIRU OS TERMINADO")
    print(f"Proyecto: {project}")
    print(f"Hallazgos: {len(issues)}")
    for i, x in enumerate(issues[:15], 1):
        print(f"{i}. [{x['prioridad']}] {x['hallazgo']}: {x['detalle'][:240]}")
    print("\nINFORMES GUARDADOS:")
    print(txtpath)
    print(jsonpath)
    print("\nSeguro: no compiló, no instaló y no modificó archivos del proyecto.")

if __name__ == "__main__":
    main()
