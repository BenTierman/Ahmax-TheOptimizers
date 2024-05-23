# Logging method for board execution
import logging
# Library for OS environment
import os
import random
import sys
# Object-level deep copy method
from copy import deepcopy
# Random number generators
from random import randint as random_integer
# Type specification for Python code
from typing import Tuple, List, Dict, Callable

# Import some class definitions that implements the Settlers of Catan game.
from pycatan import Game, Resource
from pycatan.board import BuildingType, BoardRenderer, RandomBoard, Hex, HexType, Harbor, \
    IntersectionBuilding, PathBuilding

# Process information class: for memory usage tracking
from psutil import Process as PUInfo, NoSuchProcess

# Import action specifications
from action import Action, VILLAGE, ROAD, PASS
# Import some utilities
from util import tuple_to_coordinate, count_building, coordinate_to_tuple, tuple_to_path_coordinate


#: True if the program run with 'DEBUG' environment variable.
IS_DEBUG = '--debug' in sys.argv
IS_RUN = 'fixed_evaluation' in sys.argv[0]

#: Probability of getting dice rolls
DICE_ROLL = {
    2: 1/36,
    3: 2/36,
    4: 3/36,
    5: 4/36,
    6: 5/36,
    7: 6/36,
    8: 5/36,
    9: 4/36,
    10: 3/36,
    11: 2/36,
    12: 1/36
}


# String List of available resources
RESOURCES = [
    Resource.ORE.name,
    Resource.WOOL.name,
    Resource.BRICK.name,
    Resource.GRAIN.name,
    Resource.LUMBER.name
]

# List of player colors
PLAYER_COLOR = ["#00c40d", "#ff00d9", "#0000FF", "#00FFFF"]


def _coordinate_to_identifier(c):
    """
    Return the unique identifier for a coordinate on the board.
    :param c: Coordinate to make an identifier
    :return: 2-character String identifier for Coordinate c
    """
    q, r = coordinate_to_tuple(c)
    q = chr(ord('L') + int(q))
    r = chr(ord('L') + int(r))
    return q + r


def _unique_game_state_identifier(game: Game) -> str:
    """
    Return the unique identifier for game states.
    If two states are having the same identifier, then the states can be treated as identical in this problem.

    :param game: Game to make a unique identifier
    :return: String of game identifier
    """

    hexes = ':'.join([
        str(h.token_number) + _coordinate_to_identifier(c) + str(h.hex_type.value)
        for c, h in sorted(game.board.hexes.items(), key=lambda t: t[1].token_number or -1)
    ])
    intersections = ':'.join([
        _coordinate_to_identifier(c) + str(game.players.index(i.building.owner)) + str(i.building.building_type.value)
        for c, i in game.board.intersections.items()
        if i.building is not None
    ])
    paths = ':'.join([
        '-'.join(sorted(_coordinate_to_identifier(c) for c in p)) + str(game.players.index(i.building.owner))
        for p, i in game.board.paths.items()
        if i.building is not None
    ])
    players = ':'.join([
        '.'.join(str(r.value) + str(c) for r, c in sorted(p.resources.items(), key=lambda t: t[0].name))
        for p in game.players
    ])
    harbors = ':'.join([
        '-'.join(sorted(_coordinate_to_identifier(c) for c in p)) +
        (str(i.resource.value) if i.resource is not None else 'X')
        for p, i in game.board.harbors.items()
    ])

    return f'{hexes}/{intersections}/{paths}/{players}/{harbors}'


