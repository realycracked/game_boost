"""Construction de l'exécutable Overdrive avec PyInstaller (utilisé par la CI).

Windows : --onefile --windowed --uac-admin (l'exe demande l'élévation UAC au
lancement). Autres plateformes (test local) : binaire console simple.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

#: Modules chargés dynamiquement par uvicorn, invisibles pour l'analyse PyInstaller.
HIDDEN_IMPORTS = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]


#: Binaire PresentMon (capteur de FPS du widget), embarqué seulement s'il a été
#: téléchargé par la CI avant la construction. Voir THIRD_PARTY.md (licence MIT).
PRESENTMON_EXE = ROOT / "presentmon" / "PresentMon.exe"


def build_command() -> list[str]:
    """Compose la commande PyInstaller selon la plateforme."""
    is_windows = sys.platform == "win32"
    add_data_sep = ";" if is_windows else ":"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "Overdrive",
        "--add-data",
        f"overdrive/web{add_data_sep}overdrive/web",
    ]
    if PRESENTMON_EXE.is_file():
        # Embarqué sous presentmon/ dans l'exe (voir overdrive/core/fps.py).
        command += ["--add-binary", f"presentmon/PresentMon.exe{add_data_sep}presentmon"]
        print("PresentMon.exe détecté : il sera embarqué dans l'exécutable.", flush=True)
    else:
        print(
            "PresentMon.exe absent (presentmon/PresentMon.exe) : construction sans "
            "capteur de FPS, le widget affichera — pour les FPS.",
            flush=True,
        )
    if is_windows:
        command += ["--windowed", "--uac-admin"]
    for hidden in HIDDEN_IMPORTS:
        command += ["--hidden-import", hidden]
    if importlib.util.find_spec("webview") is not None:
        # Backends pywebview chargés dynamiquement sous Windows.
        for backend in ("webview.platforms.winforms", "webview.platforms.edgechromium"):
            command += ["--hidden-import", backend]
    if sys.platform == "win32" and importlib.util.find_spec("pystray") is not None:
        # Backend Windows de pystray, choisi dynamiquement à l'exécution
        # (Pillow est détecté statiquement, aucun hidden-import nécessaire).
        command += ["--hidden-import", "pystray._win32"]
    command.append("run.py")
    return command


def main() -> int:
    """Lance PyInstaller et vérifie la présence du binaire produit."""
    command = build_command()
    print("Commande :", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, shell=False)
    if result.returncode != 0:
        print("Échec de PyInstaller (code", result.returncode, ")", flush=True)
        return result.returncode
    exe_name = "Overdrive.exe" if sys.platform == "win32" else "Overdrive"
    exe_path = ROOT / "dist" / exe_name
    if not exe_path.is_file():
        print("Binaire attendu introuvable :", exe_path, flush=True)
        return 1
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"Binaire produit : {exe_path} ({size_mb:.1f} Mo)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
