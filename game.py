import numpy as np
from typing import Dict, Tuple, Set

class Game:
    def __init__(self, size: np.ndarray):
        self.size = size
        self.state = -np.ones(tuple(size), dtype=np.int32)
        
        rows, cols = self.size
        square_coords = np.indices((rows, cols)).reshape(2, -1).T
        
        # squares that are covered (and not a mine maybe?)
        self.covered_squares = set([tuple(coord) for coord in square_coords])
        # squares that are revealed but still have covered neighbors (not mines) left
        self.uncertain_squares = set()
        # squares which meet their mine numbers so covered neighbors can be revealed
        self.clickable_squares = set()
        # squares with mines under them
        self.flagged_mines = set()
        
        # self.update_state(initial_values)

    def __str__(self):
        text = ""
        for y in range(self.size[1]):
            for x in range(self.size[0]):
                val = self.square_val(np.array([x, y]))
                text += "░" if val == -1 else "●" if val == 9 else str(val)
                text += " "
            text += "\n"
        return text
        
    def square_val(self, square) -> int:
        """returns the number of mines around a square
        -1: unknown
        0-8: actual counts
        9: it's a mine itself"""
        return self.state[tuple(square)]
    
    def update(self, new_values: Dict[Tuple[int, int], int]):
        self._update_state(new_values)
        self._update_covered_squares(new_values)
        self._update_uncertain_squares()
        self._update_clickable_squares()
    
    def get_new_mine_squares(self):
        unflagged_mines = set()
        for square in self.uncertain_squares:
            neighbors = self.get_covered_neighbors(square)
            mine_count = self.get_neighbor_mine_count(square)
            
            if len(neighbors) + mine_count == self.square_val(square):
                unflagged_mines.update([tuple(s) for s in neighbors])
        return unflagged_mines
    
    def add_flagged_mine(self, square):
        self.covered_squares.remove(square)
        self.flagged_mines.add(square)
        self.state[tuple(square)] = 9
        self._update_uncertain_squares()
        self._update_clickable_squares()
        
    def _update_state(self, new_values: Dict[tuple, int]):
        for square, value in new_values.items():
            self.state[square] = value

    def _update_covered_squares(self, new_values: Dict[tuple, int]):
        """unlists covered squares if they have been revealed.
        flags all revealed squares as uncertain (pls update uncertain next) (pls don't list mines in new_values)"""
        uncovered_squares = set([s for s, v in new_values.items() if v != -1])
        self.covered_squares.difference_update(uncovered_squares)
        # add all new squares
        self.uncertain_squares.update(uncovered_squares)

    def _update_clickable_squares(self):
        """remove clickable squares if by other actions nothing is left to click"""
        self.clickable_squares = set([s for s in self.clickable_squares if len(self.get_covered_neighbors(s)) > 0])

    def _update_uncertain_squares(self):
        """remove squares that have all their mines flagged. add them to clickable, if neighbors are still covered"""
        # squares that meet their mine count
        finished_squares = set([s for s in self.uncertain_squares if self.get_neighbor_mine_count(s) == self.square_val(s)])
        self.uncertain_squares.difference_update(finished_squares)
        self.clickable_squares.update([s for s in finished_squares if len(self.get_covered_neighbors(s)) > 0])
    
    def get_neighbor_mine_count(self, square) -> int:
        return len([s for s in self.get_neighbor_squares(square) if self.square_val(s) == 9])
    
    def get_covered_neighbors(self, square) -> Set[Tuple[int, int]]:
        return set([s for s in self.get_neighbor_squares(square) if self.square_val(s) == -1])
        
    def get_neighbor_squares(self, square) -> Set[Tuple[int, int]]:
        neighbors = set()
        row, col = square
        
        min_x = max(0, row - 1)
        min_y = max(0, col - 1)
        max_x = min(self.size[0], row + 2)
        max_y = min(self.size[1], col + 2)
    
        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                if x != row or y != col:
                    neighbors.add((x, y))
        return neighbors