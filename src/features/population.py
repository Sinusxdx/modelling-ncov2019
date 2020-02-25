from typing import List, Callable, Dict, Tuple, Any
import pandas as pd
import os
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import scipy.stats
from src.features import entities


age_gender_xlsx = 'age_gender.xlsx'


def get_distribution(distribution):
    if isinstance(distribution, str):
        return getattr(scipy.stats, distribution)
    raise ValueError(f'Expected the name of a distribution, but got {distribution}')


def sample_from_distribution(sample_size, distribution_name, loc, scale=None):
    distribution = get_distribution(distribution_name)
    if distribution.name in scipy.stats._discrete_distns._distn_names:
        return distribution.rvs(size=sample_size, loc=loc)
    elif distribution.name in scipy.stats._continuous_distns._distn_names:
        return distribution.rvs(size=sample_size, loc=loc, scale=scale)
    raise ValueError(f'Distribution {distribution_name} is neither in continuous nor in discrete distributions')


def generate_social_competence(sample_size, distribution_name='norm', loc=0, scale=1):
    """
    After [1] social competence (introversion and extraversion) are modelled according to a normal distribution with
    mean shown by the majority of the population.
    [1]  B.Zawadzki, J.Strelau, P.Szczepaniak, M.Śliwińska: Inwentarz osobowości NEO-FFI Costy i McCrae.
    Warszawa: Pracownia Testów Psychologicznych Polskiego Towarzystwa Psychologicznego, 1997. ISBN 83-85512-89-6.

    :param sample_size: size of a sample
    :param distribution_name: name of a distribution
    :param args: parameters of the distribution
    :return: social competence vector of a population
    """
    x = sample_from_distribution(sample_size, distribution_name, loc, scale)
    return MinMaxScaler().fit_transform(x.reshape(-1, 1))


def nodes_to_dataframe(nodes: List[entities.Node]) -> Dict[str, List]:
    return pd.DataFrame(data=list_of_dicts_to_dict_of_lists(nodes))


def list_of_dicts_to_dict_of_lists(list_of_dicts: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    return {k: [dic[k] for dic in list_of_dicts] for k in list_of_dicts[0]}


def generate(data_folder, population_size) -> pd.DataFrame:
    """
    :return: an dataframe with population generated from data in data_folder
    """
    voivodship = os.path.basename(data_folder)[0]
    voivodship_folder = os.path.join(data_folder, os.pardir, voivodship)
    # check Jupyter Notebooks for more on this generation

    pass







