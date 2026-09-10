"""
Step 1 tests: SkillLoader module allowlist.

Proves:
- blessed (backend.*) modules load exactly as before (import + getattr +
  cache + original error propagation for missing attributes),
- stdlib / third-party / malformed / traversal paths are rejected with
  ValueError BEFORE any import is attempted,
- dunder handler names are rejected,
- per-instance narrowing works.
"""

from __future__ import annotations

import pytest

from backend.hermes_engine.skills.skill_loader import (
    ALLOWED_MODULE_PREFIXES,
    SkillLoader,
    is_allowed_module,
)


@pytest.fixture
def loader():
    return SkillLoader()


class TestAllowlistPredicate:
    def test_default_prefixes(self):
        assert ALLOWED_MODULE_PREFIXES == ("backend.",)

    @pytest.mark.parametrize("path", [
        "backend.hermes_engine.skills.skill_creator",
        "backend.rag.retriever",
        "backend.api.skills",
        "backend.x",
    ])
    def test_blessed_paths_allowed(self, path):
        assert is_allowed_module(path) is True

    @pytest.mark.parametrize("path", [
        "os", "sys", "subprocess", "importlib", "pytest", "requests",
        "backend",  # bare top package: prefix requires the dotted form
        "..", ".", "", " ", "backend..evil", ".backend.x", "backend.x.",
        "backend/x", "backend\\x", " backend.x", "backend.x ",
        "backend.x;import os", "'backend.x'", "backend .x",
        None, 123, ["backend.x"], "backend.9lives",
    ])
    def test_disallowed_paths_rejected(self, path):
        assert is_allowed_module(path) is False

    def test_empty_allowlist_rejects_all(self):
        assert is_allowed_module("backend.x", ()) is False


class TestLoadFromModule:
    def test_allowed_module_loads_and_caches(self, loader):
        func = loader.load_from_module(
            "backend.hermes_engine.skills.skill_creator", "SkillCreator")
        from backend.hermes_engine.skills.skill_creator import SkillCreator

        assert func is SkillCreator
        assert loader.get_loaded()[
            "backend.hermes_engine.skills.skill_creator.SkillCreator"] is SkillCreator

    def test_missing_attribute_still_raises_attribute_error(self, loader):
        # Post-allowlist failures propagate unchanged (behavior preserved).
        with pytest.raises(AttributeError):
            loader.load_from_module("backend.hermes_engine.skills.skill_creator",
                                    "NoSuchSkill")

    @pytest.mark.parametrize("path", ["os", "sys", "subprocess", "pytest", "requests"])
    def test_stdlib_and_third_party_rejected(self, loader, path):
        with pytest.raises(ValueError, match="non-allowlisted module"):
            loader.load_from_module(path, "anything")
        assert loader.get_loaded() == {}

    @pytest.mark.parametrize("path", ["..", "backend..x", "backend/x", "", "backend"])
    def test_malformed_paths_rejected(self, loader, path):
        with pytest.raises(ValueError, match="non-allowlisted module"):
            loader.load_from_module(path, "anything")

    @pytest.mark.parametrize("name", ["__class__", "__subclasses__", "_private", "not a name", ""])
    def test_dunder_and_invalid_handler_names_rejected(self, loader, name):
        with pytest.raises(ValueError, match="invalid handler name"):
            loader.load_from_module("backend.hermes_engine.skills.skill_creator", name)

    def test_rejection_precedes_import(self, loader, monkeypatch):
        import importlib as std_importlib

        called = []

        def _spy(*args, **kwargs):
            called.append(args)
            return std_importlib.import_module(*args, **kwargs)

        monkeypatch.setattr("importlib.import_module", _spy)
        with pytest.raises(ValueError):
            loader.load_from_module("os", "system")
        assert called == []

    def test_per_instance_narrowing(self):
        narrow = SkillLoader(allowed_prefixes=("backend.hermes.",))
        narrow.load_from_module("backend.hermes.memory.manager", "MemoryManager")
        with pytest.raises(ValueError, match="non-allowlisted module"):
            narrow.load_from_module("backend.rag.retriever", "RetrieverBase")
