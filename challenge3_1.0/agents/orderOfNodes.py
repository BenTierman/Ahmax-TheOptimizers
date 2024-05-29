from random import choice
from time import time
from traceback import print_exc, format_exc
from typing import Tuple, List, Callable, Dict, Generator

from action import *
from board import GameBoard

explored = {}
global y
y = 0

def sort_array(array):
    #Sort the array
    sorted_array = sorted(array, key=lambda x: (x[0], x[1]))
    return sorted_array

def in_explored(board: GameBoard, state: dict):
    #Finding placed villages
    array = [coord for coord, value in state["board"]["intersections"].items() if value["type"] == "SETTLEMENT"]

    #Sort the combination before checking with explored
    key = str(sort_array(array))

    #Check if combination of villages already exists in explored
    return explored.get(key, None)

def add_in_explored(board, state: dict):
    #Finding placed villages
    array = [coord for coord, value in state["board"]["intersections"].items() if value["type"] == "SETTLEMENT"]
    
    #Sort the combination before adding to explored
    key = str(sort_array(array))

    explored[key] = state["state_id"]

def expand_board_state(board: GameBoard, state: dict, player: int):
    """
    Expand all possible children of given state, when a player placing his/her village and road, using the board.

    :param board: Game board to manipulate
    :param state: State to expand it children
    :param player: Player ID who is currently doing his/her initial setup procedure.

    :returns: A generator
        Each item is a tuple of VILLAGE action, ROAD action and the resulting state dictionary.
    """
    # Pass the board to the next player
    state = board.simulate_action(state, PASS())

    if (player == board.get_player_id()):
        #print the remaining setup order
        #print(board.get_remaining_setup_order())
        player_diversity = set()
        temp_diversity = set()
        max_diversity = set()
        best_coord = None
        if len(board.get_remaining_setup_order()) <= 3:
            player_settlement = [coord for coord, value in state["board"]["intersections"].items() if value["type"] == "SETTLEMENT" and value["owner"] == player]
            player_diversity = board.diversity_of_place(player_settlement[0])
            #print('Player Diversity:', player_diversity)

        for coord in board.get_applicable_villages(player=player):
            board.set_to_state(state)
            diversity = board.diversity_of_place(coord)
            #print('Diversity:', diversity)
            if (len(board.get_remaining_setup_order()) > 3) and (len(diversity) == 3):
                temp_diversity.clear()
                player_diversity.update(diversity)
                best_coord = coord
                break
            
            temp_diversity.clear()
            temp_diversity.update(player_diversity)
            temp_diversity.update(diversity)
            
            if len(temp_diversity) > len(player_diversity):
                max_diversity.update(temp_diversity)
                best_coord = coord
                
        player_diversity.update(max_diversity)
        #print('Best Coord:', best_coord, 'Diversity:', player_diversity)
        # Test all possible villages
        village = VILLAGE(player, best_coord)
        # Apply village construction for further construction
        board.simulate_action(state, village)

        for path_coord in board.get_applicable_roads_from(best_coord, player=player)[:1]:
            # Test all possible roads nearby that village
            road = ROAD(player, path_coord)
            yield village, road, board.simulate_action(state, village, road)

    # The player will put a village and a road block on his/her turn.
    else:
        for coord in board.get_applicable_villages(player=player):
            board.set_to_state(state)
            # Test all possible villages
            village = VILLAGE(player, coord)
            # Apply village construction for further construction
            board.simulate_action(state, village)
        
            for path_coord in board.get_applicable_roads_from(coord, player=player)[:1]:
                # Test all possible roads nearby that village
                road = ROAD(player, path_coord)
                yield village, road, board.simulate_action(state, village, road)  # Yield this simulation result


