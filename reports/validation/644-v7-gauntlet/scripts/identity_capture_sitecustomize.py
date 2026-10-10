"""Execution-identity capture for the #644 v7 Gauntlet validation (records imports; changes nothing)."""
import atexit, hashlib, json, os, sys


def _record():
    pkg = sys.modules.get("agentmem_ref")
    if pkg is None:
        return
    root = os.path.dirname(os.path.abspath(pkg.__file__))
    loaded = {}
    for name, mod in list(sys.modules.items()):
        path = getattr(mod, "__file__", None)
        if path and os.path.abspath(path).startswith(root + os.sep) and path.endswith(".py"):
            data = open(path, "rb").read()
            loaded[os.path.relpath(path, root)] = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    out = {"pid": os.getpid(), "argv": sys.argv, "executable": sys.executable, "python": sys.version.split()[0],
           "agentmem_ref_root": root, "loaded_module_blobs": dict(sorted(loaded.items()))}
    target = os.environ.get("V7G_IDENTITY_DIR")
    if target:
        with open(os.path.join(target, f"identity-{os.getpid()}.json"), "w") as fh:
            json.dump(out, fh, indent=1, sort_keys=True)


atexit.register(_record)
