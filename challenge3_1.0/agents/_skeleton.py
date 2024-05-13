from random import choice
from time import time
from typing import Tuple, List

from action import *
from board import GameBoard


class Agent:  # Do not change the name of this class!
    """
    An agent class (Skeleton)
    """

    def decide_new_village(self, board: GameBoard, time_limit: float = None) -> Tuple[int, int]:
        """
        This algorithm search for the best place of placing a new village.

        :param board: Game board to manipulate
        :param time_limit: Timestamp for the deadline of this search.
        :return: Tuple of coordinates
        """
        raise NotImplementedError('Please implement this method!')
