import logging
import os
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import pandas as pd
import scipy.stats
from sklearn.preprocessing import MinMaxScaler

from src.features import entities
from src.data import datasets


# age_gender_xlsx = 'age_gender.xlsx'


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


def generate_households(data_folder: Path, voivodship_folder: Path) -> pd.DataFrame:
    """
    Given a population size and the path to a folder with data, generates households for this population.
    :param data_folder: path to a folder with data
    :param population_size: size of a population; ignored
    :return: a pandas dataframe with households to lodge the population.
    """
    households_ready_xlsx = data_folder / 'households_ready.xlsx'
    if not households_ready_xlsx.is_file():

        # TODO: another idea - treat them as probabilities?
        households = pd.read_excel(str(data_folder / datasets.households_xlsx.file_name),
                                   sheet_name=datasets.households_xlsx.sheet_name)

        households['family1'] = ''
        households['family2'] = ''
        households['family3'] = ''

        masters_age = []
        masters_gender = []

        # household master
        household_by_master = pd.read_excel(str(voivodship_folder / datasets.households_by_master_xlsx.file_name),
                                            sheet_name=datasets.households_by_master_xlsx.sheet_name)

        headcounts = households.household_headcount.unique()
        indices_by_headcount = {
            headcount: household_by_master[household_by_master.Headcount == headcount].index.tolist() for headcount in headcounts
        }
        proba_by_headcount = {
            headcount: household_by_master.iloc[indices]['Probability within headcount'] for headcount, indices in indices_by_headcount.items()
        }

        # family structure
        families_and_children_df = pd.read_excel(str(data_folder / datasets.families_and_childer_xlsx.file_name),
                                                 sheet_name=datasets.families_and_childer_xlsx.sheet_name)

        for idx, household in households.iterrows():
            # household master
            indices = indices_by_headcount[household.household_headcount]
            proba = proba_by_headcount[household.household_headcount]
            index = np.random.choice(indices, p=proba)
            masters_age.append(household_by_master.iloc[index].Age)
            masters_gender.append(entities.gender_from_string(household_by_master.iloc[index].Gender).value)

            # family structure
            for family_nb in range(1, household.family_type+1):
                df_fc = families_and_children_df.loc[families_and_children_df.nb_of_people == household.household_headcount]
                try:
                    final_structure_idx = np.random.choice(df_fc.index.to_list(),
                                                           p=df_fc.prob_with_young_adults_per_headcount)
                    households.loc[idx, f'family{family_nb}'] = df_fc.loc[final_structure_idx, 'structure']
                except ValueError:
                    pass

        households['master_age'] = masters_age
        households['master_gender'] = masters_gender
        households.to_excel(str(households_ready_xlsx))
    else:
        households = pd.read_excel(str(households_ready_xlsx))
    return households


def __age_gender_population(age_gender_df: pd.DataFrame) -> pd.DataFrame:
    ages = []
    genders = []
    for idx, row in age_gender_df.iterrows():
        ages.extend([row.Age] * row.Total)
        genders.extend([entities.Gender.MALE.value] * row.Males)
        genders.extend([entities.Gender.FEMALE.value] * row.Females)
    return pd.DataFrame(data={entities.prop_age: ages, entities.prop_gender: genders})


def generate(data_folder: Path, population_size: int = 641607) -> pd.DataFrame:
    """
    Generates a population given the folder with data and the size of this population.
    :param data_folder: folder with data
    :param population_size: size of a population to generate; default is the size of the population of Wrocław
    :return: a pandas dataframe with a population generated from the data in data_folder
    """
    voivodship = data_folder.name[0]
    voivodship_folder = data_folder.parents[0] / voivodship
    # check Jupyter Notebooks for more on this generation

    households = generate_households(data_folder, voivodship_folder)

    # get this age_gender dataframe and sample for each person
    # or ignore population_size and sum up all
    age_gender_df = pd.read_excel(str(data_folder / datasets.age_gender_xlsx.file_name),
                                  sheet_name=datasets.age_gender_xlsx.sheet_name)

    population = __age_gender_population(age_gender_df)
    population[entities.prop_household] = -1
    # population_indices = population.index.tolist()  # probably not needed

    # get indices of households of a specific age, gender
    df23 = households.groupby(by=['master_age', 'master_gender'], sort=False).size()\
        .reset_index().rename(columns={0: 'total'})

    # given a household and its master's age and gender
    # select a person
    # set index of a person onto a household
    # set index of a household onto a person
    for idx, df23_row in df23.iterrows():
        if df23_row.master_age == '19 lat i mniej':
            subpopulation = population[population[entities.prop_age].isin((18, 19))
                                   & (population[entities.prop_gender] == df23_row['master_gender'])].index.tolist()
        elif df23_row.master_age == '20-24':
            subpopulation = population[population[entities.prop_age].isin((20, 21, 22, 23, 24))
                                       & (population[entities.prop_gender] == df23_row['master_gender'])].index.tolist()
        elif df23_row.master_age == '25-29':
            subpopulation = population[population[entities.prop_age].isin((25, 26, 27, 28, 29))
                                       & (population[entities.prop_gender] == df23_row['master_gender'])].index.tolist()
        else:
            subpopulation = population[(population[entities.prop_age] == df23_row['master_age'])
                                       & (population[entities.prop_gender] == df23_row['master_gender'])].index.tolist()
        households_indices = households[(households.master_age == df23_row.master_age) &
                                        (households.master_gender == df23_row.master_gender)].index.tolist()
        try:
            masters_indices = np.random.choice(subpopulation, replace=False, size=df23_row.total)
        except ValueError as e:
            if str(e) == 'Cannot take a larger sample than population when \'replace=False\'':
                masters_indices = subpopulation
                households_indices = np.random.choice(households_indices, replace=False, size=len(masters_indices))
        population.loc[masters_indices, entities.prop_household] = households_indices
        households.loc[households_indices, 'house_master'] = masters_indices

    # at this point 1-person households are done
    # the remaining ones as follows:
    # for each family-household we know families' structures
    # which family does the master belong to? that depends on the relationship with the master within a household

    # social competence based on previous findings, probably to be changed
    population[entities.prop_social_competence] = generate_social_competence(len(population.index))

    # TODO: save households (house master index)
    return population


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]
    data_folder = project_dir / 'data' / 'processed' / 'poland' / 'DW'

    generate(data_folder).to_excel('population.xlsx')
