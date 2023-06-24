import numpy as np
import os
import tomllib
import pathlib
from ctypes import POINTER
from map_server.utils import AreaData
from map_server.utils.data import EnumDifficulty
from map_server.utils.data import EnumAct
from map_server.session.Map import Map
from map_server.pyWrappers import Act
from map_server.pyWrappers import ApiWrapper


class Session:
    def __init__(self):
        self._seed = None
        self._difficulty = None
        self.acts = (POINTER(Act) * 5)()
        self.session = dict()

        root = pathlib.Path(__file__)
        while root.name != "rpyc-d2-map-api":
            root = root.parent

        with open(os.path.join(root, "settings.toml"), "rb") as file:
            settings = tomllib.load(file)

        self.d2api = ApiWrapper(bytes(settings["diablo2"]["path"], 'utf8'))
        if not self.d2api.initialize():
            raise ValueError("Failed to initialize Diablo 2 Lod 13.c")

    def obtain_map_data(self, area, position):
        assert self._seed is not None or self._difficulty is not None

        act = EnumAct.FromArea(area)
        act_index = act.code

        if self.session.get(area):
            return self.session[area]

        if not self.acts[act.value]:
            print(f"[!] Init Act: {act.value}, difficulty: {self._difficulty.value}, act_index: {act_index}, seed: {hex(self._seed)}")
            self.acts[act.value] = self.d2api.load_act(act.value, self._seed, self._difficulty.value, act_index)

        area_map = Map(self.d2api, area)
        area_map.build_coll_map(self.acts[act.value], area)
        area_map.generate_coll_map()
        area_map.add_outdoor_exits(position)

        exits = dict()
        adjacent_levels = dict()
        for k, v in area_map.adjacent_levels.items():
            if v["exits"] is not None:
                exits[k] = v["exits"]
            else:
                adjacent_levels[k] = v

        data = {
            "map": np.asarray(area_map.map),
            "area": area,
            "size": area_map.size,
            "origin": (area_map.originX, area_map.originY),
            "weights": area_map.weights.transpose(),
            "adjacent_levels": adjacent_levels,
            "waypoint": area_map.waypoint,
            "exits": exits,
            "tomb_area": area_map.tomb_area
        }

        self.session[area] = AreaData(**data)
        return self.session[area]

    @property
    def seed(self):
        return self._seed

    @seed.setter
    def seed(self, s):
        for act_ptr in self.acts:
            if act_ptr:
                self.d2api.unload_act(act_ptr)

        self.acts = (POINTER(Act) * 5)()
        self.session.clear()
        self._seed = s

    @property
    def difficulty(self):
        return self._difficulty

    @difficulty.setter
    def difficulty(self, d):
        self._difficulty = EnumDifficulty(d)
