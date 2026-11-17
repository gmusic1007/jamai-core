"""jamai_env — the jamai settings, for the Python parts of the package.

Same order as lib/jamai-env.sh, first match wins: the environment, jamai.env,
secrets.env, the default in `settings`.

    import jamai_env
    cfg = jamai_env.load()          # also fills os.environ, without overwriting it
    cfg["JAMAI_MELODY_DIR"]
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.environ.get("JAMAI_CONFIG_DIR") or os.path.join(base, "jamai")


def read_env_file(path):
    values = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key and all(c.isupper() or c.isdigit() or c == "_" for c in key):
                    values[key] = value
    except OSError:
        pass
    return values


def manifest():
    """The declared settings: a list of (name, kind, default, description)."""
    rows = []
    try:
        with open(os.path.join(ROOT, "settings"), encoding="utf-8") as fh:
            for line in fh:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                parts = [p.strip() for p in line.rstrip("\n").split("|", 3)]
                if len(parts) == 4 and parts[0]:
                    rows.append(tuple(parts))
    except OSError:
        pass
    return rows


def load():
    cfg = {}
    for name, kind, default, _ in manifest():
        if kind in ("secret", "auto") or not default:
            continue
        cfg[name] = os.path.expanduser(default) if default.startswith("~/") else default
    cfg.update(read_env_file(os.path.join(config_dir(), "secrets.env")))
    cfg.update(read_env_file(os.path.join(config_dir(), "jamai.env")))
    cfg.update({k: v for k, v in os.environ.items() if k.startswith(("JAMAI_", "GMUSIC_"))})
    cfg.setdefault("JAMAI_CORE_ROOT", ROOT)
    for key, value in cfg.items():
        os.environ.setdefault(key, value)
    return cfg
