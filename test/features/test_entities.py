import networkx as nx
from src.features import entities
from unittest import TestCase


class TestNodes(TestCase):
    def setUp(self):
        self.G = nx.Graph()

    def test_add_node_with_idx(self):
        idx = 1
        node = entities.Node(idx)
        entities.add_node(self.G, node)

        self.assertEqual(1, len(self.G.nodes()))
        self.assertIn(idx, self.G.nodes())

    def test_update_gender(self):
        idx = 1
        node = entities.Node(idx)
        entities.add_node(self.G, node)

        self.assertEqual(entities.Gender.NOT_SET.value, self.G.nodes[idx]['data'].gender)

        self.G.nodes[idx]['data'].gender = entities.Gender.MALE
        self.assertEqual(entities.Gender.MALE.value, self.G.nodes[idx]['data'].gender)

    def test_update_is_by_reference(self):
        idx = 1
        node = entities.Node(idx)
        entities.add_node(self.G, node)

        self.assertEqual(entities.Gender.NOT_SET.value, self.G.nodes[idx]['data'].gender)

        node.gender = entities.Gender.MALE
        self.assertEqual(entities.Gender.MALE.value, self.G.nodes[idx]['data'].gender)


