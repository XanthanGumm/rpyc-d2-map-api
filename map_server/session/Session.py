import io
import os
import pathlib
import tomllib
from ctypes import POINTER

import cv2
import numpy as np
from PIL import Image
from cachetools.keys import hashkey

from map_server.pyWrappers import Act
from map_server.pyWrappers import ApiWrapper
from map_server.session.Map import Map
from map_server.utils.data import EnumAct
from map_server.utils.data import EnumDifficulty


class Session:
    def __init__(self):
        self._seed = None
        self._difficulty = None
        self.acts = (POINTER(Act) * 5)()

        root = pathlib.Path(__file__)
        while root.name != "rpyc-d2-map-api":
            root = root.parent

        with open(os.path.join(root, "settings.toml"), "rb") as file:
            settings = tomllib.load(file)

        self.d2api = ApiWrapper(bytes(settings["diablo2"]["path"], "utf8"))
        if not self.d2api.initialize():
            raise ValueError("Failed to initialize Diablo 2 Lod 13.c")

    def read_map_data(self, area, position):
        assert self._seed is not None or self._difficulty is not None

        act = EnumAct.FromArea(area)
        act_index = act.code

        if not self.acts[act.value]:
            print(
                f"[!] Init Act: {act.value}, difficulty: {self._difficulty.value}, act_index: {act_index}, seed: {hex(self._seed)}"
            )
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

        return {
            "map": np.asarray(area_map.map),
            "area": area,
            "size": area_map.size,
            "origin": (area_map.originX, area_map.originY),
            "weights": area_map.weights.transpose(),
            "adjacent_levels": adjacent_levels,
            "waypoint": area_map.waypoint,
            "exits": exits,
            "tomb_area": area_map.tomb_area,
        }

    # TODO: find world origin
    # TODO: add waypoints, maze and outdoor, stash
    def generate_level_image(self, area, scale, upscale, player_position=None, verbose=False):
        map_data = self.read_map_data(area, player_position)  # handle this when removing cache
        level_map = map_data["map"]

        level_map_invert = level_map
        level_map_invert[level_map_invert == -1] = 255

        level_map = np.where((level_map == -1) | (level_map % 2 != 0), 0, 255).astype(np.uint8)

        height, width = level_map.shape[:2]
        offset = int(height)

        def cart_to_iso(indices):
            xs = indices[:, 1] - indices[:, 0] + offset
            ys = (indices[:, 1] + indices[:, 0]) // 2
            return np.array([ys, xs])

        level_map_invert_indices = np.argwhere(level_map_invert != 255)
        orthoX_invert_indices = level_map_invert_indices[:, 1]
        orthoY_invert_indices = level_map_invert_indices[:, 0]
        level_map_invert_iso_y, level_map_invert_iso_x = cart_to_iso(level_map_invert_indices)
        level_map_invert_iso = np.ones(((height + width) // 2, width + height)).astype(np.uint8) * 255
        level_map_invert_iso[level_map_invert_iso_y, level_map_invert_iso_x] = level_map_invert[
            orthoY_invert_indices, orthoX_invert_indices
        ]

        level_map_binary = cv2.bitwise_not(np.where(level_map_invert_iso % 2 != 0, 255, level_map_invert_iso))

        level_map_indices = np.argwhere(level_map != 255)
        orthoX_indices = level_map_indices[:, 1]
        orthoY_indices = level_map_indices[:, 0]
        level_map_iso_y, level_map_iso_x = cart_to_iso(level_map_indices)
        level_map_iso = np.ones(((height + width) // 2, width + height)).astype(np.uint8) * 255
        level_map_iso[level_map_iso_y, level_map_iso_x] = level_map[orthoY_indices, orthoX_indices]

        h_invert, w_invert = level_map_binary.shape[:2]
        cnts_invert, hierarchy_invert = cv2.findContours(level_map_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        level_map_cnts_invert = np.ones((h_invert, w_invert)).astype(np.uint8) * 255
        cv2.drawContours(level_map_cnts_invert, cnts_invert, -1, (0, 255, 0), cv2.FILLED)

        h, w = level_map_iso.shape[:2]
        cnts, hierarchy = cv2.findContours(level_map_iso, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        level_map_cnts = np.ones((h, w)).astype(np.uint8) * 255
        cv2.drawContours(level_map_cnts, cnts, -1, (0, 255, 0), 1)

        cnts_mask = level_map_cnts_invert == 0
        level_map_cnts[~cnts_mask] = 255

        level_map_iso_brga = cv2.cvtColor(level_map_cnts, cv2.COLOR_BGR2BGRA)
        level_map_iso_brga[0, :] = [255, 255, 255, 0]
        Bmask = np.all(level_map_iso_brga == [0, 0, 0, 255], axis=-1)
        Wmask = np.all(level_map_iso_brga == [255, 255, 255, 255], axis=-1)

        level_map_iso_brga[Bmask] = [127, 127, 127, 127]
        level_map_iso_brga[Wmask] = [255, 255, 255, 0]

        if scale:
            level_map_iso_brga = cv2.resize(
                level_map_iso_brga,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_AREA
            )

        if upscale:
            ksize = 3 if scale == 1 else 7 if 2.4 <= scale < 3.7 else 9 if 3.7 <= scale < 4.8 else 11
            level_map_iso_brga = cv2.GaussianBlur(level_map_iso_brga, (ksize - 2, ksize - 2), 0)
            level_map_iso_brga = cv2.medianBlur(level_map_iso_brga, ksize=ksize)

        level_map_iso_brga_img = Image.fromarray(level_map_iso_brga)
        img_byte_arr = io.BytesIO()
        level_map_iso_brga_img.save(img_byte_arr, format="PNG")

        if verbose:
            # show the level map INVERT after projecting to isometric view
            level_map_iso_img = Image.fromarray(level_map_binary)
            level_map_iso_img.show()

            # show the level map after projecting to isometric view
            level_map_iso_img = Image.fromarray(level_map_iso)
            level_map_iso_img.show()

            # show the contours INVERT of the level map
            level_map_cnts_img = Image.fromarray(level_map_cnts_invert)
            level_map_cnts_img.show()

            # show the contours of the level map
            level_map_cnts_img = Image.fromarray(level_map_cnts)
            level_map_cnts_img.show()

            # show the final image
            level_map_iso_brga_img.show()

        return img_byte_arr.getvalue()

    @property
    def seed(self):
        return self._seed

    @seed.setter
    def seed(self, s):
        for p_act in self.acts:
            if p_act:
                self.d2api.unload_act(p_act)

        self.acts = (POINTER(Act) * 5)()
        self._seed = s

    @property
    def difficulty(self):
        return self._difficulty

    @difficulty.setter
    def difficulty(self, d):
        self._difficulty = EnumDifficulty(d)
