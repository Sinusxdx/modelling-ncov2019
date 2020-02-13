from unittest import TestCase
from src.features import population
import numpy as np
import random


class TestPopulationGeneration(TestCase):
    def test_generation_without_decorators(self):
        n = 10
        graph = population.generate(n, [])
        self.assertIsNotNone(graph)
        self.assertEqual(n, len(graph.nodes))

    def test_generation_with_decorators(self):
        def function1(node):
            node[1]['field1'] = random.randint(1, 10)
            return node

        def function2(node: population.Node_Type, arg1):
            node[1]['field2'] = arg1
            return node

        def function3(node, arg2, arg3):
            node[1]['field3'] = arg3(node[1]['field2'], arg2)
            return node

        n = 10
        decorators = [(function1, ()), (function2, (2,)), (function3, (7, np.power))]
        graph = population.generate(n, decorators)

        self.assertIsNotNone(graph)
        for node_id, node_dict in graph.nodes(data=True):
            self.assertIn('field1', node_dict)
            self.assertEqual(node_dict['field2'], 2)
            self.assertEqual(node_dict['field3'], 128)
