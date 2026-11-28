"""jamai_extras — the optional listening libraries, and the Python that holds them.

Three listen/ tools need libraries too heavy to ask of every install: faster-whisper (lyrics),
Demucs (separating the voice from the guitar) and basic-pitch (the notes of a sung line).
`jamai listen-setup` installs them, at the versions measured together in
listen/requirements.txt, into one virtual environment: JAMAI_LISTEN_VENV.

A tool calls require() before importing them. When the Python running it lacks them, it
re-runs itself with the Python of that environment, so the same command works from a
terminal, from jamai-mcp and from a script. When that environment does not exist either, it
says how to make it and exits 3.

Standard library only: this module must load in a Python that has nothing.
"""
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import jamai_env  # noqa: E402

EXIT_MISSING = 3


def listen_python():
    """The Python of JAMAI_LISTEN_VENV, or None when that environment does not exist."""
    venv = jamai_env.load().get("JAMAI_LISTEN_VENV") or ""
    py = os.path.join(os.path.expanduser(venv), "bin", "python")
    return py if venv and os.access(py, os.X_OK) else None


def missing(modules):
    return [m for m in modules if importlib.util.find_spec(m) is None]


def require(modules, what):
    """Make sure `modules` import here, re-running the script in JAMAI_LISTEN_VENV if needed."""
    lack = missing(modules)
    if not lack:
        return
    py = listen_python()
    here = os.path.realpath(sys.executable)
    if py and os.path.realpath(py) != here and not os.environ.get("JAMAI_LISTEN_REEXEC"):
        os.environ["JAMAI_LISTEN_REEXEC"] = "1"
        script = os.path.realpath(sys.argv[0])
        os.execv(py, [py, script] + sys.argv[1:])
    venv = jamai_env.load().get("JAMAI_LISTEN_VENV") or "(JAMAI_LISTEN_VENV is empty)"
    sys.stderr.write(
        "  ✗ %s needs %s, which this Python (%s) does not have.\n"
        "    Install the listening libraries once:   jamai listen-setup\n"
        "    It makes %s with the versions in listen/requirements.txt.\n"
        "    Already have them elsewhere?            jamai config set JAMAI_LISTEN_VENV <that venv>\n"
        % (what, ", ".join(lack), sys.executable, venv))
    sys.exit(EXIT_MISSING)
