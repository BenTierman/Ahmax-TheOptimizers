# Package for logging your execution
import logging
import math
import os
# Package for random seed control
import random
# A dictionary class which can set the default value
from collections import defaultdict
# Package for runtime importing
from importlib import import_module
# Package for multiprocessing (evaluation will be done with multiprocessing)
from multiprocessing import Process, Queue
# Querying function for the number of CPUs
from os import cpu_count
# Package for file handling
from pathlib import Path
from time import time, sleep
# Package for writing exceptions
from traceback import format_exc
from typing import Callable

# Memory usage tracking function
import psutil as pu

from action import VILLAGE
# Package for problem definitions
from board import *
# Function for loading your agents
from agents.load import get_all_agents

#: Size of MB in bytes
MEGABYTES = 1024 ** 2
#: The number of games to run the evaluation
GAMES = 5
#: LIMIT FOR A SINGLE EXECUTION, 11 minutes. (+- 1 minute for space)
TIME_LIMIT = 60 * 11
#: LIMIT OF MEMORY USAGE, 1GB
MEMORY_LIMIT = 1 * 1024 * MEGABYTES

# Set a random seed
random.seed(5606)


def _average(items, default=0):
    return sum(items) / len(items) if len(items) else default


def _compute_efficiency_score(m, t):
    if math.isnan(m) or math.isnan(t):
        return 0

    return (2 if m <= 10 else (1 if m <= 100 else 0.5 * (m <= 500))) + \
        (1 if t <= 60 else 0.5 * (t <= 300))

def evaluate_algorithm(agent_name, initial_state, result_queue: Queue):
    """
    Run the evaluation for an agent.
    :param agent_name: Agent to be evaluated
    :param initial_state: Initial state for the test
    :param result_queue: A multiprocessing Queue to return the execution result.
    """
    # Initialize logger
    if not IS_RUN:
        logging.basicConfig(level=logging.DEBUG if IS_DEBUG else logging.INFO,
                            format='%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s',
                            filename=f'execution-{agent_name}.log',
                            # Also, the output will be logged in 'execution-(agent).log' file.
                            filemode='w+',
                            force=True)  # The logging file will be overwritten.
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s',
                            force=True)

    # Set up the given problem
    problem = GameBoard()
    problem._initialize()
    problem.set_to_state(initial_state, is_initial=True)

    # Log initial memory size
    init_memory = problem.get_current_memory_usage()
    logger = logging.getLogger('Evaluate')

    # Initialize an agent
    try:
        logger.info(f'Loading {agent_name} agent to memory...')
        module = import_module(f'agents.{agent_name}')
        agent = module.Agent()
    except Exception as e:
        # When agent loading fails, send the failure log to main process.
        failure = format_exc()
        logger.error('Loading failed!', exc_info=e)
        result_queue.put((agent_name, failure, float('NaN'), float('NaN'), float('NaN')))
        return

    # Do search
    solution = None
    failure = None  # Record for Performance measure I
    diversity_score = 0  # Record for Performance measure II
    num_calls = float('inf')  # Record for Performance measure III

    logger.info(f'Begin to search using {agent_name} agent.')
    time_start = time()
    try:
        solution = agent.decide_new_village(problem, time_limit=time_start + 600)  # 10 minutes
        assert isinstance(solution, Callable), f'Solution should be a function! Received: {type(solution)}'
    except:
        failure = format_exc()

    time_end = time()
    time_delta = min(600, max(int(time_end - time_start), 0))
    if time_delta >= 600:
        result_queue.put((agent_name,
                          f'Time limit exceeded! {time_delta} seconds passed', float('NaN'), float('NaN'), float('NaN')))
        return

    # Get maximum memory usage during search (Performance measure IV)
    max_memory_usage = int(max(0, problem.get_max_memory_usage() - init_memory) / MEGABYTES / 10) * 10
    logger.info(f'Search finished for {agent_name}, using {max_memory_usage}MB during search.')
    # Ignore memory usage below 10MB.
    max_memory_usage = max(10, max_memory_usage)

    # Execute the solution for evaluation
    if solution is not None:
        try:
            problem.set_to_state(initial_state)
            state = problem.run_initial_setup({problem.get_player_id(): solution})
            diversity_score = problem.diversity_of_state(state)  # Performance measure II
        except:
            failure = format_exc()

    if IS_DEBUG:
        logger.debug(f'Execution Result: Failure {not not failure}, {max_memory_usage}MB/{time_delta}sec, '
                     f'diversity score = {diversity_score}.')
    result_queue.put((agent_name, failure, diversity_score, max_memory_usage, time_delta))


