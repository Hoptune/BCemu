"""
Compatibility shim for stdlib ``imp`` removed in Python 3.13.

BCemu (via smt==1.0.0 -> pyDOE2) still imports ``imp``.
This module installs a lightweight replacement early in package import.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import os
import sys
import types


def install_imp_compat() -> None:
    """Install a minimal ``imp`` module on Python 3.13+ if needed."""
    if "imp" in sys.modules or sys.version_info < (3, 13):
        return

    imp_mod = types.ModuleType("imp")
    imp_mod.PY_SOURCE = 1
    imp_mod.PY_COMPILED = 2
    imp_mod.C_EXTENSION = 3
    imp_mod.PKG_DIRECTORY = 5

    def get_magic():
        return importlib.util.MAGIC_NUMBER

    def get_suffixes():
        out = []
        out.extend((s, "r", imp_mod.PY_SOURCE) for s in importlib.machinery.SOURCE_SUFFIXES)
        out.extend((s, "rb", imp_mod.PY_COMPILED) for s in importlib.machinery.BYTECODE_SUFFIXES)
        out.extend((s, "rb", imp_mod.C_EXTENSION) for s in importlib.machinery.EXTENSION_SUFFIXES)
        return out

    def find_module(name, path=None):
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None:
            raise ImportError("No module named {!r}".format(name))
        if spec.submodule_search_locations is not None:
            return None, spec.origin, ("", "", imp_mod.PKG_DIRECTORY)
        origin = spec.origin
        if origin is None:
            raise ImportError("Cannot resolve module {!r}".format(name))
        suffix = os.path.splitext(origin)[1]
        mode = "rb"
        typ = imp_mod.PY_COMPILED
        if suffix in importlib.machinery.SOURCE_SUFFIXES:
            mode = "r"
            typ = imp_mod.PY_SOURCE
        elif suffix in importlib.machinery.EXTENSION_SUFFIXES:
            typ = imp_mod.C_EXTENSION
        return open(origin, mode), origin, (suffix, mode, typ)

    def load_module(name, file=None, filename=None, details=None):
        if name in sys.modules:
            return sys.modules[name]
        if filename is None:
            return importlib.import_module(name)
        spec = importlib.util.spec_from_file_location(name, filename)
        if spec is None or spec.loader is None:
            return importlib.import_module(name)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    def new_module(name):
        return types.ModuleType(name)

    def reload(module):
        return importlib.reload(module)

    imp_mod.get_magic = get_magic
    imp_mod.get_suffixes = get_suffixes
    imp_mod.find_module = find_module
    imp_mod.load_module = load_module
    imp_mod.new_module = new_module
    imp_mod.reload = reload

    sys.modules["imp"] = imp_mod
