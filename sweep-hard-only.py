
import game

from typing import Dict, Tuple, Collection
from PIL import ImageGrab, Image
import numpy as np

import time
from pynput.mouse import Button, Controller
import async_key_listener

def find_game(im, square_colors, thresh):
    """finds the dimensions of the game rect on the screen"""
    match = find_color_match(im, square_colors, thresh)
    if match is None:
        return None
    return walk_rect(im, match, square_colors, thresh)


def find_color_match(im, colors, thresh) -> np.ndarray:
    """finds the first pixel in an image that matches one of the colors (at sample a reduced sample rate)"""
    w, h = im.size
    step = 20

    for x in range(0, w, step):
        for y in range(0, h, step):
            pixel = im.getpixel((x, y))

            for color in colors:
                if get_color_diff(color, pixel) < thresh:
                    return np.array([x, y])
    return None


def walk_rect(im, start: np.ndarray, colors, thresh) -> Tuple[np.ndarray, np.ndarray]:
    """finds the rect of the game by walking in all directions until it finds a pixel that doesn't match one of the colors"""
    rect_min = start
    rect_min = walk(im, rect_min, np.array([-1, 0]), colors, thresh)
    rect_min = walk(im, rect_min, np.array([0, -1]), colors, thresh)

    rect_max = rect_min
    rect_max = walk(im, rect_max, np.array([1, 0]), colors, thresh)
    rect_max = walk(im, rect_max, np.array([0, 1]), colors, thresh)
    rect_max += np.array([1, 1])
    return rect_min, rect_max - rect_min


def walk(im, start: np.ndarray, direction: np.ndarray, colors, thresh) -> np.ndarray:
    """iterates an image in a direction until it finds a pixel that doesn't match one of the colors"""
    while True:
        step = start + direction
        match_found = False

        for color in colors:
            pixel = im.getpixel(tuple(step))
            if get_color_diff(color, pixel) < thresh:
                match_found = True
                start = step
                break
        if not match_found:
            break
    return start


