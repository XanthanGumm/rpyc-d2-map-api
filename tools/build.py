import sys
import os
import pathlib
import subprocess
from venv import create


def main():
    """
    Script which creates venv and install map_server module for the server side.
    """
    is_64bits = sys.maxsize > 2 ** 32
    if is_64bits:
        raise Exception("rpyc-map-api can only run on 32 bit version of python")

    root = pathlib.Path(__file__).parent.parent
    print(os.path.join(root, "venv"))
    if not os.path.isdir(os.path.join(root, "venv")):
        venv_dir = os.path.join(root, "venv")
        create(venv_dir, with_pip=True)
        subprocess.run([os.path.join(root, "venv", "Scripts", "pip.exe"), "install", "."],
                       stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    main()
