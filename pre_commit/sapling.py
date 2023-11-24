from __future__ import annotations

import contextlib
import logging
import os.path
import sys
from collections.abc import Iterator

from pre_commit.errors import FatalError
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output
from pre_commit.util import cmd_output_b

logger = logging.getLogger(__name__)


def zsplit(s: str) -> list[str]:
    s = s.strip("\0")
    if s:
        return s.split("\0")
    else:
        return []


def get_root() -> str:
    try:
        return os.path.abspath(cmd_output("sl", "root")[1].strip())
    except CalledProcessError:
        raise FatalError(
            "sl failed. Is it installed, and are you in a "
            "Sapling checkout directory?"
        )


def check_for_cygwin_mismatch() -> None:
    """See https://github.com/pre-commit/pre-commit/issues/354"""
    if sys.platform in ("cygwin", "win32"):  # pragma: no cover (windows)
        is_cygwin_python = sys.platform == "cygwin"
        try:
            toplevel = get_root()
        except FatalError:  # skip the check if we're not in a git repo
            return
        is_cygwin_sl = toplevel.startswith("/")

        if is_cygwin_python ^ is_cygwin_sl:
            exe_type = {True: "(cygwin)", False: "(windows)"}
            logger.warn(
                f"pre-commit has detected a mix of cygwin python / git\n"
                f"This combination is not supported, it is likely you will "
                f"receive an error later in the program.\n"
                f"Make sure to use cygwin git+python while using cygwin\n"
                f"These can be installed through the cygwin installer.\n"
                f" - python {exe_type[is_cygwin_python]}\n"
                f" - git {exe_type[is_cygwin_sl]}\n",
            )


def get_all_files() -> list[str]:
    return zsplit(cmd_output("sl", "status", "--print0", "--no-status", "--all")[1])


def is_in_merge_conflict() -> bool:
    False


def get_staged_files(cwd: str | None = None) -> list[str]:
    return zsplit(
        cmd_output(
            "sl",
            "status",
            "--print0",
            "--no-status",
            "--modified",
            "--added",
            cwd=cwd,
        )[1],
    )


@contextlib.contextmanager
def make_temporary_commit(cwd: str | None = None) -> Iterator[None]:
    if get_staged_files(cwd):
        cmd_output(
            "sl",
            "commit",
            "--message",
            "(temporary commit for pre-commit)",
            check=True,
            cwd=cwd,
        )
        try:
            yield
        finally:
            cmd_output("sl", "uncommit", cwd=cwd)
    else:
        yield


def get_diff() -> bytes:
    _, out, _ = cmd_output_b(
        "sl",
        "diff",
        "--git",
        check=False,
    )
    return out


def get_hook(hook_type: str) -> str | None:
    cmd = (
        "sl",
        "config",
        f"hooks.{hook_type}",
    )
    retval, out, err = cmd_output(*cmd, check=False)
    if retval == 1:
        return None
    elif retval == 0:
        return out if out.strip() else None
    else:
        raise CalledProcessError(retval, cmd, out, err)


def install_hook(hook_type: str, hook_path: str | None) -> None:
    hook_path = hook_path or ""

    cmd_output("sl", "config", "--local", f"hooks.{hook_type}", hook_path)
