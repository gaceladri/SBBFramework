import sys
import errno
import socket
import time
from socket import error as socket_error
import os
import subprocess
import threading
import random
import numpy
from match_state import MatchState
from poker_match import PokerMatch
from poker_opponents import PokerRandomOpponent, PokerAlwaysFoldOpponent, PokerAlwaysCallOpponent, PokerAlwaysRaiseOpponent
from ..reinforcement_environment import ReinforcementEnvironment, ReinforcementPoint
from ...config import Config

class OpponentModel():
    """
    ATTENTION: If you change the order, add or remove inputs the SBB teams that were already trained will 
    behave unexpectedly!

    All inputs are normalized, so they influence the SBB player potentially equal,

    inputs[0] = self shot-term agressiveness (last 10 hands)
    inputs[1] = self long-term agressiveness
    inputs[2] = opponent shot-term agressiveness (last 10 hands)
    inputs[3] = opponent long-term agressiveness
    reference: "Countering Evolutionary Forgetting in No-Limit Texas Hold'em Poker Agents"
    """

    INPUTS = ['self short-term agressiveness', 'self long-term agressiveness', 'opponent short-term agressiveness', 
        'opponent long-term agressiveness']

    def __init__(self):
        self.self_agressiveness = []
        self.opponent_agressiveness = []

    def update_agressiveness(self, self_actions, opponent_actions, self_folded, opponent_folded, previous_action):
        if self_folded:
            if self_actions:
                if self_actions[-1] != 'f':
                    self_actions.append('f')
            else:
                self_actions.append('f')
        if opponent_folded:
            if opponent_actions:
                if opponent_actions[-1] != 'f':
                    opponent_actions.append('f')
            else:
                opponent_actions.append('f')
            if previous_action:
                self_actions.append(previous_action)
        if len(self_actions) > 0:
            self.self_agressiveness.append(self._calculate_points(self_actions)/float(len(self_actions)))
        if len(opponent_actions) > 0:
            self.opponent_agressiveness.append(self._calculate_points(opponent_actions)/float(len(opponent_actions)))

    def _calculate_points(self, actions):
        points = 0.0
        for action in actions:
            if action == 'c':
                points += 0.5
            if action == 'r':
                points += 1.0
        return points

    def inputs(self):
        inputs = [0] * len(OpponentModel.INPUTS)
        if len(self.self_agressiveness) > 0:
            inputs[0] = numpy.mean(self.self_agressiveness[:10])
            inputs[1] = numpy.mean(self.self_agressiveness)
        if len(self.opponent_agressiveness) > 0:
            inputs[2] = numpy.mean(self.opponent_agressiveness[:10])
            inputs[3] = numpy.mean(self.opponent_agressiveness)
        return inputs

class PokerPoint(ReinforcementPoint):
    """
    Encapsulates a poker opponent as a point.
    """

    def __init__(self, point_id, opponent):
        super(PokerPoint, self).__init__(point_id, opponent)
        self.seed_ = random.randint(0, Config.RESTRICTIONS['max_seed'])

