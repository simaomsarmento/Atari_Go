infinity = 9999


class Group:
    """
    This class stores the necessary values for the group identification, namely:

        - 'elements' - list of (i,j) elements in the group
        - 'liberties' - set of (i,j) liberties of the group
        - 'n_liberties' - number of liberties of the group

    """
    def __init__(self, initial_element):
        """
        :param initial_element: tuple with point coordinates
        """
        self.elements = [initial_element]
        self.liberties = set()
        self.n_liberties = 0

    def __copy__(self):
        """
        Copies a group object info

        :return: group object
        """
        new_group = Group(None)

        new_group.elements = self.elements.copy()
        new_group.liberties = self.liberties.copy()
        new_group.n_liberties = self.n_liberties

        return new_group

    def add_element(self, element):
        """
        Adds a list of elements (list of tuples) to the group.

        :param: element - element to add to the group
        """
        self.elements.extend(element)

    def add_liberty(self, liberty):
        """
        Tries to add a liberty. If size changes, it means
        liberty was not yet on the set and therefore number
        of liberties must be incremented, since liberty was
        added.

        :param: liberty - liberty to be added as a tuple
        """
        previous_len = len(self.liberties)
        self.liberties.add(liberty)  # only adds to the set if the element is not present already
        updated_len = len(self.liberties)

        if previous_len < updated_len:
            self.n_liberties += 1

    def remove_liberty(self, row, col):
        """
        Removes a liberty from the group

        :param: row - row of liberty to remove
        :param: col - col of liberty to remove
        """
        try:
            self.liberties.remove((row, col))
            self.n_liberties -= 1
        except:
            pass

    def add_liberties(self, row, col, board):
        """
        This function calculates the liberties for the given point,
        and updates the corresponding group information regarding so.

        :param row: row point position
        :param col: col point position
        :param board: matrix with board pieces
        """

        # check all 4 neighbors. If the neighbor is empty (= 0) it's a liberty

        if row - 1 >= 0:
            if board[row - 1][col] == 0:
                self.add_liberty((row - 1, col))
        if row + 1 < len(board):
            if board[row + 1][col] == 0:
                self.add_liberty((row + 1, col))
        if col - 1 >= 0:
            if board[row][col - 1] == 0:
                self.add_liberty((row, col - 1))
        if col + 1 < len(board):
            if board[row][col + 1] == 0:
                self.add_liberty((row, col + 1))

    def merge_groups(self, player, groups, left_neighbor_group):
        """
        This function is responsible for merging two connected groups initially
        identified as separated components.

        :param player: next player to move
        :param groups: dictionary with groups' information
        :param left_neighbor_group: group to merge
        :return board elements to update on the board
        """

        # 1) merge elements
        elements_to_merge = groups[player][left_neighbor_group].elements
        self.add_element(elements_to_merge)

        # 2) merge liberties (liberties count is updated internally)
        liberties_to_merge = groups[player][left_neighbor_group].liberties
        for liberty in liberties_to_merge:
            self.add_liberty(liberty)

        return elements_to_merge