def cascade_expansion(board: GameBoard, state: dict, players: List[int]):
    """
    Expand all possible children of given state, when several players placing his/her village and road, using the board.

    :param board: Game board to manipulate
    :param state: State to expand it children
    :param players: A list of Player IDs who are currently doing their initial setup procedure.

    :returns: A generator
        Each item is a resulting state dictionary, after all construction of given players
    """
    if len(players) == 0:
        yield state
        return

    current_player = players[0]
    next_players = players[1:]
    current_order = board.get_remaining_setup_order()
    #print (players)


    i=1
    # print('Current Player:', current_player)
    for _, _, next_state in expand_board_state(board, state, current_player):
        board.reset_setup_order(current_order[1:])
        for next_next_state in cascade_expansion(board, next_state, next_players):
            yield next_next_state
        if (current_player == board.get_player_id() and i==1):
            break


class Agent:  # Do not change the name of this class!
    """
    An agent class, with and-or search (DFS) method
    """

    def or_search(self, board: GameBoard, state: dict, remaining_order: List[int], path: list) -> list:
        """
        An Or search function.
        """
        board.set_to_state(state)
        player_id = board.get_player_id()
        board.reset_setup_order(remaining_order)

        if player_id not in remaining_order:  # After second setup turn. We reached the end point.
            return []  # Do nothing

        if state['state_id'] in path:
            raise Exception(f'We reached a cycle! {path} and {state["state_id"]}')

        # For each children state, call AND search.
        error_cause = []

        #Added only one state for OR (DELETE WHEN PUSHING CODE)
        i=1
        # print("here")
        for village, road, next_state in expand_board_state(board, state, player=player_id):
            try:
                board.set_to_state(next_state)
                and_plan = self.and_search(board, next_state, remaining_order[1:], path + [state['state_id']])
                return [(village, road), and_plan]
                # Call (village, road) at this state, and run other actions by following dictionary of and_plan
            except:
                error_cause.append(format_exc())
                pass
            if (i==1):
                break

        raise Exception('No solution exists: Errors on all AND children.\n [Cause]\n' + '\n'.join(error_cause) + '-' * 80)

    def and_search(self, board: GameBoard, state: dict, remaining_order: list, path: list) -> dict:
        """
        An And search function.
        """
        # If the remaining setup order does not contain the current player ID, finish search without doing anything
        player_id = board.get_player_id()
        board.reset_setup_order(remaining_order)
        if player_id not in remaining_order:  # We don't have to search anymore
            return {}  # Do nothing

        players_turn = remaining_order.index(player_id)
        before_player = remaining_order[:players_turn]
        order_from_player = remaining_order[players_turn:]
        # print("before_player", before_player)
        # print("order_from_player", order_from_player)
        # print("players_turn", players_turn)

        if before_player:
            path = path + [state['state_id']]

        plans = {}

        # For each children state (after doing all other's actions), call OR search.
        for next_state in cascade_expansion(board, state, before_player):
            # We will call OR search here. We will throw the error as it is.
            board.set_to_state(next_state)

            #Decide whether to explore further or not -> line 126 - 134 (NEW)
            explored_state = in_explored(board, next_state)
            
            global y
            if(explored_state != None):
                plans[next_state['state_id']] = explored_state
                y+=1
                print(y)
            else:
                or_plan = self.or_search(board, next_state, order_from_player, path)
                # Call or_plan if we reach this state
                plans[next_state['state_id']] = or_plan
                
                #Add state to explored
                add_in_explored(board, next_state)

        return plans

    def decide_new_village(self, board: GameBoard, time_limit: float = None) -> Callable[[str], Tuple[Action, Action]]:
        """
        This algorithm search for the best place of placing a new village.

        :param board: Game board to manipulate
        :param time_limit: Timestamp for the deadline of this search.
        :return: A Program (Function) to execute
        """
        initial = board.get_state()
        expansion_order = board.reset_setup_order()
        plans = self.and_search(board, initial, expansion_order, [])
        print(len(explored.keys()))
        def _plan_execute(state_id):
            plan = plans.get(state_id, None)
            if plan is None:
                return None, None

            actions, next_step_plan = plan
            plans.clear()
            plans.update(next_step_plan)

            return actions

        return _plan_execute