def find_square_count(im, game_rect: Tuple[np.ndarray, np.ndarray], colors, thresh) -> np.ndarray:
    """finds the number of squares in an image of the game"""
    step_size = 1
    start = game_rect[0]
    size = game_rect[1]

    w = count_color_switches(im, start, np.array([step_size, 0]), size[0] // step_size, colors, thresh)
    h = count_color_switches(im, start, np.array([0, step_size]), size[1] // step_size, colors, thresh)
    return np.array([w, h])


def count_color_switches(im, start: np.ndarray, direction: np.ndarray, steps: int, colors, thresh):
    """counts the number of times the color switches between a given set of colors in an image
    iterating in a given direction from a given start point"""
    color_switches = 0
    last_color_match = -1

    for  i in range(steps):
        step = start + i * direction
        pixel = im.getpixel(tuple(step))
        best_color_match, _ = get_closest_color(pixel, colors, thresh)

        #don't count pixels as new squares if the don't have square colors
        if best_color_match == -1:
            continue

        if best_color_match != last_color_match:
            color_switches += 1
            last_color_match = best_color_match

    return color_switches


def get_closest_color(pixel, colors, thresh):
    """finds the closest color to a given pixel from a given set of colors.
    returns the index of the color and the squared color difference.
    if the color difference is greater than the threshold, the index is -1"""
    best_color_match = -1
    min_color_diff = thresh

    for i, color in enumerate(colors):
        color_diff = get_color_diff(color, pixel)
        if color_diff < min_color_diff:
            best_color_match = i
            min_color_diff = color_diff
    return best_color_match, min_color_diff


def get_color_diff(color1, color2):
    """returns the squared (positive) color difference between two colors"""
    dr = color1[0] - color2[0]
    dg = color1[1] - color2[1]
    db = color1[2] - color2[2]
    return dr * dr + dg * dg + db * db


def read_square_values(
        im,
        game_rect: Tuple[np.ndarray, np.ndarray],
        sqare_count: np.ndarray,
        squares_to_read: Collection[Tuple[int, int]],
        num_images: Dict[int, Tuple[np.ndarray, np.ndarray]]):
    """reads all numbers from squares in an image at given positions and returns them in a dict"""
    square_size = game_rect[1] / sqare_count
    square_values = {}

    padding = np.array([2, 2])
    print("reading numbers...")

    # draw = ImageDraw.Draw(im)
    for square in squares_to_read:
        square_min = game_rect[0] + square * square_size
        square_max = square_min + square_size

        square_min += padding
        square_max -= padding

        frame = [*square_min, *square_max]
        square_im = im.crop(frame)

        value = read_square_num(square_im, num_images)
        square_values[tuple(square)] = value
    # im.show()
    return square_values


def read_square_num(im, num_img_arrays: Dict[int, Tuple[np.ndarray, np.ndarray]]) -> int:
    """reads the number from a square image by comparing it to a dict of number images"""
    im_array = np.array(im)
    best_match = 9999999
    best_num = -1

    for num, num_img_arrays in num_img_arrays.items():
        num_im_array1, num_im_array2 = num_img_arrays
        mse1 = mse(im_array, num_im_array1)
        mse2 = mse(im_array, num_im_array2)
        mse_min = min(mse1, mse2)

        if mse_min < best_match:
            best_match = mse_min
            best_num = num

    return best_num


def mse(im_array_a, im_array_b):
    """returns the mean squared error between two images"""
    # err = np.sum((im_array_a.astype("float") - im_array_b.astype("float")) ** 2)
    err = np.sum((im_array_a - im_array_b) ** 2)
    err /= float(im_array_a.shape[0] * im_array_b.shape[1])
    return err


def load_num_images() -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
    num_img_arrays = {}
    all_nums_img = Image.open("res/numbers.png")
    square_len = 21

    for i in range(11):
        img1 = all_nums_img.crop((i * square_len, 0, (i + 1) * square_len, square_len))
        img2 = all_nums_img.crop((i * square_len, square_len, (i + 1) * square_len, 2 * square_len))
        num_img_arrays[i - 1] = (np.array(img1)[:, :, :3], np.array(img2)[:, :, :3])

    return num_img_arrays


def mark_mine(game_rect, square_count, square: Tuple[int, int]):
    """marks a square as a mine by right clicking it"""
    move_to_square(game_rect, square_count, square)
    Controller().click(Button.right)


def reveal_neighbors(game_rect, square_count, square: Tuple[int, int]):
    """reveals all left neighbors of a fully flagged square by left-right clicking it"""
    move_to_square(game_rect, square_count, square)

    mouse = Controller()
    mouse.press(Button.left)
    time.sleep(0.05)
    mouse.press(Button.right)
    time.sleep(0.05)
    mouse.release(Button.right)
    mouse.release(Button.left)
    time.sleep(0.05)


def move_to_square(game_rect, square_count, square: Tuple[int, int], duration=0.1):
    """moves the mouse to the center position of a square"""
    pixel_pos = game_rect[0] + (np.array(square) + np.array([0.5, 0.5])) / square_count * game_rect[1]
    Controller().position = tuple(pixel_pos)
    time.sleep(duration)


def locate_screen_game(grass_colors, dirt_colors, border_colors, thresh, num_images):
    """finds the game on the screen and returns the game rect and a game object"""
    square_colors = grass_colors + dirt_colors

    while True:
        print("searching the screen for minesweeper...")
        im = ImageGrab.grab().convert("RGB")
        game_rect = find_game(im, square_colors + border_colors, thresh)

        if game_rect is not None:
            break
        time.sleep(3)

    print("\nfoudn game size is ", game_rect[0], game_rect[1])
    square_count = find_square_count(im, game_rect, square_colors, thresh)
    print("game dimensions are", square_count)

    # draw = ImageDraw.Draw(im)
    # draw.rectangle([tuple(game_rect[0]), tuple(game_rect[0] + game_rect[1])], outline="red", width=1)
    # im.show()

    my_game = game.Game(square_count)
    print("square size is", game_rect[1] / square_count)

    new_values = read_square_values(
        im,
        game_rect,
        my_game.size,
        my_game.covered_squares,
        num_images)
    my_game.update(new_values)
    return game_rect, my_game


def update_game(my_game, game_rect, num_images):
    """updates the game object with newly read square values of the game on the screen"""
    im = ImageGrab.grab().convert("RGB")
    new_values = read_square_values(
        im,
        game_rect,
        my_game.size,
        my_game.covered_squares,
        num_images)
    my_game.update(new_values)


def main():
    # colors of convered squares
    grass_colors = [(162, 209, 73), (170, 215, 81)]
    # colors of uncoveres squares with numbers
    dirt_colors = [(215, 184, 153), (229, 194, 159)]
    # border color from grass to dirt
    border_colors = [(135, 175, 58)]
    # threshold for max summed squared color diffrences
    thresh = 100

    num_images = load_num_images()
    game_rect, my_game = locate_screen_game(grass_colors, dirt_colors, border_colors, thresh, num_images)
    print("\n", my_game, sep="")

    size = my_game.size
    # click rnd square if game is new
    if len(my_game.covered_squares) == size[0] * size[1]:
        reveal_neighbors(game_rect, my_game.size, (size[0] // 2, size[1] // 2))
        time.sleep(1)
        update_game(my_game, game_rect, num_images)

    async_key_listener.listen_for_ctrl_c()

    while True:
        no_mines_left = False
        no_squares_left = False

        unflagged_mines = my_game.get_new_mine_squares()

        if len(unflagged_mines) == 0:
            no_mines_left = True

        for square in unflagged_mines:
            mark_mine(game_rect, my_game.size, square)
            my_game.add_flagged_mine(square)

        if (len(my_game.clickable_squares) == 0):
            no_squares_left = True

        if no_mines_left and no_squares_left:
            if len(my_game.covered_squares) == 0:
                print("I hope this was it uwu")
            else:
                print("nothing certain to click")
            move_to_square(game_rect, my_game.size, (0, 0))
            break

        for click_square in my_game.clickable_squares:
            reveal_neighbors(game_rect, my_game.size, click_square)

        time.sleep(1)
        update_game(my_game, game_rect, num_images)
        print("\n", my_game, sep="")


if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"--- {time.time() - start_time} seconds ---")
