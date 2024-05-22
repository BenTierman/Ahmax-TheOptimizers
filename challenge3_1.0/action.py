# Abstract Class annotations
import abc
# Logging method for board execution
import logging
# Library for OS environment
import sys
# Type definition of Python
from typing import Tuple

# Import some class definitions that implements the Settlers of Catan game.
from pycatan import Resource
from pycatan.board import BuildingType

# Import some utilities
from util import tuple_to_path_coordinate, tuple_to_coordinate


#: True if the program run with 'DEBUG' environment variable.
IS_DEBUG = '--debug' in sys.argv


class Action(abc.ABC):
    """
    Abstract class for action
    """

    #: [PRIVATE] Logger instance for Action's function calls
    _logger = logging.getLogger('Action')

    @abc.abstractmethod
    def __call__(self, board):
        """
        Executing/Simulating an action on a game board

        :param board: Game board to manipulate
        """
        raise NotImplementedError()


class PASS(Action):
    """
    Pass turn to the next players, and wait for the next turn
    """

    def __repr__(self):  # String representation for this
        return 'PASS'

    def __call__(self, board):
        if IS_DEBUG:  # Logging for debugging
            self._logger.debug('Calling PASS action')

        if board._initial_phase:
            # Move to the next setup player
            board._current_player = board._setup_order[0]
            board._setup_order = board._setup_order[1:]
        else:
            # roll the dice (deterministically)
            next_dice = board.get_next_dice_roll()

            # If the dice number is 7, do nothing.
            if next_dice == 7:
                if IS_DEBUG:  # Logging for debugging
                    self._logger.debug(f'Dice: 7; Do nothing.')
                pass
            else:
                # Otherwise, give resources to the players
                if IS_DEBUG:  # Logging for debugging
                    self._logger.debug(f'Dice: {next_dice}; Players get resources.')
                board._add_yield()


class ROAD(Action):
    """
    Construct a road
    """

    def __init__(self, player_id: int, edge: Tuple[Tuple[int, int]]):
        """
        Action for constructing a road at edge

        :param player_id: ID of the current player (You can get this from board.get_player_index())
        :param edge: Tuple of coordinates, i.e., ((Q1, R1), (Q2, R2))
        """
        self.player_id = player_id
        self.edge = tuple_to_path_coordinate(edge)

    def __repr__(self):  # String representation for this
        return f'ROAD{tuple(self.edge)} of player {self.player_id}'

    def __call__(self, board):
        if IS_DEBUG:  # Logging for debugging
            self._logger.debug(f'Calling ROAD construction on edge {self.edge}.')

        # Check whether the player can build a road.
        assert self.player_id == board._current_player
        player = board._game.players[self.player_id]

        if not board._initial_phase:  # If the board is not in the initial settlement phase
            if not player.has_resources(BuildingType.ROAD.get_required_resources()):
                # If not, do nothing.
                if IS_DEBUG:  # Logging for debugging
                    self._logger.debug('The player has not enough resources to construct a ROAD')
                return

        # Build a road on the specified place
        board._game.build_road(player=player,
                               path_coords=self.edge,
                               ensure_connected=not board._initial_phase,
                               cost_resources=not board._initial_phase)
        if IS_DEBUG:  # Logging for debugging
            self._logger.debug('ROAD construction is successful.')


class VILLAGE(Action):
    """
    Construct a settlement(village)
    """

    def __init__(self, player_id: int, node: Tuple[int, int]):
        """
        Action for constructing a village at a node

        :param player_id: ID of the current player (You can get this from board.get_player_index())
        :param node: Position of that node, i.e., (Q, R)
        """
        self.player_id = player_id
        self.node = tuple_to_coordinate(node)

    def __repr__(self):  # String representation for this
        return f'VILLAGE{self.node} of player {self.player_id}'

    def __call__(self, board):
        if IS_DEBUG:  # Logging for debugging
            self._logger.debug(f'Calling VILLAGE construction on node {self.node}.')

        # Check whether the player can build a settlement.
        assert self.player_id == board._current_player
        player = board._game.players[self.player_id]
        if not board._initial_phase:  # If the board is not in the initial settlement phase
            if not player.has_resources(BuildingType.SETTLEMENT.get_required_resources()):
                # If not, do nothing.
                if IS_DEBUG:  # Logging for debugging
                    self._logger.debug('The player has not enough resources to construct a VILLAGE')
                return

        # Build a settlement on the specified place
        board._game.build_settlement(player=player,
                                     coords=self.node,
                                     ensure_connected=not board._initial_phase,
                                     cost_resources=not board._initial_phase)
        if IS_DEBUG:  # Logging for debugging
            self._logger.debug('VILLAGE construction is successful.')


class UPGRADE(Action):
    """
    Construct a city
    """

    def __init__(self, player_id: int, node: Tuple[int, int]):
        """
        Action for constructing a city at a node

        :param player_id: ID of the current player (You can get this from board.get_player_index())
        :param node: Position of that node, i.e., (Q, R)
        """
        self.player_id = player_id
        self.node = tuple_to_coordinate(node)

    def __repr__(self):  # String representation for this
        return f'UPGRADE{self.node} of player {self.player_id}'

    def __call__(self, board):
        if IS_DEBUG:  # Logging for debugging
            self._logger.debug(f'Calling city UPGRADE on node {self.node}.')

        # Check whether the player can build a city.
        assert self.player_id == board._current_player
        player = board._game.players[self.player_id]
        if not player.has_resources(BuildingType.CITY.get_required_resources()):
            # If not, do nothing.
            if IS_DEBUG:  # Logging for debugging
                self._logger.debug('The player has not enough resources to construct a CITY')
            return

        # Build a city on the specified place
        board._game.upgrade_settlement_to_city(player=player,
                                               coords=self.node,
                                               cost_resources=True)
        if IS_DEBUG:  # Logging for debugging
            self._logger.debug('City UPGRADE is successful.')


class TRADE(Action):
    """
    Trade resources
    """

    def __init__(self, player_id: int, given: str, request: str):
        """
        Action for trading resources. The player will give resources with type 'given',
         and receive one resource with 'request' type

        :param player_id: ID of the current player (You can get this from board.get_player_index())
        :param given: Type of resources to sell
        :param request: Type of resource to buy
        """
        self.player_id = player_id
        self.given = Resource[given.upper()]
        self.request = Resource[request.upper()]

    def __repr__(self):  # String representation for this
        return f'TRADE({self.given}xN->{self.request}) of player {self.player_id}'

    def __call__(self, board):
        if IS_DEBUG:  # Logging for debugging
            self._logger.debug(f'Calling TRADE: giving {self.given} and requesting {self.request}.')

        # Get the trading rate for the resource
        assert self.player_id == board._current_player
        rate = board.get_trading_rate(self.given.name)
        if rate < 0:
            # If trading is impossible, do nothing.
            if IS_DEBUG:  # Logging for debugging
                self._logger.debug('Not enough resources to make a trade!')
            return

        # Trade resources
        board._game.players[self.player_id].add_resources({
            self.given: -rate,
            self.request: 1
        })
        if IS_DEBUG:  # Logging for debugging
            self._logger.debug('TRADE action is successfully executed.')


# Export actions only
__all__ = ['Action', 'PASS',
           'ROAD', 'VILLAGE', 'UPGRADE', 'TRADE']
