"""Regression tests for profile name sanitization (path traversal + empty + collision)."""

from __future__ import annotations

import pytest

from fastslr.app import profiles


@pytest.fixture(autouse=True)
def _isolated_profiles_dir(tmp_path, monkeypatch):
    """Point the profiles dir at a temp path so tests never touch ~/.fastslr."""
    target = tmp_path / "profiles"
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(profiles, "_profiles_dir", lambda: target)
    return target


def test_save_profile_confines_path_traversal(_isolated_profiles_dir):
    """save_profile must neutralize traversal: the file stays inside the dir."""
    path = profiles.save_profile("../../../evil", {})

    # Sanitized to a safe name confined to the profiles dir; nothing escapes.
    assert path.parent == _isolated_profiles_dir
    assert path.resolve().is_relative_to(_isolated_profiles_dir.resolve())

    parent = _isolated_profiles_dir.parent
    assert not (parent / "evil.json").exists()
    assert not (parent.parent / "evil.json").exists()
    assert path.exists()


def test_save_profile_rejects_empty_name(_isolated_profiles_dir):
    """save_profile must reject empty names (avoids hidden '.json')."""
    with pytest.raises(ValueError):
        profiles.save_profile("", {})

    assert not (_isolated_profiles_dir / ".json").exists()


def test_save_profile_rejects_name_with_only_separators(_isolated_profiles_dir):
    """A name that sanitizes to empty must also be rejected."""
    with pytest.raises(ValueError):
        profiles.save_profile("///", {})


def test_load_profile_confines_path_traversal(_isolated_profiles_dir):
    """load_profile must look only inside the profiles dir (no escape read)."""
    # Sanitizes to an in-dir name that does not exist -> FileNotFoundError,
    # never reaching a file outside the directory.
    with pytest.raises(FileNotFoundError):
        profiles.load_profile("../../../etc/passwd")


def test_delete_profile_confines_path_traversal(_isolated_profiles_dir):
    """delete_profile must not unlink files outside the profiles dir."""
    outside = _isolated_profiles_dir.parent / "secret.json"
    outside.write_text("{}", encoding="utf-8")

    # Sanitizes to in-dir 'secret' which does not exist -> returns False.
    assert profiles.delete_profile("../secret") is False

    # The outside file must remain untouched.
    assert outside.exists()


def test_round_trip_valid_name(_isolated_profiles_dir):
    """A valid profile name round-trips through save/load/list/delete."""
    config = {"alpha": 1, "beta": "two"}
    path = profiles.save_profile("My Profile", config, description="desc")

    # Sanitized to a safe name inside the profiles dir.
    assert path.parent == _isolated_profiles_dir
    assert path.name == "my_profile.json"
    assert path.exists()

    loaded = profiles.load_profile("My Profile")
    assert loaded == config

    listed = profiles.list_profiles()
    names = [p.name for p in listed]
    assert "My Profile" in names

    assert profiles.delete_profile("My Profile") is True
    assert not path.exists()
    assert profiles.delete_profile("My Profile") is False


def test_sanitized_collision_maps_to_same_file(_isolated_profiles_dir):
    """Names that differ only by separators/case map to the same sanitized file."""
    profiles.save_profile("My Profile", {"v": 1})
    profiles.save_profile("my   profile!!!", {"v": 2})

    # Both sanitize to 'my_profile.json' (collision overwrites, stays in-dir).
    json_files = list(_isolated_profiles_dir.glob("*.json"))
    assert len(json_files) == 1
    assert json_files[0].name == "my_profile.json"
    # Last write wins.
    assert profiles.load_profile("My Profile") == {"v": 2}
