"""Local Windows compatibility fixes; does not change physics or model algorithms."""
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
environment=(ROOT/'.venv').resolve()
if Path(sys.prefix).resolve()!=environment or sys.prefix==sys.base_prefix:
    raise RuntimeError('Run with this project\'s .venv\\Scripts\\python.exe.')
mujoco=Path(importlib.util.find_spec('mujoco').origin).parent
robosuite=Path(importlib.util.find_spec('robosuite').origin).parent
if not all(package.resolve().is_relative_to(environment) for package in (mujoco,robosuite)):
    raise RuntimeError('Only patch this task\'s isolated robosuite installation.')
# robosuite 1.5.1 Windows loader expects the DLL beside binding_utils.py.
source=mujoco/'mujoco.dll';destination=robosuite/'utils/mujoco.dll'
shutil.copy2(source,destination)
# Windows uses WGL. Disable the macro that otherwise forces Linux-only EGL.
(robosuite/'macros_private.py').write_text('MUJOCO_GPU_RENDERING = False\n',encoding='utf-8')
report={'mujoco_dll_source':str(source),'copied_to':str(destination),
        'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'macro':'MUJOCO_GPU_RENDERING=False (Windows WGL rendering; physics unchanged)'}
(ROOT/'data/windows_compatibility.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
