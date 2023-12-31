import numpy as np
import pyastar2d
from dataclasses import dataclass, field
from map_server.utils.data import EnumArea


@dataclass
class AreaData:
    map: np.array = field(repr=False)
    weights: np.array = field(repr=False)
    area: EnumArea
    size: tuple[int, int]
    origin: tuple[int, int]
    tomb_area: int
    exits: dict
    waypoint: tuple
    adjacent_levels: dict
    # npcs: dict
    # collision_map: list[list[str]]
    # objects: dict

    def __post_init__(self):
        self.area = EnumArea(self.area)

    def path_finding(self, src: tuple, dst: tuple):
        """
        find the path from source to destination.
        :param padding: add padding to each unwalkabale node in the map
        :param src: world position of the starting point (x, y)
        :param dst: world position of the target point (x, y)
        :return: numpy array of world coordinates to the target
        """
        src = int(src[0]) - self.origin[0], int(src[1]) - self.origin[1]
        dst = int(dst[0] - self.origin[0]), int(dst[1] - self.origin[1])
        path = pyastar2d.astar_path(self.weights, src, dst)
        path[:, 0] += self.origin[0]
        path[:, 1] += self.origin[1]
        return [{i: (int(a[0]), int(a[1]))} for i, a in enumerate(path)]
