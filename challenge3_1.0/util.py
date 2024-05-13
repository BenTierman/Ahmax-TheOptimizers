from collections import defaultdict
from typing import Tuple, Iterable, Dict

from pycatan import Player
from pycatan.board import Coords, Intersection, BuildingType


def coordinate_to_tuple(coord: Coords) -> Tuple[int, int]:
    """
    Helper function to store coordinates as a basic python object

    :param coord: Coordinate to store
    :return: Tuple of (Q, R) of the given coordinate
    """
    return coord.q, coord.r


def tuple_to_coordinate(tpl: Tuple[int, int]) -> Coords:
    """
    Helper function to restore coordinates from a basic python object

    :param tpl: Coordinate to restore
    :return: Coords object of PyCatan.
    """
    return Coords(tpl[0], tpl[1])


def tuple_to_path_coordinate(tpl: Tuple[Tuple[int, int]]) -> frozenset:
    """
    Helper function to restore path coordinates from a basic python object

    :param tpl: Coordinate to restore
    :return: FrozenSet of Coords object of PyCatan.
    """
    return frozenset({tuple_to_coordinate(tpl[0]), tuple_to_coordinate(tpl[1])})


def count_building(intersections: Iterable[Intersection], player: Player) -> Dict[BuildingType, int]:
    """
    Count the number of buildings that the player have.

    :param intersections: List of all intersections in the board.
    :param player: Player to investigate
    :return: Dictionary of building type to number mapping
    """
    counter: Dict[BuildingType, int] = defaultdict(int)
    for i in intersections:
        if i.building is not None and i.building.owner == player:
            counter[i.building.building_type] += 1
    return counter
