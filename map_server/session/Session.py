import os
import pathlib
import tomllib
import pickle
from ctypes import POINTER
import numpy as np
from cachetools import cached
from cachetools.keys import hashkey
from map_server.pyWrappers import Act
from map_server.pyWrappers import ApiWrapper
from map_server.session.Map import Map
from map_server.utils.data import EnumAct
from map_server.utils.data import EnumDifficulty


class Session:
    def __init__(self):
        self._seed: int = 0
        self._difficulty: EnumDifficulty | None = None
        self._acts = (POINTER(Act) * 5)()

        root = pathlib.Path(__file__)
        while root.name != "rpyc-d2-map-api":
            root = root.parent

        with open(os.path.join(root, "settings.toml"), "rb") as file:
            settings = tomllib.load(file)

        if not os.path.isdir(settings["diablo2"]["path"]):
            raise ValueError(f"[!] Cannot find Diablo II lod 1.13c path: {settings['diablo2']['path']}")

        self.d2api = ApiWrapper(bytes(settings["diablo2"]["path"], "utf8"))
        if not self.d2api.initialize():
            raise ValueError("[!] Failed to initialize Diablo 2 Lod 13.c")

    @cached(cache={}, key=lambda self, area: hashkey(area))
    def read_level(self, area):

        act = EnumAct.FromArea(area)
        act_index = act.code

        if not self._acts[act.value]:
            self._acts[act.value] = self.d2api.load_act(act.value, self._seed, self._difficulty.value, act_index)

        level = Map(self.d2api, area)
        level.build_coll_map(self._acts[act.value], area)

        return level

    @cached(cache={}, key=lambda self, area: hashkey(area))
    def get_level_map(self, area: int):
        level = self.read_level(area)

        map_grid = np.asarray(level.map, np.int32)
        h, w = map_grid.shape

        # add exits and waypoints here
        # exits = ...
        # waypoint = ...

        pickled_level = pickle.dumps((map_grid.tobytes(), h, w))
        return bytes(pickled_level)

    def get_level_data(self, area: int, position: tuple[float, float]):
        level = self.read_level(area)
        level.generate_coll_map()
        level.add_outdoor_exits(position)

        return {
            # later if needed return the grid as well
            "area": area,
            "size": level.size,
            "origin": (level.originX, level.originY),
            "exits": {name: lvl for name, lvl in level.adjacent_levels.items() if lvl["exits"]},
            "adjacent_levels": {name: lvl for name, lvl in level.adjacent_levels.items() if not lvl["exits"]},
            "waypoint": level.waypoint,
            "tomb_area": level.tomb_area
        }

    def clear(self):
        self.read_level.cache.clear()
        self.get_level_map.cache.clear()

        for p_act in self._acts:
            if p_act:
                self.d2api.unload_act(p_act)

        self._acts = (POINTER(Act) * 5)()

    @property
    def seed(self):
        return self._seed

    @seed.setter
    def seed(self, s):
        self.clear()
        self._seed = s

    @property
    def difficulty(self):
        return self._difficulty

    @difficulty.setter
    def difficulty(self, d):
        self._difficulty = EnumDifficulty(d)