class State:
    """
    This class stores the necessary values for the state definition

    - player - defines next player to move
    - size - defines the size of the board
    - draw - this variable plays a flag role. Takes the values:
            -1: if terminal test was not yet evaluated
            0: if terminal test was evaluated, but no draw exists
            1: if terminal test was evaluated, and a draw was found
            By storing this information, we can avoid recomputing a terminal test
            that has already been computed in an earlier stage, saving time.
    - group_board - displays the board with the component's groups
    - groups - dictionary with group labels as keys and the corresponding Group
               object associated as the value.
    - counters - dictionary with group counter for player 1 and player 2

    Note:
    1) players' counters are necessary when adding more groups, to avoid overwritting
    groups already existing
    2) To access group N structure or counter, just use N as key. (e.g: groups[player][N] returns
    group N structure for player 1)
    3) to make it more intuitive, groups for player 1 are odd, whereas groups for player 2 are even
    """

    def __init__(self, player, size, initial_board, copy=False):
        self.player = player
        self.draw = -1
        self.size = size
        self.group_board = None
        self.groups = None
        self.counters = None

        if not copy:
            group_board, player_groups, player_counters = self.initialize_groups(initial_board)
            self.group_board = group_board
            self.groups = player_groups
            self.counters = player_counters

    def __copy__(self):
        """
        Copies a state object

        :return: a new State object
        """
        new_state = State(self.player, self.size, None, copy=True)

        new_state.group_board = [row.copy() for row in self.group_board]
        new_state.counters = {1: self.counters[1], 2: self.counters[2]}

        new_groups = dict({1: dict(), 2: dict()})
        for player in [1,2]:
            for k, v in self.groups[player].items():
                new_groups[player][k] = v.__copy__()
        new_state.groups = new_groups

        return new_state

    def initialize_groups(self, initial_board):
        """
        This function receives the initial board and returns the state parameters

        :param initial_board: initial board configuration read from file
        :return: group_board: board with component labels
                 player_groups: dict with groups for each player
                 player_counters: key counter for each player
        """

        """
        Component identification goes as follows:
        1) Look for a group neighbor on the row above. If existent, join group.
        2) Look for a group neighbor on the col on the left. If existent:
            2.1) If neighbor was found both on top and left, then merge left group
                 w/ top group
            2.2) If only left neighbor was found, then join current point to left
                 group.
        3) If no neighbor was found (same player piece in any of the neighboring points)
           then a new group is created
        """

        # a matrix containing the number of the group each point belongs to or 0 (for empty)
        group_board = [[0] * len(initial_board) for i in range(len(initial_board))]
        # the groups for player 1 and for player 2
        groups = {1: dict(), 2: dict()}
        # counter for the group names. player 1: odd numbers; player 2: even numbers
        counters = {1: 1, 2: 2}

        for row in range(len(initial_board)):
            for col in range(len(initial_board)):

                player = initial_board[row][col]

                # Check if current point is occupied. If not, it just skips to next point
                if initial_board[row][col] != 0:

                    if row - 1 >= 0:
                        top_neighbor = initial_board[row - 1][col]
                        top_neighbor_group = group_board[row - 1][col]

                        if top_neighbor_group != 0 and top_neighbor == player:
                            # updates group board
                            group_board[row][col] = top_neighbor_group
                            # adds element to group structure
                            new_elements = [(row, col)]
                            groups[player][group_board[row][col]].add_element(new_elements)

                    if col - 1 >= 0:
                        left_neighbor = initial_board[row][col - 1]
                        left_neighbor_group = group_board[row][col - 1]

                        if left_neighbor_group != 0 and left_neighbor == player:
                            # verifies if groups must be merged (condition 2.1)
                            # by checking group_board[row][col] != 0, we ensure a group has been
                            # attributed before
                            if group_board[row][col] != 0 and left_neighbor_group != group_board[row][col]:
                                # updates left neighbor's group elements
                                group = group_board[row][col]
                                elements_to_merge = groups[player][group].merge_groups(player, groups, left_neighbor_group)

                                # removes old group from dictionary
                                groups[player].pop(left_neighbor_group)
                                # updates group board
                                for old_element_row, old_element_col in elements_to_merge:
                                    group_board[old_element_row][old_element_col] = group_board[row][col]

                            # no neighbor on top, just join left neighbor's group (condition 2.2)
                            elif group_board[row][col] == 0:
                                # updates group board
                                group_board[row][col] = left_neighbor_group
                                # adds element to group structure
                                new_elements = [(row, col)]
                                groups[player][group_board[row][col]].add_element(new_elements)

                    # if no merging neighbors were found, than just creates a new group
                    if group_board[row][col] == 0:
                        group_board[row][col] = counters[player]
                        groups[player][counters[player]] = Group((row, col))
                        counters[player] += 2

                    # Finally, add information about group's liberties to the structure
                    group = group_board[row][col]
                    groups[player][group].add_liberties(row, col, initial_board)

        return group_board, groups, counters

    def update_state(self, a):
        """
        This function updates the state representation after a change in the state

        :param: a - tuple (player, x, y) with action to perform
        """
        # Next player
        self.update_player()

        # Reset draw
        self.draw = False

        # Update group board and groups
        self.update_groups(a)

    def update_player(self):
        """
        Update info about next player to move.
        Since players are either 1 or 2, we can
        simply subtract 3 - player
        """
        self.player = 3 - self.player

    def find_neighboring_groups(self, group_list, neighbor_pos, my_pos, player):
        """
        This function finds the neighboring groups, and updates
        their liberties

        :param group_list: set with groups to be merged
        :param neighbor_pos: position of neighbor
        :param my_pos: current move position
        :param player: color to play
        :return updated set of groups to merge
        """

        group = self.group_board[neighbor_pos[0]][neighbor_pos[1]]
        if group != 0:  # Found a group
            neighbor_player = self.get_group_player(group)
            # removes liberty corresponding to current point
            self.groups[neighbor_player][group].remove_liberty(my_pos[0], my_pos[1])
            # if same group, adds to group list
            if neighbor_player == player:
                group_list.add(group)

        return group_list

    def update_groups(self, move):
        """
        Function responsible for updating the state after
        having played a certain move.

        :param move: action played as an action tuple (p, i, j)
        :return: updated state
        """
        player = move[0]

        row = move[1]
        col = move[2]
        new_element = [(row, col)]

        wanted_group_list = set()

        # Check if there groups nearby

        # Look up for same player groups
        if row - 1 >= 0:
            wanted_group_list = self.find_neighboring_groups(wanted_group_list, (row - 1, col), new_element[0], player)
        # Look down
        if row + 1 < self.size:
            wanted_group_list = self.find_neighboring_groups(wanted_group_list, (row + 1, col), new_element[0],player)
        # Look right
        if col + 1 < self.size:
            wanted_group_list = self.find_neighboring_groups(wanted_group_list, (row, col + 1), new_element[0], player)
        # Look left
        if col - 1 >= 0:
            wanted_group_list = self.find_neighboring_groups(wanted_group_list, (row, col - 1), new_element[0], player)

        if len(wanted_group_list) >= 1:  # Want to join to more than 1 group

            # Insert me in the first group (ordered)
            first_group = wanted_group_list.pop()

            # Update group board accordingly
            self.group_board[row][col] = first_group

            # add element along with its liberties
            self.groups[player][first_group].add_element(new_element)
            self.groups[player][first_group].add_liberties(row, col, self.group_board)

            # Merge all the groups
            for group in wanted_group_list:

                # merges next group to the first
                elements_to_merge = self.groups[player][first_group].merge_groups(player, self.groups, group)

                # removes old group from dictionary
                self.groups[player].pop(group)

                # updates group board
                for old_element_row, old_element_col in elements_to_merge:
                    self.group_board[old_element_row][old_element_col] = self.group_board[row][col]

        elif len(wanted_group_list) == 0:  # Alone
            # Create a new group for myself
            self.groups[player][self.counters[player]] = Group((row, col))
            # Update group board accordingly
            self.group_board[row][col] = self.counters[player]
            # Update counter
            self.counters[player] += 2
            # Add liberties to group
            group = self.group_board[row][col]
            self.groups[player][group].add_liberties(row, col, self.group_board)

    def get_group_player(self, group_number):
        """
        Gives the player for a given group label

        :param group_number: label/group number to identify
        :return: corresponding player
        """
        if group_number % 2 == 0:
            return 2
        else:
            return 1


