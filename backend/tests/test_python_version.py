"""uv installs the Python for the packaged app, so the project must name one that works."""

import re
import tomllib
from pathlib import Path

from packaging.specifiers import SpecifierSet

BACKEND = Path(__file__).resolve().parent.parent
# Wheel file names end in `-<python tag>-<abi tag>-<platform tag>.whl`.
WHEEL_TAGS = re.compile(r"-([^-]+)-([^-]+)-[^-]+\.whl$")


def wheel_supports(url: str, minor: int) -> bool:
    python_tags, abi_tags = WHEEL_TAGS.search(url).groups()
    for tag in python_tags.split("."):
        if tag in ("py3", "py2.py3"):
            return True
        built_for = re.fullmatch(r"cp3(\d+)", tag)
        if built_for is None:
            continue
        if int(built_for.group(1)) == minor:
            return True
        if "abi3" in abi_tags.split(".") and int(built_for.group(1)) < minor:
            return True
    return False


def test_every_allowed_python_can_install_every_locked_package():
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text())
    lock = tomllib.loads((BACKEND / "uv.lock").read_text())
    allowed = SpecifierSet(project["project"]["requires-python"])
    # Far enough ahead to notice a missing upper bound.
    minors = [minor for minor in range(8, 30) if allowed.contains(f"3.{minor}.0")]

    missing = [
        f"{package['name']} on Python 3.{minor}"
        for package in lock["package"]
        # A package with a source distribution can be built for any Python.
        if "sdist" not in package and package.get("wheels")
        for minor in minors
        if not any(wheel_supports(wheel["url"], minor) for wheel in package["wheels"])
    ]

    assert missing == []


def test_pinned_python_is_one_the_project_allows():
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text())
    pinned = (BACKEND / ".python-version").read_text().strip()

    assert re.fullmatch(r"3\.\d+", pinned)
    assert SpecifierSet(project["project"]["requires-python"]).contains(f"{pinned}.0")
