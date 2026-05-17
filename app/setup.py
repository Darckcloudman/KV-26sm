"""Setup для сборки SMP12C VibroDiag Analyzer v1.2 через cx_Freeze"""

from cx_Freeze import setup, Executable
import sys

build_exe_options = {
    "packages": [
        "numpy",
        "scipy",
        "PySide6",
        "pyqtgraph",
        "encodings",
    ],
    "includes": ["numpy", "scipy", "PySide6", "pyqtgraph"],
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
        target_name="SMP12C_VibroDiag.exe",
        icon=None
    )
]

setup(
    name="SMP12C VibroDiag Analyzer",
    version="1.2",
    description="Анализатор вибрационной диагностики ветротурбин SMP12C",
    author="A.Telezhenko",
    options={"build_exe": build_exe_options},
    executables=executables
)
]

setup(
    name="SMP12C_VibroDiag",
    version="2.0.0",
    description="Анализатор вибрационной диагностики ветротурбин SMP12C",
    author="NLP-Core-Team",
    options={"build_exe": build_exe_options},
    executables=executables
)
