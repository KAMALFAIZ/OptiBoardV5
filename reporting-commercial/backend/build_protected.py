"""
OptiBoard - Script de build protege (Cython)
==============================================

Ce script LIT les sources depuis app/ et ECRIT une version compilee
dans dist_client/. Les fichiers sources originaux ne sont JAMAIS modifies.

Strategie de protection:
- services/, routes/, middleware/  -> compiles en .pyd (Cython, code natif)
- config*.py, database*.py         -> compiles en .pyd
- models/schemas.py                -> laisse en .py (Pydantic incompatible Cython)
- __init__.py                      -> laisses en .py (init de package)
- run.py                           -> laisse en clair (point d'entree)

Usage:
    build_protected.bat     (Windows - lance vcvarsall puis ce script)
    python build_protected.py   (si l'env MSVC est deja charge)
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import time
import traceback
import py_compile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).parent.resolve()
SRC_APP = BACKEND_DIR / "app"
OUT_DIR = BACKEND_DIR / "dist_client"
OUT_APP = OUT_DIR / "app"

# Dossiers dont TOUS les .py seront tentes en Cython
CYTHONIZE_DIRS = [
    "services",
    "routes",
    "middleware",
    "sage_direct",
]

# Fichiers top-level dans app/ a compiler en Cython
CYTHONIZE_TOPLEVEL = [
    "config.py",
    "config_multitenant.py",
    "database.py",
    "database_multitenant.py",
    "database_unified.py",
]

# Fichiers jamais compiles en Cython (laisses en .py)
SKIP_CYTHON_NAMES = {
    "__init__.py",   # init de package
    "schemas.py",    # Pydantic -> incompatible
    "main.py",       # minimal, point d'entree
}

# Fichiers/dossiers a copier en plus de app/
EXTRA_FILES = [
    "run.py",
    "run_service.py",
    "requirements.txt",
    ".env.example",
]

EXTRA_DIRS = [
    "sql",
    "static",
]


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def banner(msg: str) -> None:
    line = "=" * 70
    log("")
    log(line)
    log(f"  {msg}")
    log(line)


def clean_output() -> None:
    """Supprime dist_client/ s'il existe."""
    if OUT_DIR.exists():
        log(f"[clean] Suppression de {OUT_DIR}")
        shutil.rmtree(OUT_DIR, ignore_errors=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def copy_sources() -> None:
    """Copie app/ et les fichiers annexes vers dist_client/."""
    log(f"[copy] app/  ->  dist_client/app/")
    shutil.copytree(
        SRC_APP,
        OUT_APP,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", "*.pyo", ".pytest_cache", "*.log"
        ),
    )

    for fname in EXTRA_FILES:
        src = BACKEND_DIR / fname
        if src.exists():
            shutil.copy2(src, OUT_DIR / fname)
            log(f"[copy] {fname}")

    for dname in EXTRA_DIRS:
        src = BACKEND_DIR / dname
        if src.exists() and src.is_dir():
            shutil.copytree(
                src,
                OUT_DIR / dname,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            log(f"[copy] {dname}/")


PYDANTIC_PATTERN = re.compile(
    r"class\s+\w+\s*\([^)]*\b(?:BaseModel|BaseSettings|RootModel)\b",
    re.MULTILINE,
)


def defines_pydantic_model(py_file: Path) -> bool:
    """
    Retourne True si le fichier DEFINIT une classe Pydantic BaseModel.
    Ces fichiers doivent aller en .pyc car Cython + Pydantic => incompatible
    (les methodes deviennent cyfunction et Pydantic les confond avec des champs).
    """
    try:
        txt = py_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return bool(PYDANTIC_PATTERN.search(txt))


def compile_to_pyc(py_file: Path) -> tuple[bool, str]:
    """
    Compile un .py en .pyc 'legacy' (a cote du .py, pas dans __pycache__),
    puis supprime le .py. Le .pyc est importable tel quel par Python.
    """
    try:
        pyc_path = py_file.with_suffix(".pyc")
        py_compile.compile(
            str(py_file),
            cfile=str(pyc_path),
            doraise=True,
            optimize=2,
        )
        py_file.unlink()
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def collect_py_files() -> list[Path]:
    """Retourne la liste des .py a compiler (chemins dans dist_client/)."""
    files: list[Path] = []

    # Top-level
    for name in CYTHONIZE_TOPLEVEL:
        p = OUT_APP / name
        if p.exists():
            files.append(p)

    # Sous-dossiers
    for d in CYTHONIZE_DIRS:
        sub = OUT_APP / d
        if not sub.exists():
            continue
        for p in sub.rglob("*.py"):
            if p.name in SKIP_CYTHON_NAMES:
                continue
            files.append(p)

    return sorted(files)


def _is_transient_error(output: str) -> bool:
    """Retourne True si l'erreur ressemble a un probleme d'antivirus/lock."""
    transient_markers = (
        "Permission denied",
        "LNK1104",
        "C1083",
        "being used by another process",
        "Acces refuse",
        "Access is denied",
    )
    return any(m in output for m in transient_markers)


def build_one(py_file: Path, max_retries: int = 4) -> tuple[bool, str]:
    """
    Compile un fichier .py en .pyd via Cython.
    Travaille en se placant dans dist_client/ pour que le nom du module
    reflete le chemin (app.services.xxx).

    Retente jusqu'a max_retries si l'erreur ressemble a un conflit antivirus
    (Permission denied / LNK1104 / C1083).
    """
    import contextlib
    import io

    rel = py_file.relative_to(OUT_DIR)  # ex: app/services/cache.py
    rel_str = str(rel).replace("\\", "/")

    last_err = ""

    for attempt in range(1, max_retries + 1):
        cwd_backup = os.getcwd()
        try:
            os.chdir(OUT_DIR)

            # Import tardif pour que l'erreur soit claire si Cython absent
            from Cython.Build import cythonize
            from setuptools import setup

            # Cythonize: capture les erreurs de compilation Cython (syntaxe)
            cy_buf = io.StringIO()
            with contextlib.redirect_stdout(cy_buf), contextlib.redirect_stderr(cy_buf):
                try:
                    exts = cythonize(
                        [rel_str],
                        language_level=3,
                        quiet=True,
                        nthreads=1,
                        # CRITIQUE: desactive l'enforcement des annotations Python
                        # par Cython. Sans ca, FastAPI casse car `param: str = Query(...)`
                        # est interprete comme "param doit etre un str natif" et le
                        # defaut `Query(...)` (objet) est refuse au init du module avec
                        # TypeError: Expected str, got Query.
                        compiler_directives={
                            "language_level": 3,
                            "annotation_typing": False,
                            "binding": True,
                            "embedsignature": True,
                        },
                    )
                except Exception as cy_err:
                    # Erreur Cython (pas transitoire) -> pas de retry
                    detail = cy_buf.getvalue() or str(cy_err)
                    return False, f"[Cython] {type(cy_err).__name__}: {detail[-1500:]}"

            # Build C: peut echouer temporairement (antivirus)
            build_buf = io.StringIO()
            with contextlib.redirect_stdout(build_buf), contextlib.redirect_stderr(build_buf):
                try:
                    setup(
                        name=f"_build_{py_file.stem}",
                        ext_modules=exts,
                        script_args=[
                            "build_ext",
                            "--inplace",
                            "--build-temp",
                            str(OUT_DIR / "_build_temp"),
                        ],
                    )
                    # Succes
                    return True, ""
                except SystemExit as se:
                    if se.code in (0, None):
                        return True, ""
                    last_err = build_buf.getvalue()[-2000:]

            # Erreur: transitoire ?
            if _is_transient_error(last_err) and attempt < max_retries:
                time.sleep(0.6 * attempt)  # backoff
                continue

            return False, f"[Link] attempt {attempt}/{max_retries}: {last_err}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}"
            if _is_transient_error(last_err) and attempt < max_retries:
                time.sleep(0.6 * attempt)
                continue
            return False, last_err
        finally:
            os.chdir(cwd_backup)

    return False, last_err or "unknown error"


def remove_source_after_success(py_file: Path) -> None:
    """Supprime le .py et le .c dans dist_client/ si le .pyd existe."""
    pyd_candidates = list(py_file.parent.glob(f"{py_file.stem}.cp*-win_amd64.pyd"))
    if not pyd_candidates:
        return
    try:
        py_file.unlink()
    except OSError:
        pass
    c_file = py_file.with_suffix(".c")
    if c_file.exists():
        try:
            c_file.unlink()
        except OSError:
            pass


def cleanup_build_artifacts() -> None:
    """Supprime les dossiers temporaires de build dans dist_client/."""
    for name in ("build", "_build_temp"):
        p = OUT_DIR / name
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    # Supprime aussi les .exp / .lib / .obj residuels
    for pat in ("*.exp", "*.lib", "*.obj"):
        for f in OUT_DIR.rglob(pat):
            try:
                f.unlink()
            except OSError:
                pass


def has_existing_pyd(py_file: Path) -> bool:
    """Check si un .pyd correspondant existe deja a cote du .py."""
    return bool(list(py_file.parent.glob(f"{py_file.stem}.cp*-win_amd64.pyd")))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    retry_mode = "--retry" in sys.argv

    banner("OptiBoard - Build Protected Distribution")
    log(f"Source  : {SRC_APP}")
    log(f"Sortie  : {OUT_DIR}")
    if retry_mode:
        log("Mode    : RETRY (rebuild des echecs uniquement)")
    log("")
    log("IMPORTANT: les fichiers sources originaux NE sont PAS modifies.")

    t0 = time.time()

    if retry_mode:
        if not OUT_DIR.exists():
            log("[retry] dist_client/ n'existe pas -> fallback build complet")
            retry_mode = False

    if not retry_mode:
        # 1. Nettoyage
        banner("[1/5] Nettoyage du dossier de sortie")
        clean_output()

        # 2. Copie
        banner("[2/5] Copie des sources vers dist_client/")
        copy_sources()
    else:
        banner("[1-2/5] Mode retry: conservation du dist_client/ existant")

    # 3. Collecte
    banner("[3/6] Collecte des fichiers a compiler")
    all_files = collect_py_files()
    if retry_mode:
        before = len(all_files)
        all_files = [f for f in all_files if f.exists()]
        log(f"-> {before} candidats, {len(all_files)} encore en .py dans dist_client")
    else:
        log(f"-> {len(all_files)} fichiers Python candidats")

    # 4. Split Pydantic vs non-Pydantic
    banner("[4/6] Detection des fichiers contenant des modeles Pydantic")
    pyd_targets: list[Path] = []      # -> Cython .pyd (protection maximale)
    pyc_targets: list[Path] = []      # -> bytecode .pyc (Pydantic-safe)
    for f in all_files:
        if defines_pydantic_model(f):
            pyc_targets.append(f)
        else:
            pyd_targets.append(f)
    log(f"-> {len(pyd_targets)} fichiers -> Cython .pyd (code natif)")
    log(f"-> {len(pyc_targets)} fichiers -> bytecode .pyc (Pydantic-safe)")

    # 5. Compilation Cython
    banner("[5/6] Compilation Cython -> .pyd")
    pyd_successes: list[Path] = []
    pyd_failures: list[tuple[Path, str]] = []
    total_pyd = len(pyd_targets)

    for i, f in enumerate(pyd_targets, 1):
        rel = f.relative_to(OUT_DIR)
        log(f"  [{i:3d}/{total_pyd}] {rel} ...")
        ok, err = build_one(f)
        if ok:
            pyd_successes.append(f)
        else:
            pyd_failures.append((f, err))
            first_err = (err.splitlines() or [""])[0][:120]
            log(f"        ECHEC: {first_err}")

    # Suppression des .py sources des modules .pyd compiles
    for f in pyd_successes:
        remove_source_after_success(f)

    # 6. Compilation py_compile -> .pyc
    banner("[6/6] Compilation bytecode -> .pyc (fichiers Pydantic)")
    pyc_successes: list[Path] = []
    pyc_failures: list[tuple[Path, str]] = []
    total_pyc = len(pyc_targets)

    for i, f in enumerate(pyc_targets, 1):
        rel = f.relative_to(OUT_DIR)
        log(f"  [{i:3d}/{total_pyc}] {rel} ...")
        ok, err = compile_to_pyc(f)
        if ok:
            pyc_successes.append(f)
        else:
            pyc_failures.append((f, err))
            log(f"        ECHEC: {err}")

    # Cleanup
    cleanup_build_artifacts()

    elapsed = time.time() - t0

    # Rapport final
    banner("RAPPORT FINAL")
    log(f"Modules en .pyd (Cython natif) : {len(pyd_successes)}/{total_pyd}")
    log(f"Modules en .pyc (bytecode)     : {len(pyc_successes)}/{total_pyc}")
    log(f"Total protege                  : {len(pyd_successes) + len(pyc_successes)}/{total_pyd + total_pyc}")
    log(f"Echecs                         : {len(pyd_failures) + len(pyc_failures)}")
    log(f"Duree                          : {elapsed:.1f}s")
    log(f"Sortie                         : {OUT_DIR}")

    all_failures = pyd_failures + pyc_failures
    if all_failures:
        log("")
        log("Modules NON protegeables (restent en .py) :")
        for f, err in all_failures:
            log(f"  - {f.relative_to(OUT_DIR)}")
            first_err = (err.splitlines() or [""])[0][:120]
            log(f"      {first_err}")

    log("")
    log("Termine.")
    return 0 if not all_failures else 2


if __name__ == "__main__":
    sys.exit(main())
