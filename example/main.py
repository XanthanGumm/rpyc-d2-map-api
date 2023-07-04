import os
import pathlib
import subprocess
import rpyc
from PIL import Image


def main():
    root = pathlib.Path(__file__).parent.parent
    python_exe = os.path.join(root, "venv", "Scripts", "python.exe")
    server_proc = subprocess.Popen([python_exe, "-m", "map_server"])
    try:
        if server_proc.poll() is not None:
            raise Exception("Failed to start RPC server")

        example_seed = 0x525b4cfd
        # 0 normal = 0, nightmare = 1, hell = 2
        difficulty = 2
        # blood moor area
        blood_moor = 2

        dummy_player_position = (5720, 5640)

        rpyc_conn = rpyc.connect("localhost", port=18861)
        rpyc_conn.root.set_map_seed(example_seed)
        rpyc_conn.root.set_difficulty(difficulty)

        map_data = rpyc_conn.root.read_map_data(blood_moor, dummy_player_position)
        image = rpyc_conn.root.generate_map_image(blood_moor)

    finally:
        server_proc.terminate()


if __name__ == '__main__':
    main()