def _read_state(game: Game, player: int, current_player: int) -> dict:
    """
    Helper function for reading the current state representation as a python dictionary from the PyCatan board.

    :param game: Game to build a state.
    :return: State representation of a game (in basic python objects)
    """

    return {
        'state_id': _unique_game_state_identifier(game),
        # Unique identifier for the game state. If this is the same, then the state will be equivalent.
        'player_id': player,  # The agent's Player ID
        'current_player': current_player,  # Currently playing Player's ID
        'board': {  # Information about the current board
            'hexes': {  # Information about each hexagon cell
                coordinate_to_tuple(c): {  # For each coordinate(placement)
                    'type': h.hex_type.name,  # Resource type of that hexagon
                    'dice': h.token_number  # Dice number for that hexagon
                }
                for c, h in game.board.hexes.items()
            },
            'intersections': {  # Information about node intersection among three hexagon cells
                coordinate_to_tuple(c): {  # For each coordinate (placement)
                    'type': i.building.building_type.name if i.building is not None else None,  # Type of building
                    'owner': game.players.index(i.building.owner) if i.building is not None else None
                    # Owner of building
                }
                for c, i in game.board.intersections.items()
            },
            'paths': {  # Information about edge intersection between two hexagon cells
                tuple(sorted(coordinate_to_tuple(c) for c in p)): {  # For each edge (placement)
                    'type': i.building is not None,  # Road constructed or not (boolean)
                    'owner': game.players.index(i.building.owner) if i.building is not None else None  # Owner of path
                }
                for p, i in game.board.paths.items()
            },
            'harbors': {  # Information about harbors
                tuple(sorted(coordinate_to_tuple(c) for c in p)): {  # For each coordinate of harbor,
                    'type': i.resource.name if i.resource is not None else None
                    # Resource type for that harbor(2:1 trade). None means generic harbor(3:1)
                }
                for p, i in game.board.harbors.items()
            },
        },
        'player': {
            p: {  # Information about the current player
                'resources': {  # Information about resource cards
                    res.name: cnt  # For each resource, the number of resource cards will be stored
                    for res, cnt in game.players[p].resources.items()
                },
                'harbors': [  # Information about the connected harbors, with the coordinate names
                    tuple(sorted(coordinate_to_tuple(c) for c in h.path_coords))
                    for h in game.players[p].connected_harbors
                ]
            }
            for p in range(4)
        },
        'robber': coordinate_to_tuple(game.board.robber)
    }


def _restore_state(game: Game, state: dict, turnoff_check: bool):
    """
    Helper function to restore board state to given state representation.

    :param game: Game to restore a state.
    :param state: State to be restored
    """
    # Check whether hexes are the same.
    if turnoff_check:
        game.board.hexes.clear()
        game.board.harbors.clear()

    for c, h in state['board']['hexes'].items():
        c = tuple_to_coordinate(c)
        if turnoff_check:
            game.board.hexes[c] = Hex(
                coords=c, hex_type=HexType[h['type'].upper()], token_number=h['dice']
            )
        else:
            assert game.board.hexes[c].hex_type.name == h['type'],\
                f'The hex information (hex type) is different! {game.board.hexes[c].hex_type.name} == {h["type"]}'
            assert game.board.hexes[c].token_number == h['dice'], 'The hex information (hex token) is different!'

    # Check whether harbors are the same.
    for (c1, c2), i in state['board']['harbors'].items():
        c = tuple_to_path_coordinate((c1, c2))

        if turnoff_check:
            game.board.harbors[c] = Harbor(
                path_coords=c,
                resource=None if i['type'] is None else Resource[i['type'].upper()]
            )
        else:
            res = game.board.harbors[c].resource
            assert (res is None and i['type'] is None) or (res.name == i['type']), 'Harbor information is different!'

    # Restore intersections
    for c, i in state['board']['intersections'].items():
        c = tuple_to_coordinate(c)
        building = None
        if i['type'] is not None:
            building = IntersectionBuilding(building_type=BuildingType[i['type']], owner=game.players[i['owner']],
                                            coords=c)

        game.board.intersections[c].building = building

    # Restore paths
    for (c1, c2), i in state['board']['paths'].items():
        c = tuple_to_path_coordinate((c1, c2))
        building = None
        if i['type']:
            building = PathBuilding(building_type=BuildingType.ROAD, owner=game.players[i['owner']], path_coords=c)

        game.board.paths[c].building = building

    for p in range(4):
        # Restore player's resource
        for res, cnt in state['player'][p]['resources'].items():
            res = Resource[res.upper()]
            game.players[p].resources[res] = cnt

        # Restore connected harbor information
        game.players[p].connected_harbors = set()
        for (c1, c2) in state['player'][p]['harbors']:
            c = tuple_to_path_coordinate((c1, c2))
            game.players[p].connected_harbors.add(game.board.harbors[c])

    # Move robber
    if 'robber' in state:
        game.board.robber = tuple_to_coordinate(state['robber'])
    else:
        game.board.robber = [
            h.coords for h in game.board.hexes.values() if h.hex_type == HexType.DESERT
        ][0]

    return state['player_id'], state['current_player']


