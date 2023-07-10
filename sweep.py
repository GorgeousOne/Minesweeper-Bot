
import game
import config

from typing import Dict, Tuple, Collection
from PIL import ImageGrab, ImageDraw
import numpy as np
import pytesseract as tess
tess.pytesseract.tesseract_cmd = config.TESSERACT_EXE_PATH

import time
from pynput.mouse import Button, Controller


def find_game(im, square_colors, thresh):
    match = find_color_match(im, square_colors, thresh)
    if match is None:
        return None
    return walk_rect(im, match, square_colors, thresh)


def find_color_match(im, colors, thresh) -> np.ndarray:
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
    rect_min = start
    rect_min = walk(im, rect_min, np.array([-1, 0]), colors, thresh)
    rect_min = walk(im, rect_min, np.array([0, -1]), colors, thresh)
    
    rect_max = rect_min
    rect_max = walk(im, rect_max, np.array([1, 0]), colors, thresh)
    rect_max = walk(im, rect_max, np.array([0, 1]), colors, thresh)
    rect_max += np.array([1, 1])
    return rect_min, rect_max - rect_min


def walk(im, start: np.ndarray, direction: np.ndarray, colors, thresh) -> np.ndarray:
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
    step_size = 1
    start = game_rect[0]
    size = game_rect[1]
    
    w = count_color_switches(im, start, np.array([step_size, 0]), size[0] // step_size, colors, thresh)
    h = count_color_switches(im, start, np.array([0, step_size]), size[1] // step_size, colors, thresh)
    return np.array([w, h])


def count_color_switches(im, start: np.ndarray, direction: np.ndarray, steps: int, colors, thresh):
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
    best_color_match = -1
    min_color_diff = thresh
    
    for i, color in enumerate(colors):
        color_diff = get_color_diff(color, pixel)
        if color_diff < min_color_diff:
            best_color_match = i
            min_color_diff = color_diff    
    return best_color_match, min_color_diff


def get_color_diff(color1, color2):
    dr = color1[0] - color2[0]
    dg = color1[1] - color2[1]
    db = color1[2] - color2[2]
    return dr * dr + dg * dg + db * db


def read_square_values(
        im, 
        game_rect: Tuple[np.ndarray, np.ndarray], 
        sqare_count: np.ndarray, 
        squares_to_read: Collection[Tuple[int, int]], 
        grass_colors, dirt_colors, thresh):
    square_size = game_rect[1] / sqare_count
    square_values = {}

    padding = np.array([4, 4])
    print("reading numbers... (sry this is super slow)")
    
    # draw = ImageDraw.Draw(im)
    for square in squares_to_read:
        square_min = game_rect[0] + square * square_size
        square_max = square_min + square_size
            
        square_min += padding
        square_max -= padding
        
        frame = [*square_min, *square_max]
        square_im = im.crop(frame)
        is_covered = is_square_convered(square_im, grass_colors, thresh)

        # draw.rectangle([tuple(square_min), tuple(square_max)], outline="red", width=1)
        
        if is_covered:
            square_values[tuple(square)] = -1
        else:
            square_values[tuple(square)] = read_square_num(square_im)                
    # im.show()
    return square_values


def is_square_convered(square_im, grass_colors, thresh) -> bool:
    avg_color = get_avg_color(square_im)
    color_match, _ = get_closest_color(avg_color, grass_colors, thresh)
    return color_match != -1


def get_avg_color(im) -> Tuple[int, int, int]:
    r, g, b = 0, 0, 0
    for pixel in im.getdata():
        red, green, blue = pixel
        r += red
        g += green
        b += blue

    w, h = im.size
    total_pixels = w * h
    avg_r = r // total_pixels
    avg_g = g // total_pixels
    avg_b = b // total_pixels
    return avg_r, avg_g, avg_b


def read_square_num(im) -> int:
    # psm 10: single character? doesnt work
    # oem 3: sets the OCR engine mode to use default OCR engine?
    # c tessedit_char_whitelist=0123456789: restricts to 0 - 9?
    text = tess.image_to_string(im, config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')
    text = text.strip()
    if text != "":
        return int(text)
    return 0


def mark_mine(game_rect, square_count, square: Tuple[int, int]):
    move_to_square(game_rect, square_count, square)
    Controller().click(Button.right)


def reveal_neighbors(game_rect, square_count, square: Tuple[int, int]):
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
    pixel_pos = game_rect[0] + (np.array(square) + np.array([0.5, 0.5])) / square_count * game_rect[1]
    Controller().position = tuple(pixel_pos)
    time.sleep(duration)

def locate_screen_game(grass_colors, dirt_colors, border_colors, thresh):
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

    new_values = read_square_values(im, game_rect, my_game.size, my_game.covered_squares, grass_colors, dirt_colors, thresh)
    my_game.update(new_values)
    return game_rect, my_game


def update_game(my_game, game_rect, grass_colors, dirt_colors, thresh):
    im = ImageGrab.grab().convert("RGB")
    new_values = read_square_values(im, game_rect, my_game.size, my_game.covered_squares, grass_colors, dirt_colors, thresh)
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
    
    game_rect, my_game = locate_screen_game(grass_colors, dirt_colors, border_colors, thresh)
    print("\n", my_game, sep="")

    size = my_game.size
    # click rnd square if game is new
    if len(my_game.covered_squares) == size[0] * size[1]:
        reveal_neighbors(game_rect, my_game.size, (size[0] // 2, size[1] // 2))
        time.sleep(1)
        update_game(my_game, game_rect, grass_colors, dirt_colors, thresh)
        
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
        update_game(my_game, game_rect, grass_colors, dirt_colors, thresh)
        print("\n", my_game, sep="")


if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"--- {time.time() - start_time} seconds ---")
