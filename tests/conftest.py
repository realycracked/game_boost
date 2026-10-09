"""Configuration commune des tests : dossier de données isolé et temporaire.

Les modules d'Overdrive lisent leur dossier de données à chaque appel
(``overdrive.paths.data_dir``) : on le redirige avant tout import pour que
les tests n'écrivent jamais dans la configuration réelle de la machine.
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="overdrive-tests-")
if sys.platform == "win32":
    os.environ["APPDATA"] = os.environ["XDG_CONFIG_HOME"]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