class Game:
    """
    This class implements the Atari Go game.

    While Go scoring is based on both surrounded territory and captured stones,
    the Atari Go finishes when the first stone is captured. More information on
    Atari Go can be found here:
        https://senseis.xmp.net/?CaptureGo

    This class assumes the following:
        - players: Players are represented with the integers 1 for black and 2 for white
        - actions: Actions are represented as a tuple (p,i,j) where:
                - p ∈ {1, 2} is the player
                - i ∈ {1, . . . , N} is the row
                - j ∈ {1, . . . , N} is the column
                (assuming that (1,1) corresponds to the top left position and the size of the board is N)
        - states:

    Note: A game is similar to a problem, but it has a utility for each
    state and a terminal test instead of a path cost and a goal
    test.
    """

    def to_move(self, s):
        """
        Returns the player to move next given the state s.

        :returns: next player to play
        """
        return s.player

    def terminal_test(self, s):
        """Returns a boolean of whether state s is terminal.

        The procedure is the following:
            - the current player must have at least one liberty on
            all its groups;
            - if the condition above verifies, there still need to
            be a non empty list of possible actions given the state s

        If any of the conditions above is violated the state is terminal.

        The winner is also updated in the state.

        :param: s - state
        :return: terminal_test - boolean for terminal state
        """
        terminal_state = False
        # s.draw = 0 mean that the termina_test has been called (previously s.draw = -1)
        s.draw = 0

        # verifies that no group has 0 liberties
        for player in [1,2]:
            for group in s.groups[player].values():
                if group.n_liberties == 0:
                    terminal_state = True


        # no group was closed, must verify if there's a possible action
        # to play

        if not terminal_state:
            possible_actions = self.actions(s)

            if len(possible_actions) == 0:
                terminal_state = True
                s.draw = 1

        return terminal_state

    def utility(self, s, player):
        """
        Returns the payoff of state s if it is terminal (1 if p wins, -1
        if p loses, 0 in case of a draw), otherwise, its evaluation with respect
        to player p.
        To calculate the evaluation it uses the alpha beta cut
        off search, described further below

        Note the following:
            s.player - is the player that is going to play this round
            player - is the player being evaluated

        :param: s - state
        :param: player - player for which utility is being calculated
        :returns: utility score , belong to the interval [-1,1]
        """

        if s.draw == -1:  # terminal test not yet run
            self.terminal_test(s)
        if s.draw == 1:
            return 0

        # calculate liberties of group with less liberties
        own_min = infinity
        own_liberties = 0
        for group in s.groups[player].values():
            own_liberties += group.n_liberties
            if group.n_liberties < own_min:
                own_min = group.n_liberties

        other_min = infinity
        other_liberties = 0
        for group in s.groups[3-player].values():
            other_liberties += group.n_liberties
            if group.n_liberties < other_min:
                other_min = group.n_liberties

        # verifies suicidal kill
        if other_min == 0 and own_min == 0:
            if s.player != player:
                return 1
            else:
                return -1

        # regular win
        if other_min == 0:
            return 1
        # regular death
        if own_min == 0:
            return -1

        #return (lambda * (own_min/(own_min+other_min)) + (1-lambda)* ((own_min-other_min)/(own_min+other_min)))
        return ((own_min-other_min)/(own_min+other_min))

    def actions(self, s):
        """
        Returns a list of valid moves at state s.

        Because we use 0 based board indexation in our implementation and the API states that 1 based
        indexation should be used, we have so add one from each coordinate when an action is returned

        :param: s - state
        :returns: list of actions available for state s
        """

        actions = list()

        for row in range(s.size):
            for col in range(s.size):

                if s.group_board[row][col] == 0:
                    if row - 1 >= 0:
                        if self.not_suicide(s, row-1, col):
                            actions.append((s.player, row + 1, col + 1))
                            continue

                    if row + 1 < s.size:
                        if self.not_suicide(s, row + 1, col):
                            actions.append((s.player, row + 1, col + 1))
                            continue

                    if col - 1 >= 0:
                        if self.not_suicide(s, row, col - 1):
                            actions.append((s.player, row + 1, col + 1))
                            continue

                    if col + 1 < s.size:
                        if self.not_suicide(s, row, col + 1):
                            actions.append((s.player, row + 1, col + 1))
                            continue

        return actions

    def not_suicide(self, s, row, col):
        """
        This function verifies the piece played at (row,col)
        given the state s is not a suicide

        :param s -  state
        :param row - row in the board
        :param col - col in the board
        :return: boolean - it is or it isn't suicide
        """

        group = s.group_board[row][col]

        if group == 0:
            return True

        player = s.get_group_player(group)
        group_liberties = s.groups[player][group].n_liberties

        if player == s.player and group_liberties > 1:
            return True

        if player != s.player and group_liberties == 1:
            return True

        return False

    def result(self, s, a):
        """
        Return the state that results from making action a from state s.

        Because we use 0 based board indexation in our implementation and the API states that 1 based
        indexation should be used, we have so subtract one from each coordinate when an action is received

        Generates next state (allocates new memory).

        :param: s - state
        :param: a - action tuple
        :returns next state
        """
        a = (a[0], a[1]-1, a[2]-1)

        # Initialize successor state
        successor_s = s.__copy__()
        
        # Assuming that action a is a valid action (verified before), next state is updated accordingly
        successor_s.update_state(a)
        
        return successor_s

    def load_board(self, file):
        """
        Loads a board from an opened file and returns the corresponding state

        :returns: corresponding state
        """

        # 1. First line should contain:
        #   - size of board
        #   - next player to move
        line1 = file.readline()
        size, player = map(int, line1.split(' '))

        # 2. Load board into matrix
        board = []
        for row in range(size):
            board_row = file.readline().split('\n')[0]
            board.append([int(point) for point in board_row])

        # 3. Initialize state
        s = State(player, size, initial_board=board)

        return s