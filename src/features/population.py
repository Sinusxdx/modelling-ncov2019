from typing import List, Callable, Dict, Tuple, Any
import pandas as pd
import os


def generate(data_folder) -> pd.DataFrame:
    """
    :return: an dataframe with population generated from data in data_folder
    """
    voivodship = os.path.basename(data_folder)[0]
    voivodship_folder = os.path.join(data_folder, os.pardir, voivodship)
    pass




