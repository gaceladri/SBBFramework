import random
import numpy
from tictactoe_match import TictactoeMatch
from tictactoe_opponents import TictactoeRandomOpponent, TictactoeSmartOpponent
from ..reinforcement_environment import ReinforcementEnvironment
from ..reinforcement_point import ReinforcementPoint
from ....core.diversity_maintenance import DiversityMaintenance
from ....config import Config

class TictactoeEnvironment(ReinforcementEnvironment):
    """
    This environment encapsulates all methods to deal with a reinforcement learning task for TicTacToe.
    """
    def __init__(self):
        total_actions = Config.USER['reinforcement_parameters']['environment_parameters']['actions_total'] # spaces in the board
        total_inputs = Config.USER['reinforcement_parameters']['environment_parameters']['inputs_total'] # spaces in the board (0, 1, 2 as the states, 0: no player, 1: player 1, 2: player 2)
        total_labels = Config.USER['reinforcement_parameters']['environment_parameters']['point_labels_total'] # since no labels are being used, group everything is just one label
        available_opponents = [TictactoeRandomOpponent, TictactoeSmartOpponent]
        t_opponents = []
        for opponent in available_opponents:
            if opponent.OPPONENT_ID in Config.USER['reinforcement_parameters']['environment_parameters']['training_opponents_labels']:
                t_opponents.append(opponent)
        v_opponents = []
        for opponent in available_opponents:
            if opponent.OPPONENT_ID in Config.USER['reinforcement_parameters']['environment_parameters']['validation_opponents_labels']:
                v_opponents.append(opponent)
        point_class = ReinforcementPoint
        super(TictactoeEnvironment, self).__init__(total_actions, total_inputs, total_labels, t_opponents, v_opponents, point_class)
        self.total_positions_ = 2
        self.action_mapping_ = {
            '[0,0]': 0, '[0,1]': 1, '[0,2]': 2,
            '[1,0]': 3, '[1,1]': 4, '[1,2]': 5,
            '[2,0]': 6, '[2,1]': 7, '[2,2]': 8,
        }
        self.actions_ = []

    def _play_match(self, team, opponent, point, mode, match_id):
        """

        """
        if mode == Config.RESTRICTIONS['mode']['training']:
            is_training = True
        else:
            is_training = False
        outputs = []
        for position in range(1, self.total_positions_+1):
            if position == 1:
                first_player = opponent
                is_training_for_first_player = False
                second_player = team
                is_training_for_second_player = is_training
                sbb_player = 2
            else:
                first_player = team
                is_training_for_first_player = is_training
                second_player = opponent
                is_training_for_second_player = False
                sbb_player = 1

            team.encodings_['encoding_custom_info_per_match'].append("<"+str(point.seed_)+"_"+str(position)+">")

            match = TictactoeMatch(player1_label = first_player.__repr__(), 
                player2_label = second_player.__repr__())
            opponent.initialize(point.seed_)
            self.actions_ = []
            while True:
                is_over, result = self._execute_ttt_player(1, first_player, is_training_for_first_player, 
                    sbb_player, point, match)
                if is_over:
                    outputs.append(result)
                    break

                is_over, result = self._execute_ttt_player(2, second_player, is_training_for_second_player, 
                    sbb_player, point, match)
                if is_over:
                    outputs.append(result)
                    break

        return numpy.mean(outputs)

    def _execute_ttt_player(self, player_id, player, is_training, sbb_player, point, match):
        inputs = match.inputs_from_the_point_of_view_of(player_id)
        action = player.execute(point.point_id_, inputs, match.valid_actions(), is_training)
        if action is None:
            action = random.choice(match.valid_actions())
        if is_training:
            self.actions_.append(action)
            player.encodings_['encoding_for_actions_per_match'].append(str(action))
            player.encodings_['encoding_custom_info_per_match'].append(str(action))
        match.perform_action(player_id, action)

        if match.is_over():
            result = match.result_for_player(sbb_player)
            if Config.USER['reinforcement_parameters']['environment_parameters']['weights_per_action']:
                bin_label = DiversityMaintenance.define_bin_for_actions(self.actions_)
                team.encodings_['encoding_for_pattern_of_actions_per_match'].append(bin_label)
            return True, result
        else:
            return False, None