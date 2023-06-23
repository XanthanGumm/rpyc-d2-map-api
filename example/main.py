import sys
from PIL import Image
import numpy as np
import rpyc
import os
import pathlib
import subprocess
import pylab as plt
import cv2
from scipy.ndimage import rotate
np.set_printoptions(threshold=sys.maxsize)


# TODO: fix the map server to work with all exits
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
        blood_moor = 46
        # if we want outdoor exits we have to send valid position of the player.
        dummy_player_position = None #(5420, 5640)

        rpyc_conn = rpyc.connect("localhost", port=18861)
        rpyc_conn.root.set_map_seed(example_seed)
        rpyc_conn.root.set_difficulty(difficulty)

        map_data = rpyc_conn.root.obtain_map_data(blood_moor, dummy_player_position)
        print(f"Area: {map_data.area}, Origin: {map_data.origin}, Size: {map_data.size}")
        print(f"Maze exits: {map_data.exits}")
        print("Adjacent levels:")
        for k, v in map_data.adjacent_levels.items():
            print("\t", k, v)

        # we can also use A* for path finding
        # src = dummy_player_position
        # dst = map_data.adjacent_levels["ColdPlains"]["outdoor"][0]
        # cold_plains_path = map_data.path_finding(src=src, dst=dst)

        area_map = rpyc.classic.obtain(map_data.map)
        grayscale_map = np.where(area_map == -1, 255, area_map)
        grayscale_map = np.where(grayscale_map % 2 == 1, 255, grayscale_map)
        # save as png
        cv2.imwrite(f"{map_data.area.name}.png", grayscale_map)
        # load as png
        texture_map = cv2.imread(f"{map_data.area.name}.png", cv2.IMREAD_GRAYSCALE)
        # invert the pixels
        texture_map = cv2.bitwise_not(texture_map)
        # convert gray pixels to white
        ret, th1 = cv2.threshold(texture_map, 120, 255, cv2.THRESH_BINARY)
        # detect contours
        cnts, hierarchy = cv2.findContours(th1, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        # draw only the contours on blank image
        cnts_img = np.ones((map_data.size[1], map_data.size[0]))
        # draw only large area of unwalkable pixels
        for cnt in cnts:
            area_size = cv2.contourArea(cnt)
            if area_size > 100:
                cv2.drawContours(cnts_img, cnt, -1, (0, 255, 0), 1)

        cnts_img = cnts_img * 255

        # crop the image
        black_pixels_rows = np.array(np.where(cnts_img == 0))
        first_black_pixel_r = black_pixels_rows[:, 0][0]
        last_black_pixel_r = black_pixels_rows[:, -1][0]
        black_pixels_cols = np.array(np.where(cnts_img.transpose() == 0))
        first_black_pixel_c = black_pixels_cols[:, 0][0]
        last_black_pixel_c = black_pixels_cols[:, -1][0]
        crop_img = cnts_img[first_black_pixel_r:last_black_pixel_r + 1, first_black_pixel_c:last_black_pixel_c + 1]

        scale_percent = 50

        # calculate the 50 percent of original dimensions
        width = int(crop_img.shape[1] * 3)
        height = int((crop_img.shape[0] * 3) * scale_percent / 100)
        # dsize
        dsize = (width, height)

        # resize image
        output = cv2.resize(crop_img, dsize, interpolation=cv2.INTER_LINEAR)
        output = rotate(output, angle=-45, cval=255)

        # save the new image
        cv2.imwrite(f"{map_data.area.name}.png", cnts_img)
        cv2.imwrite(f"{map_data.area.name}_cropped.png", output)

        # plot images
        cv2.imshow(f"{map_data.area.name}", cnts_img)
        cv2.imshow(f"{map_data.area.name}_cropped", crop_img)
        cv2.imshow(f"{map_data.area.name}_resized", output)

        cv2.waitKey(0)
        cv2.destroyAllWindows()

        plt.imshow(output)
        plt.show()

    finally:
        server_proc.terminate()


if __name__ == '__main__':
    main()
