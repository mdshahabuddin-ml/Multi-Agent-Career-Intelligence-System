"""
Skill Loader - Loads skills from files or modules.

SECURITY (Step 1 hardening): :meth:`SkillLoader.load_from_module` only
imports modules under an explicit allowlist of blessed prefixes
(``ALLOWED_MODULE_PREFIXES``). Anything else — stdlib, third-party,
absolute/traversal/malformed paths — is rejected with ``ValueError``
BEFORE any import is attempted. This keeps a future LLM-influenced
``module_path`` from becoming an arbitrary-code import.
"""

from __future__ import annotations

import importlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Blessed import roots for skill code. First-party project modules only:
# ``backend.`` covers every in-repo skill implementation while excluding
# stdlib (os/sys/subprocess/…), site-packages, and anything else on
# sys.path. Narrow per instance via ``SkillLoader(allowed_prefixes=...)``.
ALLOWED_MODULE_PREFIXES: Tuple[str, ...] = ("backend.",)

# Dotted module path shape: identifiers separated by single dots, no
# leading/trailing/empty segments (rejects "..", "/", quotes, spaces…).
_MODULE_PATH_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+")

# Handler names must be public identifiers (rejects dunders such as
# __class__/__subclasses__ gadget vectors).
_FUNCTION_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def is_allowed_module(module_path: Any, allowed_prefixes: Tuple[str, ...] = ALLOWED_MODULE_PREFIXES) -> bool:
    """True only for well-formed paths under a blessed prefix (no import)."""
    if not isinstance(module_path, str):
        return False
    if _MODULE_PATH_RE.fullmatch(module_path) is None:
        return False
    if not allowed_prefixes:
        return False
    return module_path.startswith(tuple(allowed_prefixes))


class SkillLoader:
    """
    Loads skills from files, modules, or configurations.
    """

    def __init__(self, allowed_prefixes: Optional[Tuple[str, ...]] = None):
        self._loaded: Dict[str, Any] = {}
        self._allowed_prefixes = tuple(allowed_prefixes) if allowed_prefixes is not None else ALLOWED_MODULE_PREFIXES

    def load_from_module(
        self,
        module_path: str,
        function_name: str,
    ) -> Any:
        """Load a skill from a module.

        Raises:
            ValueError: If ``module_path`` is outside the allowlist,
                malformed, or ``function_name`` is not a public identifier.
                Import/attribute errors for ALLOWED modules propagate
                unchanged, exactly as before.
        """
        if not is_allowed_module(module_path, self._allowed_prefixes):
            raise ValueError(
                f"Refused to load skill from non-allowlisted module: {str(module_path)[:120]!r} "
                f"(allowed prefixes: {list(self._allowed_prefixes)})"
            )
        if (not isinstance(function_name, str)
                or _FUNCTION_NAME_RE.fullmatch(function_name) is None
                or function_name.startswith("_")):
            raise ValueError(
                f"Refused to load skill with invalid handler name: {str(function_name)[:80]!r}"
            )
        try:
            module = importlib.import_module(module_path)
            func = getattr(module, function_name)
            self._loaded[f"{module_path}.{function_name}"] = func
            return func
        except Exception as e:
            logger.error(f"Failed to load skill from {module_path}: {e}")
            raise

    def load_from_config(
        self,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Load a skill from configuration."""
        return {
            "name": config.get("name", "unknown"),
            "description": config.get("description", ""),
            "module": config.get("module"),
            "function": config.get("function"),
            "parameters": config.get("parameters", {}),
        }

    def get_loaded(self) -> Dict[str, Any]:
        """Get all loaded skills."""
        return dict(self._loaded)
