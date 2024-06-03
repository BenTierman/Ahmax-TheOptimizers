from random import choice
from time import time
from traceback import print_exc, format_exc
from typing import Tuple, List, Callable, Dict, Generator

from action import *
from board import GameBoard


class Agent:  # Do not change the name of this class!
    """
    An agent class

    The list of algorithms that you can use
    - AND-OR Search or other variants
    - Online DFS or other Online variant of uninformed/heuristic search algorithms
    - LRTA*s
    """

    def combination_of_initial_villages(self, board: GameBoard):
        # Initializing
        player = board.get_player_id()
        start_state = board.get_initial_state()
        unvalid_placements = {}
        all_villages = board.get_applicable_villages(player = player)
        diversity_combo = {5: {}, 4: {},3: {}, 2: {}, 1: {}, 0: {}}
        roads = {}

        #Bad code - should perhaps fix before delivering
        for i in range(len(board.get_remaining_setup_order()[:player]) + 1):
            start_state = board.simulate_action(start_state, PASS())

        remaining_order = board.get_remaining_setup_order()
        # The player will put a village and a road block on his/her turn.
        for coord in board.get_applicable_villages(player=player):
            board.set_to_state(start_state)

            # Test all possible villages
            village1 = VILLAGE(player, coord)
            # Apply village construction for further construction
            board.simulate_action(start_state, village1)
            # Construction of ROAD
            path_coord = board.get_applicable_roads_from(coord, player=player)[0]
            road1 = ROAD(player, path_coord)
            roads[coord] = road1

            # Simulating the new state
            new_state = board.simulate_action(start_state, village1, road1) 
            board.set_to_state(new_state)
            
            board.reset_setup_order(remaining_order)
            passing_state = new_state
            
            #Bad code - should perhaps fix before delivering (possible to reset the setup order instead of skipping the pass?) // Passing other players 
            for i in range(len(board.get_remaining_setup_order()[:board.get_remaining_setup_order().index(player)])+1):
                passing_state = board.simulate_action(passing_state, PASS())


            # Finding unvalid placements of villages nearby
            possible_villages = board.get_applicable_villages(player=player)
            unvalid_villages = result = [v for v in all_villages if v not in possible_villages]
            unvalid_placements[coord] = unvalid_villages


            # Inner for-loop
            for coord2 in board.get_applicable_villages(player=player):
                board.set_to_state(passing_state)
                # Test all possible villages
                village2 = VILLAGE(player, coord2)

                # Apply village construction for further construction
                board.simulate_action(passing_state, village2)
                # ROAD
                path_coord = board.get_applicable_roads_from(coord2, player=player)[0]
                road2 = ROAD(player, path_coord)
                # Simulating the new state
                new_new_state = board.simulate_action(passing_state, village2, road2) 
                diversity = board.diversity_of_state(new_new_state)

                inner_dict_combo = diversity_combo[diversity]
                if(coord in inner_dict_combo):
                    inner_dict_combo[coord].append(coord2)
                else:
                    inner_dict_combo[coord] = [coord2]
        
        return diversity_combo, roads, unvalid_placements

    def decide_new_village(self, board: GameBoard, time_limit: float = None) -> Callable[[dict], Tuple[Action, Action]]:
        """
        This algorithm search for the best place of placing a new village.

        :param board: Game board to manipulate
        :param time_limit: Timestamp for the deadline of this search.
        :return: A Program (Function) to execute
        """

        player = board.get_player_id()
        diversity_combo, roads, unvalid_placements = self.combination_of_initial_villages(board)

        def _plan_execute(state):
            placed_villages = []
            players_village = None

            for village, dict in state["board"]["intersections"].items():
                if(dict["type"] == "SETTLEMENT" and dict["owner"] != None):
                    if(dict["owner"] == player):
                        players_village = village
                    placed_villages.append(village)
            
            #Unvalid villages
            unvalid_placements_state = []
            unvalid_placements_state.extend(placed_villages)
            for village in placed_villages:
                unvalid_placements_state.extend(unvalid_placements[village])
            
            # Finding first initial village
            if(players_village == None):
                #Finding best placement based on the number of valid combinations
                max_length = 0
                max_key = None

                index = 5

                while max_key == None:
                    for key, array in diversity_combo[index].items():
                        if(key not in unvalid_placements_state):
                            # Filter out values that are in unvalid_placements_state
                            valid_values = [v for v in array if v not in unvalid_placements_state]
            
                            if len(valid_values) > max_length:
                                max_length = len(valid_values)
                                max_key = key
                    index-=1
                
                return VILLAGE(player,max_key),roads[max_key]
            
            #Fining second initial village
            else:
                for i in range(5, -1, -1):
                    possible_villages = diversity_combo[i][players_village]
                    for village in possible_villages:
                        if(village not in unvalid_placements_state):
                            return VILLAGE(player,village), roads[village]
            return (None, None)
        
        return _plan_execute