class PokerEnvironment(ReinforcementEnvironment):
    """
    This environment encapsulates all methods to deal with a reinforcement learning task for TicTacToe.
    """

    ACTION_MAPPING = {0: 'f', 1: 'c', 2: 'r'}
    INPUTS = ['chips']+MatchState.INPUTS+OpponentModel.INPUTS

    def __init__(self):
        total_actions = 3 # fold, call, raise
        total_inputs = len(PokerEnvironment.INPUTS)
        coded_opponents = [PokerRandomOpponent, PokerAlwaysFoldOpponent, PokerAlwaysCallOpponent, PokerAlwaysRaiseOpponent]
        super(PokerEnvironment, self).__init__(total_actions, total_inputs, coded_opponents)
        self.total_positions_ = 2

    def instantiate_point_for_coded_opponent_class(self, opponent_class):
        instance = opponent_class()
        return PokerPoint(str(instance), instance)

    def instantiate_point_for_sbb_opponent(self, team):
        return PokerPoint(team.__repr__(), team)

    def play_match(self, team, point, is_training):
        """

        """
        # TODO temp, for debug
        team = PokerAlwaysRaiseOpponent()
        team.opponent_id = "team"
        point = self.instantiate_point_for_coded_opponent_class(PokerAlwaysRaiseOpponent)
        point.opponent.opponent_id = "opponent"
        team.seed_ = 2363931385
        point.opponent.seed_ = 1550424471
        point.seed_ = 3660868348
        print str(team.seed_ )
        print str(point.opponent.seed_)
        print str(point.seed_)
        #

        if Config.USER['reinforcement_parameters']['debug_matches'] and not os.path.exists(Config.RESTRICTIONS['poker']['acpc_path']+"outputs/"):
            os.makedirs(Config.RESTRICTIONS['poker']['acpc_path']+"outputs/")

        t1 = threading.Thread(target=PokerEnvironment.execute_player, args=[team, Config.RESTRICTIONS['poker']['available_ports'][0], point.point_id, is_training])
        t2 = threading.Thread(target=PokerEnvironment.execute_player, args=[point.opponent, Config.RESTRICTIONS['poker']['available_ports'][1], point.point_id, False])
        p = subprocess.Popen([
                                Config.RESTRICTIONS['poker']['acpc_path']+'dealer', 
                                Config.RESTRICTIONS['poker']['acpc_path']+'outputs/match_output', 
                                Config.RESTRICTIONS['poker']['acpc_path']+'holdem.limit.2p.reverse_blinds.game', 
                                str(Config.USER['reinforcement_parameters']['poker']['total_hands']), 
                                str(point.seed_),
                                'sbb', 'opponent', 
                                '-p', str(Config.RESTRICTIONS['poker']['available_ports'][0])+","+str(Config.RESTRICTIONS['poker']['available_ports'][1])
                                # '-l'
                            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        t1.start()
        t2.start()
        out, err = p.communicate()
        t1.join()
        t2.join()

        if Config.USER['reinforcement_parameters']['debug_matches']:
            with open(Config.RESTRICTIONS['poker']['acpc_path']+"outputs/match.log", "w") as text_file:
                text_file.write(str(err))
        score = out.split("\n")[1]
        score = score.replace("SCORE:", "")
        splitted_score = score.split(":")
        scores = splitted_score[0].split("|")
        players = splitted_score[1].split("|")
        if players[0] != 'sbb':
            print "\nbug!\n"
            raise SystemExit
        avg_score = float(scores[0])/float(Config.USER['reinforcement_parameters']['poker']['total_hands'])
        normalized_value = MatchState.normalize_winning(avg_score)
        if Config.USER['reinforcement_parameters']['debug_matches']:
            print "scores: "+str(scores)
            print "players: "+str(players)
            print "avg score: "+str(avg_score)
            print "normalized_value: "+str(normalized_value)
        return normalized_value

    def metrics(self):
        msg = ""
        msg += "\n### Environment Info:"
        msg += "\ntotal inputs: "+str(self.total_inputs_)
        msg += "\ninputs: "+str(PokerEnvironment.INPUTS)
        msg += "\ntotal actions: "+str(self.total_actions_)
        msg += "\nactions mapping: "+str(PokerEnvironment.ACTION_MAPPING)
        msg += "\npositions: "+str(self.total_positions_)
        msg += "\nmatches per opponents (for each position): "+str(self.population_size_)
        return msg

    @staticmethod
    def execute_player(player, port, point_id, is_training):
        socket_tmp = socket.socket()

        total = 10
        attempt = 0
        while True:
            try:
                socket_tmp.connect(("localhost", port))
                break
            except socket_error as e:
                attempt += 1
                if e.errno == errno.ECONNREFUSED:
                    time.sleep(1)
                if attempt > total:
                    raise ValueError(player.opponent_id+" could not connect to port "+str(port))

        if Config.USER['reinforcement_parameters']['debug_matches']:
            debug_file = open(Config.RESTRICTIONS['poker']['acpc_path']+'outputs/player'+str(port)+'.log','w')
        socket_tmp.send("VERSION:2.0.0\r\n")
        last_hand_id = -1
        opponent_model = OpponentModel()
        previous_messages = None
        previous_action = None
        total_chips = 0.0 # Chips (the stacks are infinite, but it may be useful to play more conservative if it is losing a lot)
        while True:
            try:
                message = socket_tmp.recv(1000)
            except socket_error as e:
                if e.errno == errno.ECONNRESET:
                    break
                else:
                    raise e
            if not message:
                break
            message = message.replace("\r\n", "")
            partial_messages = message.split("MATCHSTATE")
            last_message = partial_messages[-1] # only cares about the last message sent (ie. the one where this player should act)
            match_state = MatchState(last_message)
            if match_state.hand_id != last_hand_id:
                player.initialize() # so a probabilistic opponent will always play equal for the same hands and actions
                if last_hand_id != -1:
                    messages = previous_messages + partial_messages
                    for partial_msg in reversed(messages):
                        if partial_msg:
                            partial_match_state = MatchState(partial_msg)
                            if partial_match_state.hand_id == match_state.hand_id-1: # get the last message of the last hand
                                print partial_msg+" : "+str(partial_match_state.calculate_pot())
                                if partial_match_state.is_showdown():
                                    if Config.USER['reinforcement_parameters']['debug_matches']:
                                        debug_file.write("partial_msg: "+str(partial_msg)+", previous_action: "+str(previous_action)+"\n\n")
                                    self_folded = False
                                    opponent_folded = False
                                    winner = partial_match_state.get_winner_of_showdown()
                                    if winner is None:
                                        debug_file.write("showdown, draw\n\n")
                                    else:
                                        if winner == partial_match_state.position:
                                            debug_file.write("showdown, I won\n\n")
                                            total_chips = total_chips + partial_match_state.calculate_pot()
                                        else:
                                            total_chips = total_chips - partial_match_state.calculate_pot()
                                            debug_file.write("showdown, I lost\n\n")
                                else:
                                    if previous_action == 'f':
                                        if Config.USER['reinforcement_parameters']['debug_matches']:
                                            debug_file.write("partial_msg: "+str(partial_msg)+", I folded\n\n")
                                        self_folded = True
                                        opponent_folded = False
                                    else:
                                        if Config.USER['reinforcement_parameters']['debug_matches']:
                                            debug_file.write("partial_msg: "+str(partial_msg)+", opponent folded\n\n")
                                        self_folded = False
                                        opponent_folded = True
                                    # if partial_match_state.is_current_player_to_act() and partial_match_state.is_last_action_a_fold():
                                    #     if Config.USER['reinforcement_parameters']['debug_matches']:
                                    #         debug_file.write("partial_msg: "+str(partial_msg)+", opponent folded (1)\n\n")
                                    #     self_folded = False
                                    #     opponent_folded = True
                                    #     total_chips = total_chips + partial_match_state.calculate_pot()
                                    # elif not partial_match_state.is_current_player_to_act() and partial_match_state.is_last_action_a_fold():
                                    #     if Config.USER['reinforcement_parameters']['debug_matches']:
                                    #         debug_file.write("partial_msg: "+str(partial_msg)+", I folded (1)\n\n")
                                    #     self_folded = True
                                    #     opponent_folded = False
                                    #     total_chips = total_chips - partial_match_state.calculate_pot()
                                    # elif previous_action == 'f':
                                    #     if Config.USER['reinforcement_parameters']['debug_matches']:
                                    #         debug_file.write("partial_msg: "+str(partial_msg)+", I folded (2)\n\n")
                                    #     self_folded = True
                                    #     opponent_folded = False
                                    #     total_chips = total_chips - partial_match_state.calculate_pot()
                                    # else:
                                    #     if Config.USER['reinforcement_parameters']['debug_matches']:
                                    #         debug_file.write("partial_msg: "+str(partial_msg)+", opponent folded (2)\n\n")
                                    #     self_folded = False
                                    #     opponent_folded = True
                                    #     total_chips = total_chips + partial_match_state.calculate_pot()
                                self_actions, opponent_actions = partial_match_state.actions_per_player()
                                opponent_model.update_agressiveness(self_actions, opponent_actions, self_folded, opponent_folded, previous_action)
                                break
                last_hand_id = match_state.hand_id
            previous_messages = partial_messages
            if match_state.is_showdown():
                previous_action = None
                if Config.USER['reinforcement_parameters']['debug_matches']:
                    debug_file.write("showdown\n\n")
            elif match_state.is_current_player_to_act():
                if match_state.is_last_action_a_fold():
                    previous_action = None
                    if Config.USER['reinforcement_parameters']['debug_matches']:
                        debug_file.write("opponent folded\n\n")
                else:
                    if match_state.hand_id == 0:
                        chips = 0.5
                    else:
                        chips = MatchState.normalize_winning(total_chips/float(match_state.hand_id))
                    inputs = [total_chips, chips] + match_state.inputs() + opponent_model.inputs()
                    action = player.execute(point_id, inputs, match_state.valid_actions(), is_training)
                    if action is None:
                        action = "c"
                    else:
                        action = PokerEnvironment.ACTION_MAPPING[action]
                    previous_action = action
                    send_msg = "MATCHSTATE"+last_message+":"+action+"\r\n"
                    try:
                        socket_tmp.send(send_msg)
                    except socket_error as e:
                        if e.errno == errno.ECONNRESET:
                            break
                    if Config.USER['reinforcement_parameters']['debug_matches']:
                        debug_file.write("match_state: "+str(match_state)+"\n\n")
                        debug_file.write("inputs: "+str(inputs)+"\n\n")
                        debug_file.write("send_msg: "+str(send_msg)+"\n\n")
            else:
                if not previous_action == 'f':
                    previous_action = None
                if Config.USER['reinforcement_parameters']['debug_matches']:
                    debug_file.write("nothing to do\n\n")
        socket_tmp.close()
        if Config.USER['reinforcement_parameters']['debug_matches']:
            debug_file.write("The end.\n\n")
            debug_file.close()