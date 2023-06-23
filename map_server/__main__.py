import sys
from map_server.MapService import MapService
from rpyc.utils.server import ThreadedServer


def main():
    is_64bits = sys.maxsize > 2 ** 32
    if is_64bits:
        raise Exception("rpyc-map-api can only run on 32 bit version of python")

    try:
        print("[!] RPC server is up.")
        server = ThreadedServer(MapService, port=18861, protocol_config={
            'allow_public_attrs': True,
            'allow_setattr': True,
            'allow_pickle': True
        })
        server.start()
    except Exception as e:
        print(e)
        print("[!] Exiting RPC server.")


if __name__ == "__main__":
    main()
