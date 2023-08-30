import rpyc
from map_server.session import Session


class MapService(rpyc.Service):
    _session = None

    def on_connect(self, conn):
        print("Client Connected")
        # self._session = Session()

    def initialize(self, callback):
        callback = rpyc.async_(callback)
        self._session = Session(callback)

    @rpyc.exposed
    def map_seed(self):
        return self._session.seed

    @rpyc.exposed
    def set_map_seed(self, seed):
        self._session.seed = seed

    @rpyc.exposed
    def get_difficulty(self):
        return self._session.difficulty

    @rpyc.exposed
    def set_difficulty(self, d):
        self._session.difficulty = d

    @rpyc.exposed
    def read_map_data(self, area: int, position: tuple | None = None):
        return self._session.read_map_data(area, position)

    @rpyc.exposed
    def generate_map_image(self, area, scale=0.0, upscale=False, player_position=None, verbose=False):
        return self._session.generate_level_image(area, scale, upscale, player_position, verbose)

    def on_disconnect(self, conn):
        pass