# Main function
if __name__ == '__main__':
    # Problem generator for the same execution
    prob_generator = GameBoard()
    # List of all agents
    all_agents = get_all_agents()

    # Performance measures
    failures = defaultdict(list)  # This will be counted across different games
    failure_counts = defaultdict(list)
    diversity_avg = defaultdict(list)  # This will be computed as average score
    mem_avg = defaultdict(list)  # This will be computed as average score
    time_avg = defaultdict(list)  # This will be computed as average score
    last_execution = defaultdict(lambda: (1, float('NaN'), float('NaN'), float('NaN')))

    def _print(t):
        """
        Helper function for printing rank table
        :param t: Game trial number
        """

        # Print header
        print('-' * 80)
        print(f'\nCurrent game trial: #{t}')
        print(f' AgentName    |  Failure?  Diversity  MemoryUsg  TimeSpent | Score ')
        print('=' * 14 + '|' + '=' * 44 + '|' + '=' * 30)

        for agent in all_agents:
            if agent in last_execution:
                is_failure, diversity, memory, time_spent = last_execution[agent]
            else:
                is_failure, diversity, memory, time_spent = 1, float('NaN'), float('NaN'), float('NaN')

            # Add items
            failure_counts[agent].append(is_failure)
            if not math.isnan(diversity):
                diversity_avg[agent].append(diversity)
            if not math.isnan(memory):
                mem_avg[agent].append(memory)
            if not math.isnan(time_spent):
                time_avg[agent].append(time_spent)

            # Name print option
            key_print = agent if len(agent) < 13 else agent[:9] + '...'

            # Score computation
            failure_score = min(10, sum(failure_counts[agent])) / min(10, len(failure_counts[agent]))
            diversity_score = _average(diversity_avg[agent]) / 5
            memory_score = _average(mem_avg[agent], default=float('NaN'))
            time_score = _average(time_avg[agent], default=float('NaN'))
            efficiency_score = _compute_efficiency_score(memory_score, time_score)

            score = (1 - failure_score) * (2 * diversity_score + efficiency_score)

            print(f' {key_print:12s} |  {"FAILURE!" if is_failure else "        "} '
                  f' {diversity:9.2f}  {memory:7.2f}MB  {time_spent:6.0f}sec |'
                  f' (1 - {failure_score:3.1f}) * [ 2 * {diversity_score:3.1f} + {efficiency_score:3.1f} ]'
                  f' = {score:4.2f}')

            # Write-down the failures
            with Path(f'./failure_{agent}.txt').open('w+t') as fp:
                fp.write('\n\n'.join(failures[agent]))

    # Start evaluation process (using multi-processing)
    process_results = Queue(len(all_agents) * 2)
    process_count = max(cpu_count() - 2, 1)

    def _execute(prob, agent_i):
        """
        Execute an evaluation for an agent with given initial state.
        :param prob: Initial state for a problem
        :param agent_i: Agent
        :return: A process
        """
        proc = Process(name=f'EvalProc', target=evaluate_algorithm, args=(agent_i, prob, process_results), daemon=True)
        proc.start()
        proc.agent = agent_i  # Make an agent tag for this process
        last_execution[agent_i] = 1, float('NaN'), float('NaN'), float('NaN')
        return proc


    def _read_result(res_queue):
        """
        Read evaluation result from the queue.
        :param res_queue: Queue to read
        :param exceeds: failure message for agents who exceeded limits
        """
        while not res_queue.empty():
            agent_i, failure_i, div_i, mem_i, time_i = res_queue.get()
            if failure_i is None:
                last_execution[agent_i] = 0, div_i, mem_i, time_i
            else:
                last_execution[agent_i] = 1, float('NaN'), float('NaN'), float('NaN')
                failures[agent_i].append(failure_i)


    for trial in range(GAMES):
        # Clear all previous results
        last_execution.clear()
        while not process_results.empty():
            process_results.get()

        # Generate new problem
        prob_generator._initialize()
        prob_spec = prob_generator.get_initial_state()
        logging.info(f'Trial {trial} begins!')

        # Execute agents
        processes = []
        agents_to_run = all_agents.copy()
        random.shuffle(agents_to_run)

        exceed_limit = {}  # Timeout limit
        while agents_to_run or processes:
            # If there is a room for new execution, execute new thing.
            if agents_to_run and len(processes) < process_count:
                alg = agents_to_run.pop()
                processes.append((_execute(prob_spec, alg), time()))

            new_proc_list = []
            for p, begin in processes:
                if not p.is_alive():
                    continue

                # Print running info
                now = time()
                print(f'Running "{p.agent}" for {now - begin:4.0f}/{TIME_LIMIT} second(s).', end='\r')

                # For each running process, check for timeout
                if begin + TIME_LIMIT < now:
                    p.terminate()
                    exceed_limit[p.agent] = \
                        f'Process is running more than {TIME_LIMIT} sec, from ts={begin}; now={time()}'
                    logging.error(f'[TIMEOUT] {p.agent} / '
                                  f'Process is running more than {TIME_LIMIT} sec, from ts={begin}; now={time()}')
                else:
                    try:
                        p_bytes = pu.Process(p.pid).memory_info().rss
                        if p_bytes > MEMORY_LIMIT:
                            p.terminate()
                            exceed_limit[p.agent] = \
                                f'Process consumed memory more than {MEMORY_LIMIT / MEGABYTES}MB (used: {p_bytes / MEGABYTES}MB)'
                            logging.error(f'[MEM LIMIT] {p.agent} / '
                                          f'Process consumed memory more than {MEMORY_LIMIT / MEGABYTES}MB (used: {p_bytes / MEGABYTES}MB)')
                        else:
                            new_proc_list.append((p, begin))
                    except pu.NoSuchProcess:
                        new_proc_list.append((p, begin))

            # Prepare for the next round
            processes = new_proc_list
            # Read result from queue
            _read_result(process_results)

            # Wait for one seconds
            sleep(1)

        # Read results
        logging.info(f'Reading results at Trial {trial}')
        _read_result(process_results)

        for agent_i, failure_i in exceed_limit.items():
            last_execution[agent_i] = 1, float('NaN'), float('NaN'), float('NaN')
            failures[agent_i].append(failure_i)

        # Sort the results for each performance criteria and give ranks to agents
        _print(trial)
