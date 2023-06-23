import rpyc
from map_server.session import Session


class MapService(rpyc.Service):

    _session = None

    def on_connect(self, conn):
        self._session = Session()

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
    def obtain_map_data(self, area: int, position: tuple | None = None):
        return self._session.obtain_map_data(area, position)

    def on_disconnect(self, conn):
        pass
