import rpyc
from map_server.session import Session


class MapService(rpyc.Service):
    _session = None

    def on_connect(self, conn) -> None:
        self._session = Session()

    @rpyc.exposed
    def map_seed(self) -> int:
        return self._session.seed

    @rpyc.exposed
    def set_map_seed(self, seed: int):
        self._session.seed = seed

    @rpyc.exposed
    def get_difficulty(self) -> int:
        return self._session.difficulty

    @rpyc.exposed
    def set_difficulty(self, d: int):
        self._session.difficulty = d

    @rpyc.exposed
    def get_level_data(self, area: int, position: tuple[float, float]) -> dict:
        return self._session.get_level_data(area, position)

    @rpyc.exposed
    def get_level_map(self, area: int) -> bytes:
        return self._session.get_level_map(area)

    def on_disconnect(self, conn) -> None:
        pass
