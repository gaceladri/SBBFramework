import unittest
from pSBB.SBB.config import Config
from pSBB.SBB.sbb import SBB

TEST_CONFIG = {
    'task': 'classification',
    'classification_parameters': { # only used if 'task' is 'classification'
        'dataset': 'iris', # must have a .train and a .test file in the pSBB/datasets folder
    },
    'training_parameters': {
        'runs_total': 3,
        'generations_total': 30,
        'validate_after_each_generation': 30,
        'populations': {
            'programs': 40,
            'teams': 20,
            'points': 40,
        },
        'replacement_rate': {
            'teams': 0.8,
            'points': 0.2,
        },
        'mutation': {
            'team': {
                'remove_program': 0.7,
                'add_program': 0.8,
            },
            'program': {
                'remove_instruction': 0.7,
                'add_instruction': 0.8,
                'change_instruction': 0.8,
                'swap_instructions': 0.8,
                'change_action': 0.1,
            },
        },
        'team_size': { # the min size is the total number of actions
            'min': 2,
            'max': 5,
        },
        'program_size': {
            'min': 2,
            'max': 20,
        },
    },

    'advanced_training_parameters': {
        'seed': 1, # default = None
        'use_pareto_for_team_population_selection': False, # if False, will select solutions by best fitness
        'use_pareto_for_point_population_selection': False, # if False, will select points using uniform probability
        'use_operations': ['+', '-', '*', '/', 'ln', 'exp', 'cos', 'if_lesser_than', 'if_equal_or_higher_than'],
        'extra_registers': 1,
        'diversity': {
            'genotype_fitness_maintanance': False,
            'fitness_sharing': False,
        },
        'diversity_configs': { # p_value is with how much strenght this diversity metric will be applied to the fitness
            'genotype_fitness_maintanance': {
                'p_value': 0.1,
                'k': 8,
            },
            'fitness_sharing': {
                'p_value': 0.1,
            },       
        },
    },
}

class ClassificationTests(unittest.TestCase):
    def setUp(self):
        Config.RESTRICTIONS['write_output_files'] = False

    def test_classification_for_iris_without_pareto_and_without_diversity_maintenance(self):
        """ Checking if everything for classification is still working and producing the same result. """
        config = dict(TEST_CONFIG)
        config['advanced_training_parameters']['use_pareto_for_team_population_selection'] = False
        config['advanced_training_parameters']['use_pareto_for_point_population_selection'] = False
        config['advanced_training_parameters']['diversity']['genotype_fitness_maintanance'] = False
        config['advanced_training_parameters']['diversity']['fitness_sharing'] = False
        Config.USER = config
        sbb = SBB()
        sbb.run()
        result = sbb.best_scores_per_runs_
        expected = [0.7, 0.83333, 0.63333]
        self.assertEqual(expected, result)

    def test_classification_for_iris_without_pareto_and_with_diversity_maintenance(self):
        """ Checking if everything for classification is still working and producing the same result. """
        config = dict(TEST_CONFIG)
        config['advanced_training_parameters']['use_pareto_for_team_population_selection'] = False
        config['advanced_training_parameters']['use_pareto_for_point_population_selection'] = False
        config['advanced_training_parameters']['diversity']['genotype_fitness_maintanance'] = True
        config['advanced_training_parameters']['diversity']['fitness_sharing'] = True
        Config.USER = config
        sbb = SBB()
        sbb.run()
        result = sbb.best_scores_per_runs_
        expected = [0.7, 0.93333, 0.86666]
        self.assertEqual(expected, result)

    def test_classification_for_iris_with_pareto_and_without_diversity_maintenance(self):
        """ Checking if everything for classification is still working and producing the same result. """
        config = dict(TEST_CONFIG)
        config['advanced_training_parameters']['use_pareto_for_team_population_selection'] = True
        config['advanced_training_parameters']['use_pareto_for_point_population_selection'] = True
        config['advanced_training_parameters']['diversity']['genotype_fitness_maintanance'] = False
        config['advanced_training_parameters']['diversity']['fitness_sharing'] = False
        Config.USER = config
        sbb = SBB()
        sbb.run()
        result = sbb.best_scores_per_runs_
        expected = [0.9, 1.0, 0.66666]
        self.assertEqual(expected, result)

    def test_classification_for_iris_with_pareto_for_teams_without_pareto_for_points(self):
        """ Checking if everything for classification is still working and producing the same result. """
        config = dict(TEST_CONFIG)
        config['advanced_training_parameters']['use_pareto_for_team_population_selection'] = True
        config['advanced_training_parameters']['use_pareto_for_point_population_selection'] = False
        config['advanced_training_parameters']['diversity']['genotype_fitness_maintanance'] = False
        config['advanced_training_parameters']['diversity']['fitness_sharing'] = False
        Config.USER = config
        sbb = SBB()
        sbb.run()
        result = sbb.best_scores_per_runs_
        expected = [0.66666, 0.96666, 0.86666]
        self.assertEqual(expected, result)

    def test_classification_for_thyroid(self):
        """ Checking if everything for classification is still working and producing the same result. """
        config = dict(TEST_CONFIG)
        config['advanced_training_parameters']['use_pareto_for_team_population_selection'] = False
        config['advanced_training_parameters']['use_pareto_for_point_population_selection'] = False
        config['advanced_training_parameters']['diversity']['genotype_fitness_maintanance'] = False
        config['advanced_training_parameters']['diversity']['fitness_sharing'] = False
        config['classification_parameters']['dataset'] = 'thyroid'
        config['training_parameters']['runs_total'] = 2
        Config.USER = config
        sbb = SBB()
        sbb.run()
        result = sbb.best_scores_per_runs_
        expected = [0.64715, 0.60857]
        self.assertEqual(expected, result)

if __name__ == '__main__':
    unittest.main()