import importlib.util
if not importlib.util.find_spec("pyastar2d"):
    import sys
    import os
    import pathlib

    root = pathlib.Path(__file__)
    while root != "rpyc-d2-map-api":
        root = root.parent

    sys.path.insert(0, os.path.join(root, "dep"))

