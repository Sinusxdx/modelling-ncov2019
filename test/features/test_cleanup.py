from unittest import TestCase
from pathlib import Path
import pandas as pd
from src.features import cleanup


class TestCleanup(TestCase):
    def test_age_transformation(self):
        df = pd.read_excel(str(Path(__file__).resolve().parents[0] / 'test_cleanup_age_parsing.xlsx'))
        print(cleanup.age_range_to_age(df))

