"""Setup для сборки KWF Prometheus v1.4.1 через cx_Freeze"""

from cx_Freeze import setup, Executable
import sys

build_exe_options = {
    "packages": [
        "numpy",
        "scipy",
        "PySide6",
        "pyqtgraph",
        "encodings",
        "qtawesome",
    ],
    "includes": ["numpy", "scipy", "PySide6", "pyqtgraph", "qtawesome"],
    "include_files": [
        ("smp12c_vibrodiag/gui/styles.py", "smp12c_vibrodiag/gui/styles.py"),
    ],
    "excludes": [
        "tkinter",
        "unittest",
        "email",
        "http",
        "xmlrpc",
        "urllib",
        "logging",
        "doctest",
        "pdb",
        "distutils",
        "setuptools",
        "pip",
        "PyQt5",
        "matplotlib",
    ],
    "optimize": 2
}

base = "gui" if sys.platform == "win32" else None

executables = [
    Executable(
        "smp12c_vibrodiag/main.py",
        base=base,
        target_name="KWF_Prometheus.exe",
        icon=None
    )
]

setup(
    name="KWF_Prometheus",
    version="1.3.0",
    description="Анализатор вибрационной диагностики ветротурбин SMP12C",
    author="NLP-Core-Team",
    options={"build_exe": build_exe_options},
    executables=executables
)

