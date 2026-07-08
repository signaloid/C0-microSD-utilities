#!/usr/bin/env python3

# Copyright (c) 2026, Signaloid.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import hashlib
import importlib
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional


def load_regmap_namespace(
    default_module: str,
    package: str,
    top_attr: str,
    regmap_path: Optional[str] = None,
):
    """Return the top-level regmap namespace class (e.g. ``Top``).

    When ``regmap_path`` is None, import the in-tree regmap package
    ``default_module`` relative to ``package`` and return its
    ``top_attr`` attribute. Otherwise load the regmap package whose
    directory is ``regmap_path`` (it must contain an ``__init__.py``)
    from the filesystem, honouring the package's internal relative
    imports, and return its ``top_attr`` attribute.

    Args:
        default_module: Dotted module name of the in-tree regmap package,
            resolved relative to ``package`` (e.g.
            ``".regmaps.c0microsdplus"``).
        package: Anchor package for the relative ``default_module``
            import (typically the caller's ``__package__``).
        top_attr: Name of the top-level namespace attribute to return
            from the package (e.g. ``"Top"``).
        regmap_path: Optional path to an alternative regmap package
            directory. When None, the in-tree package is used.

    Returns:
        The ``top_attr`` attribute of the loaded regmap package.

    Raises:
        FileNotFoundError: If ``regmap_path`` has no ``__init__.py``.
        AttributeError: If the package has no ``top_attr`` attribute.
    """
    if regmap_path is None:
        module: ModuleType = importlib.import_module(default_module, package)
    else:
        package_dir = Path(regmap_path).expanduser().resolve()
        init_file = package_dir / "__init__.py"
        if not init_file.is_file():
            raise FileNotFoundError(
                f"No regmap package found at {package_dir} "
                "(expected an __init__.py)."
            )
        # Unique, collision-proof module name derived from the absolute
        # package directory. Loading a regmap from a path must never clash
        # with an installed module or with another regmap that happens to
        # share the same directory basename. The name is flat (no dots) and
        # the basename is sanitised, so directories with non-identifier
        # names (hyphens, dots) are safe; the path-derived digest makes the
        # name stable, so re-loading the same path overwrites only its own
        # entry.
        digest = hashlib.sha256(str(package_dir).encode()).hexdigest()[:16]
        safe_base = re.sub(r"[^0-9A-Za-z_]", "_", package_dir.name)
        module_name = f"_signaloid_regmap_{safe_base}_{digest}"

        spec = importlib.util.spec_from_file_location(
            module_name,
            str(init_file),
            submodule_search_locations=[str(package_dir)],
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load regmap package from {init_file}.")
        module = importlib.util.module_from_spec(spec)
        # Register under the unique name so the regmap's internal relative
        # imports (e.g. ``from .top_regs import Top``) resolve.
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return getattr(module, top_attr)
