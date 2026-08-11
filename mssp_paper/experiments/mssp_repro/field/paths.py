"""
Locating the field archives, on a filesystem that may or may not care about
case.

WHY THIS MODULE EXISTS
----------------------
The published notebooks open `../NASA_Bearing/IMS`. The directory on disk is
`NASA_bearing/IMS`. Both work on macOS, whose default filesystem is
case-insensitive, and neither works on Linux. The discrepancy therefore
survived every run the author made and would have failed on the first machine
belonging to anyone else -- which is to say, on the machine of every reader
the reproducibility package exists for.

Rather than correcting the spelling and hoping no other case mismatch is
lurking, resolution is made explicitly case-insensitive and the resolved path
is reported, so a reader on either kind of filesystem gets the same behaviour
and can see which directory was actually opened.
"""

from pathlib import Path

__all__ = ["resolve_ci", "find_archive"]


def resolve_ci(root, *parts):
    """
    Resolve `root/parts...` treating each component case-insensitively.

    Returns the resolved `Path`. Raises `FileNotFoundError` naming the
    component that failed and listing what was actually present, which is the
    error a reader can act on; a bare "no such file" is not.
    """
    here = Path(root)
    if not here.exists():
        raise FileNotFoundError(f"archive root does not exist: {here}")
    if parts and not here.is_dir():
        raise NotADirectoryError(f"archive root is not a directory: {here}")

    for part in parts:
        if not here.is_dir():
            raise NotADirectoryError(
                f"cannot descend to {part!r}: {here} is not a directory")
        if (here / part).exists():
            here = here / part
            continue
        wanted = str(part).lower()
        matches = [c for c in here.iterdir() if c.name.lower() == wanted]
        if not matches:
            available = sorted(c.name for c in here.iterdir()
                               if not c.name.startswith("."))
            raise FileNotFoundError(
                f"{part!r} not found under {here} (searched case-insensitively). "
                f"Present: {', '.join(available[:12])}"
                + (" ..." if len(available) > 12 else ""))
        if len(matches) > 1:
            # Possible on a case-sensitive filesystem, and genuinely ambiguous.
            raise FileNotFoundError(
                f"{part!r} is ambiguous under {here}: "
                f"{', '.join(sorted(m.name for m in matches))}")
        here = matches[0]
    return here


def find_archive(name, *, explicit=None, search_from=None):
    """
    Locate a field archive, preferring an explicit path.

    `name` is the directory to look for -- "NASA_bearing" or
    "CWRU_Bearing_NumPy-main". Search proceeds upward from `search_from`,
    defaulting to this package, so that the layout used by the author (the
    archives beside the paper repository) works without configuration while an
    explicit path or the corresponding environment variable always wins.

    Returns None rather than raising: an absent archive is a reason to skip
    Layer B, not an error. The caller decides.
    """
    if explicit is not None:
        p = Path(explicit).expanduser()
        return p if p.exists() else None

    start = Path(search_from) if search_from else Path(__file__).resolve()
    if not start.is_dir():
        start = start.parent

    for base in [start, *start.parents]:
        try:
            return resolve_ci(base, name)
        except (FileNotFoundError, NotADirectoryError):
            pass
        # One level into siblings. The archives typically live beside the
        # paper repository rather than inside it -- `git/inverse_problem/`
        # next to `git/shamayam/` -- so the common ancestor is reached before
        # either, and searching only ancestors would never find them. One
        # level is enough for that layout and keeps the scan bounded; going
        # deeper would walk the whole home directory.
        try:
            children = sorted(c for c in base.iterdir()
                              if c.is_dir() and not c.name.startswith("."))
        except (PermissionError, NotADirectoryError, OSError):
            continue
        for child in children:
            try:
                return resolve_ci(child, name)
            except (FileNotFoundError, NotADirectoryError):
                continue
    return None
