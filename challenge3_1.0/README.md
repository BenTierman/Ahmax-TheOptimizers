# CAU56753 Challenge III: Search on nondeterministic/unobservable environment

## Problem definition / 문제정의

The third programming challenge is making a winning agent, against other agents.

세번째 프로그래밍 도전과제는 다른 에이전트를 이기는 에이전트를 만드는 것입니다.

In this challenge, you have to make a search algorithm for finding the best possible initial settlements, before observing other's action.

이번 도전과제에서, 여러분은 다른 플레이어의 행동을 관측하지 않고, 가장 좋은 초기 정착촌을 건설하는 탐색 알고리즘을 만들어야 합니다.

Here, 'best' means that the highest diversity in hex types neighboring the initial settlements.

여기서, '가장 좋은'이라는 단어의 의미는 초기 정착촌 주변 육각형 타일 유형의 다양성이 높은 상태를 말합니다.

Here's PEAS description. According to the description, the system will automatically run your code and give you the evaluation result.

아래에 PEAS 상세정보가 주어져 있습니다. 평가 시스템은 PEAS 정보에 따라 여러분의 코드를 실행하고 평가하여, 평가 결과를 제공할 것입니다.

(Are you curious about how to run the evaluation? Then, go to [RUN](./#RUN) section!)
(어떻게 평가를 실행하는지 궁금하다면, [RUN](./#RUN) 부분으로 넘어가세요!)

### PEAS description

#### Performance measure (수행지표)

We'll use absolute evaluation. The evaluation score will be = {1 - (error score)} × {2 × (diversity score) + (efficiency score)}.

절대평가를 사용합니다. 평가 점수는 다음과 같습니다: {1 - (error score)} × {2 × (diversity score) + (efficiency score)}.

  1. Error score: computed as follows.
  
     오류 점수는 다음과 같이 계산됩니다.

     * min(10, The number of errored trials) / min(10, The number of total trials)

       (총 오류 횟수와 10 중 작은 값) / (전체 실행 수와 10 중 작은 값)

  2. Diversity score: computed as follows.

     다양성 점수는 다음과 같이 계산됩니다.

     * (The number of distinct hex types, except the dessert) / 5

       (사막을 제외한 육각형 타일의 종류 개수) / 5
     
  3. Efficiency score: Sum of the followings.

     효율성 점수는 다음을 합산합니다.

     * Max memory usage / 메모리 사용량
       * 0 ~ 10MB, 2 points
       * 10 ~ 100MB, 1 point
       * 100MB ~ 500MB, 0.5 point
       * 500MB ~, 0 point
       * Note: if your memory usage exceeds 1GB, the evaluation program will consider it as failure.
         여러분의 메모리 사용량이 1GB를 초과하면, 평가 프로그램은 그 시도를 실패한 것으로 계산합니다.
     
     * Time for searching / 탐색 시간
       * 0 ~ 1 minutes, 1 point
       * 1 ~ 5 minutes, 0.5 point
       * 5+ minutes, 0 point
       * Note: if your time consumption exceeds 10 minutes, the evaluation program will consider it as failure.
         여러분의 시간 소비가 10분을 초과하면, 평가 프로그램은 그 시도를 실패한 것으로 계산합니다.


**Note**: Evaluation program will automatically build a table that sort your codes' evaluation result in the order of performance measure. Also, the algorithm should finish its search procedure **within 10 minutes**.

**참고**: 평가 프로그램이 여러분 코드의 평가 결과를 수행지표 순서대로 정렬하여 표 형태로 표시해줄 예정입니다. 그리고, 알고리즘의 탐색 절차는 **10분 이내**에 끝나야 합니다.

**Note**: Also, the program should use lower than **1GB in total**, including your program code on the memory. For your information: when I tested with `default.py`, the memory usage after initial loading is 22MB.

**참고**: 또한, 프로그램은 (여러분의 코드를 포함) 최대 **1GB까지** 메모리를 사용할 수 있습니다. 참고로, `default.py`로 테스트했을 때, 상태 초기화 후 메모리 사용량은 22MB였습니다. 


#### Environment (환경)

Okay, the environment follows the initial set-up procedure in the Settlers of Catan game. Here, your agent is not the only one to settle down. But, different from the previous challenge, your search process will be done before other's action. So, you need to do is making a plan (or program) using your belief states. Note that the game board is randomly generated.

이번 도전과제의 환경은 카탄 게임의 초기 마을 설정 과정을 따릅니다. 그러니까, 여러분의 에이전트만 초기 마을 설정을 하고 있는 것이 아니라, 다른 에이전트도 함께 하고 있습니다. 다만, 이전 도전과제와 다른 것은, 여러분의 탐색 절차가 다른 플레이어의 행동 이전에 진행된다는 것입니다. 그러니, 여러분이 해야 할 일은 여러분의 믿음 상태를 바탕으로 계획(또는 프로그램)을 세우는 것입니다.

1. The environment will call your decide_new_village() function before the initial setting phase, once.

    환경은 초기 정착촌 건설 과정이 진행되기 전, 여러분 에이전트의 'decide_new_village()' 함수를 딱 한번 호출할겁니다.

2. The environment will run your plan (or program) without asking the agent when it's your turn for building the initial settlement. That is, the decide_new_village() function is not called during the game. Also, the program that you returned cannot access the board.

    또, 환경은 여러분 에이전트에게 묻지 않고 차례에 따라 계획을 실행할 것입니다. 그러니까, decide_new_village() 함수는 게임 중에는 호출되지 않습니다. 또한, 여러분의 프로그램은 게임판에 접근해서는 안됩니다.

In terms of seven characteristics, the game can be classified as:

환경을 기술하는 7개의 특징을 기준으로, 게임은 다음과 같이 분류됩니다:

- Fully observable (완전관측가능)

  You know everything required to decide your action.

  여러분은 이미 필요한 모든 내용을 알고 있습니다.

- Single-agent (단일 에이전트)

  The other agents are actually doing nothing during your search procedure. So, it seems that you're the only one who pursues those performance measure.

  다른 모든 에이전트는 여러분이 탐색을 하는 동안 사실 아무것도 안 합니다. 그러므로, 그 판에서 여러분만이 수행지표를 최대화하려는 유일한 에이전트라고 생각해도 됩니다.

- Nondeterministic (비결정론적)

  There's unexpected chances of change on the board when executing the sequence of actions.

  행동을 순서대로 수행할 때, 예상치 못한 변수가 있을 수 있습니다.

- Sequential actions (순차적 행동)

  You should handle the sequence of your actions to build an initial village.

  초기 마을을 건설하기 위해서 필요한 여러분의 행동의 순서를 고민해야 합니다.

- Semi-dynamic performance (준역동적 지표)

  Note that performance metrics 1, 2 are static, but the metric 3 is dynamic metric, which changes its measure by how your algorithm works. So you need some special effort for achieving good performance measure on 3, when designing your algorithm.

  지표 1과 2는 정적이고, 지표 3은 동적입니다. 특히 지표 3은 여러분의 알고리즘 작동에 따라 변화하는 지표입니다. 그래서 알고리즘을 설계할 때, 지표 3의 변화에 신경써서 설계하는 노력이 필요합니다.

- Discrete action, perception, state and time (이산적인 행동, 지각, 상태 및 시간개념)

  All of your actions, perceptions, states and time will be discrete, although you can query about your current memory usage in the computing procedure.

  여러분의 모든 행동, 지각, 상태 및 시간 흐름은 모두 이산적입니다. 여러분이 계산 도중 메모리 사용량을 시스템에 물어볼 수 있다고 하더라도 말입니다.

- Known rules (규칙 알려짐)

  All rules basically follows the original Catan game.

  모든 규칙은 기본적으로 원래의 카탄 게임을 따릅니다.

#### Actions

You can take one of the following actions.

다음 행동 중의 하나를 할 수 있습니다.

- **VILLAGE(p, v)**: Build a village at a specific node `v` by player `p`.

  특정한 꼭짓점 `v`에 플레이어 `p`가 마을 짓기

  Here, the list of applicable nodes will be given by the board. The list may be empty if you reached the maximum number of villages, i.e., five.

  마을 짓기가 가능한 꼭짓점의 목록은 board가 제공합니다. 단, 가능한 마을의 수가 최대치인 5개에 도달한 경우, 목록은 빈 리스트로 제공될 수 있습니다.

- **ROAD(p, e)**: Build a road at a specific edge `e` by player `p`.

  특정한 모서리 `e`에 플레이어 `p`가 도로 짓기

  Here, the list of applicable edges will be given by the board.

  도로 짓기가 가능한 모서리의 목록은 board가 제공합니다.


#### Sensors

You can perceive the game state, during the search, as follows:

- The board (게임 판)
  - All the place of hexes(resources), villages, roads and ports

    모든 육각형(자원), 마을, 도로, 항구의 위치

  - You can ask the board to the list of applicable actions for.

    가능한 행동에 대해서 게임판 객체에 물어볼 수 있습니다.

  - You can ask the board about the current diversity of neighborhood hex tiles.  
  
    현재 상태에서 주변 육각형 타일의 종류 다양성을 물어볼 수 있습니다.

- Your resource cards (여러분의 자원카드 목록)


You cannot access the board when executing your plan. The only thing that your program can access is:

- The current board state (현재 보드의 상태)


## Structure of evaluation system

평가 시스템의 구조

The evaluation code has the following structure.

평가용 코드는 다음과 같은 구조를 가지고 있습니다.

```text
/                   ... The root of this project
/README.md          ... This README file
/evaluate.py        ... The entrance file to run the evaluation code
/board.py           ... The file that specifies programming interface with the board
/actions.py         ... The file that specifies actions to be called
/util.py            ... The file that contains several utilities for board and action definitions.
/agents             ... Directory that contains multiple agents to be tested.
/agents/__init__.py ... Helper code for loading agents to be evaluated
/agents/load.py     ... Helper code for loading agents to be evaluated
/agents/default.py  ... A default DFS agent 
/agents/_skeleton.py... A skeleton code for your agent. (You should change the name of file to run your code)
```

All the codes have documentation that specifies what's happening on that code (only in English).

모든 코드는 어떤 동작을 하는 코드인지에 대한 설명이 달려있습니다 (단, 영어로만).

To deeply understand the `board.py` and `actions.py`, you may need some knowlege about [`pyCatan2` library](https://pycatan.readthedocs.io/en/latest/index.html).

`board.py`와 `actions.py`를 깊게 이해하고 싶다면, [`pyCatan2` library](https://pycatan.readthedocs.io/en/latest/index.html) 라이브러리에 대한 지식이 필요할 수 있습니다.

### What should I submit?

You should submit an agent python file, which has a similar structure to `/agents/default.py`.
That file should contain a class name `Agent` and that `Agent` class should have a method named `decide_new_village(board)`.
Please use `/agents/_skeleton.py` as a skeleton code for your submission.

`/agents/default.py`와 비슷하게 생긴 에이전트 코드를 담은 파이썬 파일을 제출해야 합니다.
해당 코드는 `Agent`라는 클래스가 있어야 하고, `Agent` 클래스는 `decide_new_village(board)` 메서드를 가지고 있어야 합니다.
편의를 위해서 `/agents/_skeleton.py`를 골격 코드로 사용하여 제출하세요.

Also, you cannot use the followings to reduce your search time:

그리고 시간을 줄이기 위해서 다음에 나열하는 것을 사용하는 행위는 제한됩니다.

- multithreading / 멀티스레딩
- multiprocessing / 멀티프로세싱
- using other libraries other than basic python libraries. / 기본 파이썬 라이브러리 이외에 다른 라이브러리를 사용하는 행위

The TA will check whether you use those things or not. If so, then your evaluation result will be marked as zero.

조교가 여러분이 해당 사항을 사용하였는지 아닌지 확인하게 됩니다. 만약 그렇다면, 해당 평가 점수는 0점으로 처리됩니다.

## RUN

실행

To run the evaluation code, do the following:

1. (Only at the first run) Install the required libraries, by run the following code on your terminal or powershell, etc:

   (최초 실행인 경우만) 다음 코드를 터미널이나 파워쉘 등에서 실행하여, 필요한 라이브러리를 설치하세요.

    ```bash
    pip install -r requirements.txt
    ```

2. Place your code under `/agents` directory.

    여러분의 코드를 `/agents` 디렉터리 밑에 위치시키세요.

3. Execute the evaluation code, by run the following code on a terminal/powershell:

    다음 코드를 실행하여 평가 코드를 실행하세요.

    ```bash 
    python evaluate.py
    ```

    If you want to print out all computational procedure, then put `--debug` at the end of python call, as follows:

    만약, 모든 계산 과정을 출력해서 보고 싶다면, `--debug`을 파이썬 호출 부분 뒤에 붙여주세요.

    ```bash 
    python evaluate.py --debug
    ```

4. See what's happening.

    어떤 일이 일어나는지를 관찰하세요.

Note: All the codes are tested both on (1) Windows 11 (23H2) with Python 3.9.13 and (2) Ubuntu 22.04 with Python 3.10. Sorry for Mac users, because you may have some unexpected errors.

모든 코드는 윈도우 11 (23H2)와 파이썬 3.9.13 환경과, 우분투 22.04와 파이썬 3.10 환경에서 테스트되었습니다. 예측불가능한 오류가 발생할 수도 있어, 미리 맥 사용자에게 미안하다는 말을 전합니다.