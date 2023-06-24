import os
import pathlib
import math
import numpy as np
import subprocess
import rpyc
import cv2
from PIL import Image, ImageFilter


def generate_image(area_map, area_name, size, origin, path):
    grayscale_map = np.where(area_map == -1, 255, area_map)
    grayscale_map = np.where(grayscale_map % 2 == 1, 255, grayscale_map).astype(np.uint8)
    # invert the pixels
    texture_map = cv2.bitwise_not(grayscale_map)
    # convert gray pixels to white
    ret, th1 = cv2.threshold(texture_map, 120, 255, cv2.THRESH_BINARY)
    # detect contours
    cnts, hierarchy = cv2.findContours(th1, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    # draw only the contours on blank image
    cnts_img = np.ones((size[1], size[0]))
    # draw only large area of unwalkable pixels
    for cnt in cnts:
        area_size = cv2.contourArea(cnt)
        if area_size > 100:
            cv2.drawContours(cnts_img, cnt, -1, (0, 255, 0), 1)

    cnts_img = cnts_img.astype(np.uint8) * 255

    def filter_path_by_distance(nodes: list, distance: int):
        p = [nodes[-1]]
        pos = nodes[-1]
        for i in range(len(nodes) - 2, -1, -1):
            next_pos = nodes[i]
            if math.dist(pos, next_pos) >= distance:
                p.append(nodes[i])
                pos = next_pos

        return p

    # mark the path
    path = [next(iter(p.values())) for p in path]
    path = filter_path_by_distance(path, distance=15)

    for node in path:
        x, y = node
        cv2.circle(cnts_img, [x - origin[0], y - origin[1]], 1, 127, 2)

    backtorgb = cv2.cvtColor(cnts_img, cv2.COLOR_GRAY2RGB)
    backtorgb[np.all(backtorgb == (127, 127, 127), axis=-1)] = (255, 127, 70)

    org = path[-1][0] - origin[0] - 20, path[-1][1] - origin[1] - 10
    image = cv2.putText(backtorgb, 'Player', org, cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, (255, 20, 60), 1, cv2.LINE_AA)
    org = path[0][0] - origin[0] + 30, path[0][1] - origin[1] + 10
    image = cv2.putText(image, 'ColdPlains', org, cv2.FONT_HERSHEY_SIMPLEX,
                        0.35, (60, 80, 255), 1, cv2.LINE_AA)

    height, width = backtorgb.shape[:2]
    offset = int(width / 2)

    def cartToIso(point):
        isoX = point[0] - point[1] + offset
        isoY = (point[0] + point[1]) / 2
        return np.array([int(isoX), int(isoY)]) - 1

    iso_img = np.ones((height + offset, width * 2, 3), dtype=np.uint8) * 255
    for i in range(width):
        for j in range(height):
            x, y = cartToIso([i, j])
            iso_img[y, x] = backtorgb[j, i]

    # # # crop the image
    backtogray = cv2.cvtColor(iso_img, cv2.COLOR_BGR2GRAY)
    black_pixels_rows = np.array(np.where(backtogray == 0))
    first_black_pixel_r = black_pixels_rows[:, 0][0]
    last_black_pixel_r = black_pixels_rows[:, -1][0]
    black_pixels_cols = np.array(np.where(backtogray.transpose() == 0))
    first_black_pixel_c = black_pixels_cols[:, 0][0]
    last_black_pixel_c = black_pixels_cols[:, -1][0]
    crop_img = iso_img[first_black_pixel_r:last_black_pixel_r + 1, first_black_pixel_c:last_black_pixel_c + 1]

    iso_image = cv2.resize(crop_img, (crop_img.shape[1] * 3, crop_img.shape[0] * 3), interpolation=cv2.INTER_AREA)
    img = Image.fromarray(iso_image)
    img = img.filter(ImageFilter.SMOOTH_MORE)
    img.show()
    img.save(f"{area_name}.png")


def main():
    root = pathlib.Path(__file__).parent.parent
    python_exe = os.path.join(root, "venv", "Scripts", "python.exe")
    server_proc = subprocess.Popen([python_exe, "-m", "map_server"])
    try:
        if server_proc.poll() is not None:
            raise Exception("Failed to start RPC server")

        example_seed = 0x3098ddf4
        # 0 normal = 0, nightmare = 1, hell = 2
        difficulty = 2
        # blood moor area
        blood_moor = 2
        # if we want outdoor exits we have to send valid position of the player.

        # WorldStoneKeep valid dummy position
        # dummy_player_position = (12790, 10590)

        # BloodMoor dummy valid position
        dummy_player_position = (5720, 5640)

        rpyc_conn = rpyc.connect("localhost", port=18861)
        rpyc_conn.root.set_map_seed(example_seed)
        rpyc_conn.root.set_difficulty(difficulty)

        map_data = rpyc_conn.root.obtain_map_data(blood_moor, dummy_player_position)
        print(f"Area: {map_data.area}, Origin: {map_data.origin}, Size: {map_data.size}")
        if map_data.exits:
            print(f"Maze exits: {map_data.exits}")
        if map_data.adjacent_levels:
            print("Adjacent levels:")
        for k, v in map_data.adjacent_levels.items():
            print("\t", k, v)

        # we can also use A* for path finding
        src = dummy_player_position
        # ColdPlains path
        dst = map_data.adjacent_levels["ColdPlains"]["outdoor"][0]
        # WorldStoneKeepLevel2 path
        # dst = map_data.exits["TheWorldStoneKeepLevel2"]
        cold_plains_path = map_data.path_finding(src=src, dst=dst)

        area_map = rpyc.classic.obtain(map_data.map)
        generate_image(area_map, map_data.area.name, map_data.size, map_data.origin, cold_plains_path)

    finally:
        server_proc.terminate()


if __name__ == '__main__':
    main()