class GameBoard:
    """
    The game board object.
    By interacting with Board, you can expect what will happen afterward.
    """
    #: [PRIVATE] The game instance running currently. Don't access this directly in your agent code!
    _game = None
    #: [PRIVATE] The game renderer
    _renderer = None
    #: [PRIVATE] The order of your turn. Don't access this directly in your agent code!
    _player_number = 0
    #: [PRIVATE] The current player's index.
    _current_player = 0
    #: [PRIVATE] The remaining order of setup turn.
    _setup_order = (0, 1, 2, 3, 3, 2, 1, 0)
    #: [PRIVATE] The initial state of the board. Don't access this directly in your agent code!
    _initial = None
    #: [PRIVATE] The current state of the board. Don't access this directly in your agent code!
    _current = None
    #: [PRIVATE] Logger instance for Board's function calls
    _logger = logging.getLogger('GameBoard')
    #: [PRIVATE] Memory usage tracker
    _process_info = None
    #: [PRIVATE] Maximum memory usage. Don't access this directly in your agent code!
    _max_memory = 0
    #: [PRIVATE] Boolean for indicating whether this is on an initial set-up procedure or not
    _initial_phase = True
    #: [PRIVATE] Random seed generator
    _rng = random.Random(2938)

    def _initialize(self):
        """
        Initialize the board for evaluation. ONLY for evaluation purposes.
        [WARN] Don't access this method in your agent code.
        """
        # Initialize process tracker
        self._process_info = PUInfo(os.getpid())

        if IS_DEBUG:  # Logging for debug
            self._logger.debug('Initializing a new game board...')
        # Initialize a new game board
        self._game = Game(RandomBoard())
        # Initialize board renderer for debugging purposes
        if IS_DEBUG:  # Logging for debug
            self._renderer = BoardRenderer(self._game.board, player_color_map={
                player: PLAYER_COLOR[pid]
                for pid, player in enumerate(self._game.players)
            })
            self._logger.debug('Rendered board: \n' + _unique_game_state_identifier(self._game))
            self._renderer.render_board()

        # Pick a setup turn randomly
        self._player_number = random_integer(0, 3)
        self._current_player = 0
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'You\'re player {self._player_number}')

        if IS_DEBUG:  # Logging for debug
            self._logger.debug('After constructing initial village: \n' + _unique_game_state_identifier(self._game))
            self._renderer.render_board()

        # Store initial state representation
        self._initial = _read_state(self._game, self._player_number, 0)
        self._current = deepcopy(self._initial)
        self.reset_setup_order()

        # Update memory usage
        self._update_memory_usage()

    def reset_setup_order(self, reset_to=None):
        """
        Initialize the setup turn order to 1-2-3-4-4-3-2-1.

        :returns: The tuple of player IDs, ordered by setup ordering
        """
        self._setup_order = (0, 1, 2, 3, 3, 2, 1, 0) if reset_to is None else reset_to
        return self._setup_order

    def get_remaining_setup_order(self):
        """
        :returns: The tuple of remaining player IDs, ordered by setup ordering
        """
        return self._setup_order

    def run_initial_setup(self, players_policy: Dict[int, Callable[[dict], Tuple[Action, Action]]]):
        """
        Run the initial setup procedure, in the order of 1-2-3-4-4-3-2-1.

        :param players_policy: Dictionary of setup function for each player.
        :return: The last state after initialization.
        """
        state = self._initial
        self.reset_setup_order()

        for player in range(4):
            if player not in players_policy:
                players_policy[player] = \
                    self._one_resource_init_policy(self._rng.choice([Resource.BRICK, Resource.LUMBER]))

        while self._setup_order:
            # Move turn to the current player
            state = self.simulate_action(state, PASS())
            policy = players_policy[self._current_player]

            act1, act2 = policy(self._current.copy())
            assert isinstance(act1, VILLAGE), f'The first action should be a VILLAGE action, but received {type(act1)} for {self._current_player}'
            assert isinstance(act2, ROAD), f'The second action should be a ROAD action, but received {type(act2)} for {self._current_player}'

            state = self.simulate_action(state, act1, act2)

        return state

    def _one_resource_init_policy(self, resource: Resource):
        """
        Greedy initialization strategy for a player (Take a coordinate where maximizes the number of given resources)
        """

        def policy(state: dict):
            def _res_counter(coord):
                return self._game.board.get_hex_resources_for_intersection(tuple_to_coordinate(coord)).get(resource, 0)

            # Query all applicable nodes for the initial village.
            applicable_nodes = self.get_applicable_villages()
            # Choose a random node
            chosen_node = max(applicable_nodes, key=_res_counter)
            # Make the initial village(settlement)
            village_act = VILLAGE(self._current_player, chosen_node)
            # Apply village action for further construction
            village_act(self)

            # Query all applicable road options adjacent to the lastly built village
            applicable_edges = self.get_applicable_roads_from(chosen_node)
            # Choose a random edge
            chosen_path = max(applicable_edges, key=lambda path: max(_res_counter(c) for c in path))
            # Make the initial route
            road_act = ROAD(self._current_player, chosen_path)

            return village_act, road_act

        return policy

    def set_to_state(self, specific_state=None, is_initial: bool = False):
        """
        Restore the board to the initial state for repeated evaluation.

        :param specific_state: A state representation which the board reset to
        :param is_initial: True if this is an initial state to begin evaluation
        """
        assert specific_state is not None or not is_initial
        if specific_state is None:
            specific_state = self._initial
        if is_initial:
            self._initial = specific_state
            self._current = deepcopy(self._initial)
            self._rng.seed(hash(self._initial['state_id']))  # Use state_id as hash seed.
            self.reset_setup_order()  # Reset the setup order

        # Restore the board to the given state.
        self._player_number, self._current_player = _restore_state(self._game, specific_state, turnoff_check=is_initial)

        # Update memory usage
        self._update_memory_usage()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug('State has been set as follows: \n' + _unique_game_state_identifier(self._game))
            self._renderer.render_board()

    def is_game_end(self):
        """
        Check whether the given state indicate the end of the game

        :param state: A state to check. If None, then it will use the initial state.
        :return: True if the game ends at the given state
        """
        player = self._game.players[self._current_player]
        is_game_end = self._game.get_victory_points(player) >= 10
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'Querying whether the game ends in this state... Answer = {is_game_end}')
        return is_game_end

    def get_state(self) -> dict:
        """
        Get the current board state

        :return: A copy of the initial board state dictionary
        """
        if IS_DEBUG:  # Logging for debug
            self._logger.debug('Querying initial state...')

        # Check whether the game has been initialized or not.
        assert self._current is not None, 'The board should be initialized. Did you run the evaluation code properly?'
        # Return the initial state representation as a copy.
        return deepcopy(self._current)

    def get_initial_state(self) -> dict:
        """
        Get the initial board state

        :return: A copy of the initial board state dictionary
        """
        if IS_DEBUG:  # Logging for debug
            self._logger.debug('Querying initial state...')

        # Check whether the game has been initialized or not.
        assert self._initial is not None, 'The board should be initialized. Did you run the evaluation code properly?'
        # Return the initial state representation as a copy.
        return deepcopy(self._initial)

    def get_applicable_roads(self, player: int = None) -> List[Tuple[Tuple[int, int]]]:
        """
        Get the list of applicable roads

        :param player: Player index. 0 to 3. (You can ask your player ID by calling get_player_index())
        :return: A copy of the list of applicable road coordinates.
            (List of Tuple[pair] of Coordinate tuples[Q, R].)
        """
        if IS_DEBUG:  # Logging for debug
            self._logger.debug('Querying applicable roads...')

        # Query the player's current building state
        player = self._game.players[self._current_player if player is None else player]

        if not self._initial_phase:
            path_count = count_building(self._game.board.paths.values(), player)

            # If the number of current road is 15, then we cannot build a road anymore.
            if path_count[BuildingType.ROAD] >= 15:
                if IS_DEBUG:  # Logging for debug
                    self._logger.debug('All road blocks are already in use. You cannot construct it now.')
                return []

        # Read all applicable positions
        applicable_positions = \
            self._game.board.get_valid_road_coords(player,
                                                   ensure_connected=not self._initial_phase)
        # Make it to a basic python tuples
        applicable_positions = [
            tuple(sorted([coordinate_to_tuple(coord) for coord in coord_set]))
            for coord_set in applicable_positions
        ]

        # Update memory usage
        self._update_memory_usage()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'List of applicable positions for a ROAD: {applicable_positions}')
        # Return applicable positions as list of tuples.
        return applicable_positions

    def get_applicable_roads_from(self, coord: Tuple[int, int], player: int = None) -> List[Tuple[Tuple[int, int]]]:
        """
        Get the list of applicable roads that can be connected to the given coordinate.

        :param coord: Coordinate of a village or a city to query connectable roads.
        :param player: Player index. 0 to 3. (You can ask your player ID by calling get_player_index())

        :return: A copy of the list of applicable road coordinates from the given coordinate.
            (List of Tuple[pair] of Coordinate tuples[Q, R].)
        """
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'Querying applicable roads for {coord}...')

        # Query the player's current building state
        player = self._game.players[self._current_player if player is None else player]

        if not self._initial_phase:
            path_count = count_building(self._game.board.paths.values(), player)

            # If the number of current road is 15, then we cannot build a road anymore.
            if path_count[BuildingType.ROAD] >= 15:
                if IS_DEBUG:  # Logging for debug
                    self._logger.debug('All road blocks are already in use. You cannot construct it now.')
                return []

        # Read all applicable positions
        applicable_positions = \
            self._game.board.get_valid_road_coords(player,
                                                   connected_intersection=tuple_to_coordinate(coord),
                                                   ensure_connected=True)
        # Make it to a basic python tuples
        applicable_positions = [
            tuple(sorted([coordinate_to_tuple(coord) for coord in coord_set]))
            for coord_set in applicable_positions
        ]

        # Update memory usage
        self._update_memory_usage()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'List of applicable positions for a ROAD: {applicable_positions}')
        # Return applicable positions as list of tuples.
        return applicable_positions

    def get_applicable_villages(self, player: int = None) -> List[Tuple[int, int]]:
        """
        Get the list of applicable villages

        :param player: Player index. 0 to 3. (You can ask your player ID by calling get_player_index())
        :return: A copy of the list of applicable village coordinates.
            (List of Coordinate tuples[Q, R].)
        """
        # Query the player's current building state
        player = self._game.players[self._current_player if player is None else player]

        if not self._initial_phase:
            village_count = count_building(self._game.board.intersections.values(), player)

            # If the number of current village is 5, then we cannot build a village anymore.
            if village_count[BuildingType.SETTLEMENT] >= 5:
                if IS_DEBUG:  # Logging for debug
                    self._logger.debug('All village blocks are already in use. You cannot construct it now.')
                return []

        # Read all applicable positions
        applicable_positions = \
            self._game.board.get_valid_settlement_coords(player, ensure_connected=not self._initial_phase)
        # Make it to a basic python tuples
        applicable_positions = [
            coordinate_to_tuple(coord)
            for coord in applicable_positions
        ]

        # Update memory usage
        self._update_memory_usage()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'List of applicable positions for a VILLAGE: {applicable_positions}')
        # Return applicable positions as list of tuples.
        return applicable_positions

    def get_applicable_cities(self, player: int = None) -> List[Tuple[int, int]]:
        """
        Get the list of applicable villages

        :param player: Player index. 0 to 3. (You can ask your player ID by calling get_player_index())
        :return: A copy of the list of applicable village coordinates.
            (List of Coordinate tuples[Q, R].)
        """
        # Query the player's current building state
        player = self._game.players[self._current_player if player is None else player]
        village_count = count_building(self._game.board.intersections.values(), player)

        # If the number of current city is 4, then we cannot build a city anymore.
        if village_count[BuildingType.CITY] >= 4:
            if IS_DEBUG:  # Logging for debug
                self._logger.debug('All city blocks are already in use. You cannot construct it now.')
            return []

        # Read all applicable positions
        applicable_positions = \
            self._game.board.get_valid_city_coords(player)
        # Make it to a basic python tuples
        applicable_positions = [
            coordinate_to_tuple(coord)
            for coord in applicable_positions
        ]

        # Update memory usage
        self._update_memory_usage()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'List of applicable positions for a CITY: {applicable_positions}')
        # Return applicable positions as list of tuples.
        return applicable_positions

    def get_resource_cards(self) -> Dict[str, int]:
        """
        Get the number of resource cards that you have.

        :return: Dictionary of resource to number of cards mapping.
        """
        resources = {
            str(res): count
            for res, count in self._game.players[self._player_number].resources.items()
        }

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'Querying current resource counts: {resources}')

        # Update memory usage
        self._update_memory_usage()

        return resources

    def get_longest_route(self, player: int = None) -> int:
        """
        :param player: Player index. 0 to 3. (You can ask your player ID by calling get_player_index())

        :return: The length of the longest trading route for the player.
        """
        player = self._game.players[self._current_player if player is not None else player]
        long_route = self._game.board.calculate_player_longest_road(player)
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'Querying the length of the longest route: {long_route}')

        # Update memory usage
        self._update_memory_usage()

        return long_route

    def get_trading_rate(self, resource: str) -> int:
        """
        Compute your trading rate for the given resources
        :param resource: The resource to sell
        :return: The minimum number of resources required to get one required resource.
        If trading is impossible, then -1 will be given.
        """
        # Get all possible trade conditions
        trading_conds = self._game.players[self._current_player].get_possible_trades()
        # Filter out other resources
        resource = Resource[resource.upper()]
        trading_conds = [-c[resource] for c in trading_conds
                         if c.get(resource, 0) < 0]

        if not trading_conds:
            # If you cannot do trading due to lack of resources, the trading rate will be returned as -1.
            if IS_DEBUG:  # Logging for debug
                self._logger.debug(f'Not enough {resource} resources for TRADE.')
            return -1

        # Return minimum trading rate
        min_cond = min(trading_conds)
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'To get one of other resource cards, you need {min_cond} {resource} cards.')

        # Update memory usage
        self._update_memory_usage()

        return min_cond

    def get_next_dice_roll(self) -> int:
        """
        Move to the next turn, and rolling dices.
        :return: The number from two dices.
        """

        # Move to the next turn
        # self._dice_roll += 1
        # Update memory usage
        self._update_memory_usage()

        # Return 7 always.
        return 7

    def get_current_memory_usage(self):
        """
        :return: Current memory usage for the process having this board
        """
        try:
            return self._process_info.memory_info().rss
        except NoSuchProcess:
            if self._max_memory >= 0:
                self._logger.warning('As tracking the process has been failed, '
                                     'I turned off memory usage tracking ability.')
                self._max_memory = -1
            return -1

    def get_max_memory_usage(self):
        """
        :return: Maximum memory usage for the process having this board
        """
        return self._max_memory

    def _update_memory_usage(self):
        """
        [PRIVATE] updating maximum memory usage
        """
        if self._max_memory >= 0:
            self._max_memory = max(self._max_memory, self.get_current_memory_usage())

    def simulate_action(self, state: dict = None, *actions: Action) -> dict:
        """
        Simulate given actions.

        Usage:
            - `simulate_action(state, action1)` will execute a single action, `action1`
            - `simulate_action(state, action1, action2)` will execute two consecutive actions, `action1` and `action2`
            - ...
            - `simulate_action(state, *action_list)` will execute actions in the order specified in the `action_list`

        :param state: State where the simulation starts from. If None, the simulation starts from the initial state.
        :param actions: Actions to simulate or execute.
        :return: The last state after simulating all actions
        """
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'------- SIMULATION START: {actions} -------')

        # Restore to the given state
        self.set_to_state(state)

        # Check whether these actions are valid
        if self._initial_phase:
            if len(actions) > 2:
                raise ValueError('On the initial phase, you can simulate at most two actions.')
            if len(actions) == 2 and {type(a) for a in actions} != {VILLAGE, ROAD}:
                raise ValueError('When executing two consecutive actions, '
                                 'you need to execute VILLAGE and ROAD actions during the initial phase')
            if len(actions) == 1 and not isinstance(actions[0], (VILLAGE, ROAD, PASS)):
                raise ValueError('You need to execute VILLAGE, ROAD, or PASS actions during the initial phase')

        for act in actions:  # For each actions in the variable arguments,
            # Run actions through calling each action object. If error occurs, raise as it is.
            act(self)

            # Break the loop if the game ends within executing actions.
            if not self._initial_phase and self.is_game_end():
                break

        # Copy the current state to return
        self._current = _read_state(self._game, self._player_number, self._current_player)

        if IS_DEBUG:  # Logging for debug
            self._logger.debug('State has been changed to: \n' + _unique_game_state_identifier(self._game))
            self._renderer.render_board()
            self._logger.debug('------- SIMULATION ENDS -------')

        # Update memory usage
        self._update_memory_usage()

        return deepcopy(self._current)

    def diversity_of_place(self, coord: Tuple[int, int]) -> set:
        """
        Evaluate the diversity of given place.
        Here, the diversity is the number of resource types (hex tile types) neighboring the given position.

        Usage:
            - `diversity_of_state(coordinate)` will give you a single diversity score of the given position.

        :param coord: Coordinate to evaluate.
        :return: The set of resource types (hex tile types) neighboring the given position
        """

        return {r.name
                for r, c in self._game.board.get_hex_resources_for_intersection(tuple_to_coordinate(coord)).items()
                if c > 0}

    def diversity_of_road(self, path_coord: Tuple[Tuple[int, int]]) -> set:
        """
        Evaluate the diversity of given place.
        Here, the diversity is the number of resource types (hex tile types) neighboring the given road path.

        Usage:
            - `diversity_of_state(coordinate)` will give you a single diversity score of the given road path.

        :param path_coord: Coordinate to evaluate.
        :return: The set of resource types (hex tile types) neighboring the given position
        """

        return self.diversity_of_place(path_coord[0]).union(self.diversity_of_place(path_coord[1]))

    def diversity_of_state(self, state: dict = None) -> int:
        """
        Evaluate the diversity of given state.
        Here, the diversity is the number of resource types (hex tile types) neighboring the current settlements.

        Usage:
            - `diversity_of_state(state)` will give you a single diversity score of the current state.

        :param state: State to evaluate. If None, the evaluation uses the initial state.
        :return: The number of resource types (hex tile types) neighboring the current settlements.
        """
        # Restore to the given state
        self.set_to_state(state)

        # Get the current number of cards
        player = self._game.players[self._player_number]
        # Evaluate the expected resource income
        hex_types = set()
        for roll, prob in DICE_ROLL.items():
            players_yields = self._game.board.get_yield_for_roll(roll)
            if player not in players_yields:
                continue

            yields = players_yields[player].total_yield
            hex_types.update({key for key, value in yields.items() if value > 0})

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'Hex types near this player: {hex_types}')

        # Update memory usage
        self._update_memory_usage()
        # Pop desert
        hex_types.difference_update([HexType.DESERT])

        # Return evaluation result
        return len(hex_types)

    def get_player_id(self):
        return self._player_number


# Export only GameBoard and RESOURCES.
__all__ = ['GameBoard', 'RESOURCES', 'IS_DEBUG', 'IS_RUN']
