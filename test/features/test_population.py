from unittest import TestCase
from src.features import population, entities
import scipy.stats
import numpy as np
import pandas as pd


class TestDistributionRetrieval(TestCase):

    def test_should_raise_error_on_unknown_datatype(self):
        try:
            population.get_distribution(1)
            self.fail('Should have raised ValueError')
        except ValueError as e:
            self.assertTrue(str(e).startswith('Expected the name of a distribution'))

    def test_should_raise_error_on_unknown_distribution(self):
        try:
            population.get_distribution('giberish')
            self.fail('Should have raised an error')
        except Exception as e:
            self.assertEqual('module \'scipy.stats\' has no attribute \'giberish\'', str(e))

    def test_should_return_normal_distribution(self):

        distribution = population.get_distribution('norm')
        self.assertIsInstance(distribution, scipy.stats._continuous_distns.norm_gen)


class TestDrawingFromDistribution(TestCase):

    def test_should_draw_10_samples_from_normal_distribution(self):
        sample = population.sample_from_distribution(10, 'norm', 0, 1)
        self.assertEqual(10, len(sample))
        self.assertIsInstance(sample, np.ndarray)


class TestSocialCompatenece(TestCase):

    def test_should_generate_social_competence_vector_between_0_and_1(self):
        size = 10
        result = population.generate_social_competence(size)
        self.assertEqual(size, result.shape[0])
        self.assertEqual(1, result.shape[1])
        for x in result:
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x, 1)


class TestNodesToDataFrame(TestCase):

    def test_should_convert_LD_to_DL(self):
        ld = [dict(a=1, b=2), dict(a=2, b=3)]
        dl = population.list_of_dicts_to_dict_of_lists(ld)

        self.assertEqual(2, len(dl.keys()))
        self.assertIn('a', dl.keys())
        self.assertIn('b', dl.keys())
        self.assertEqual([1, 2], dl['a'])
        self.assertEqual([2, 3], dl['b'])

    def test_should_convert_nodes_to_dataframe(self):
        node1 = entities.Node(age=2, gender=entities.Gender.MALE,
                              employment_status=entities.EmploymentStatus.NOT_EMPLOYED,
                              social_competence=0.3,
                              public_transport_duration=0,
                              public_transport_usage=False,
                              household=1, profession=entities.PROFESSION_NOT_ASSIGNED)
        node2 = entities.Node(age=37, gender=entities.Gender.FEMALE,
                              employment_status=entities.EmploymentStatus.EMPLOYED,
                              social_competence=0.7,
                              public_transport_duration=30,
                              public_transport_usage=True,
                              household=1, profession=7)
        nodes = [node1, node2]

        df = population.nodes_to_dataframe(nodes)

        columns = [entities.prop_age, entities.prop_gender, entities.prop_employment_status,
                   entities.prop_social_competence, entities.prop_public_transport_usage,
                   entities.prop_public_transport_duration, entities.prop_household, entities.prop_profession]
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(columns), len(df.columns))
        self.assertEqual(2, len(df.index))
        self.assertEqual(columns, df.columns.tolist())

        self.assertNodeAndRowEqual(node1, df.iloc[0])
        self.assertNodeAndRowEqual(node2, df.iloc[1])

    def assertNodeAndRowEqual(self, node, row):
        self.assertEqual(node.age, row[entities.prop_age])
        self.assertEqual(node.gender, row[entities.prop_gender])
        self.assertEqual(node.employment_status, row[entities.prop_employment_status])
        self.assertEqual(node.social_competence, row[entities.prop_social_competence])
        self.assertEqual(node.public_transport_usage, row[entities.prop_public_transport_usage])
        self.assertEqual(node.public_transport_duration, row[entities.prop_public_transport_duration])
        self.assertEqual(node.household, row[entities.prop_household])
        self.assertEqual(node.profession, row[entities.prop_profession])


