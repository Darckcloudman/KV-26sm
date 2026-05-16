"""Setup для сборки SMP12C VibroDiag Analyzer через cx_Freeze"""

from cx_Freeze import setup, Executable
import sys

build_exe_options = {
    "packages": [
        "numpy",
        "scipy",
        "PyQt5",
        "encodings",
        "xml.parsers",
        "xml.parsers.expat",
        "plistlib"
    ],
    "includes": ["numpy", "scipy"],
    "include_files": [],
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
        "pip"
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
    name="SMP12C_VibroDiag",
    version="2.0.0",
    description="Анализатор вибрационной диагностики ветротурбин SMP12C",
    author="NLP-Core-Team",
    options={"build_exe": build_exe_options},
    executables=executables
)
