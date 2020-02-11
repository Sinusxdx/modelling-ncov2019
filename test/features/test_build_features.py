from src.features import build_features
from unittest import TestCase


class TestSamplers(TestCase):

    def test_age_gender_sampler(self):
        age, gender = build_features.sample_age_gender()
        self.assertIsInstance(age, int)
        self.assertGreaterEqual(age, 0)
        self.assertIsInstance(gender, build_features.entities.Gender)
        self.assertNotEqual(gender, build_features.entities.Gender.NOT_SET)
