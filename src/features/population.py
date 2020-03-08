import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import pandas as pd
import scipy.stats
from sklearn.preprocessing import MinMaxScaler

from src.features import entities
from src.data import datasets


def get_distribution(distribution):
    if isinstance(distribution, str):
        return getattr(scipy.stats, distribution)
    raise ValueError(f'Expected the name of a distribution, but got {distribution}')


def sample_from_distribution(sample_size, distribution_name, *args, **kwargs):
    distribution = get_distribution(distribution_name)
    if distribution.name in scipy.stats._discrete_distns._distn_names:
        return distribution.rvs(*args, size=sample_size, **kwargs)
    elif distribution.name in scipy.stats._continuous_distns._distn_names:
        return distribution.rvs(*args, size=sample_size, **kwargs)
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
    x = sample_from_distribution(sample_size, distribution_name, loc=loc, scale=scale)
    return MinMaxScaler().fit_transform(x.reshape(-1, 1))


def nodes_to_dataframe(nodes: List[entities.Node]) -> Dict[str, List]:
    return pd.DataFrame(data=list_of_dicts_to_dict_of_lists(nodes))


def list_of_dicts_to_dict_of_lists(list_of_dicts: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    return {k: [dic[k] for dic in list_of_dicts] for k in list_of_dicts[0]}


def narrow_housemasters_by_headcount_and_age_group(household_by_master, household_row):
    """
    Przy wyborze reprezentanta kierowano się następującymi zasadami:
    •   gdy mieszkanie zajmowała tylko jedna osoba, ona była reprezentantem;
    •   gdy  mieszkanie  zajmowali  małżonkowie/partnerzy  z  dziećmi  lub  bez  dzieci,
    reprezentantem należało wybrać jednego z małżonków/partnerów,
    •   gdy mieszkanie zajmował rodzic z dzieckiem/dziećmi, reprezentantem był rodzic;
    •   gdy  mieszkanie  zajmowała  rodzina  trzypokoleniowa  –  należało  wybrać  osobę
    ze średniego pokolenia;
    •   gdy  żaden  z  powyższych  warunków  nie  był  spełniony,  reprezentantem  mogła  zostać
    osoba dorosła mieszkająca w tym mieszkaniu.

    :param household_by_master:
    :param household_row:
    :return:
    """

    elderly = household_row.elderly == 1
    middle = household_row.middle == 1
    young = household_row.young == 1
    masters = household_by_master[household_by_master.Headcount == household_row.household_headcount]

    if elderly and not middle and not young:
        return masters[masters.elderly == 1]
    if not elderly and middle and not young:
        return masters[masters.middle == 1]
    if not elderly and not middle and young:
        return masters[masters.young == 1]

    if not elderly:
        masters = masters[masters.elderly == 0]
    if not middle:
        masters = masters[masters.middle == 0]
    if not young:
        masters = masters[masters.young == 0]

    if household_row.family_type == 0 or household_row.family_type == 3:
        # does it have different probability (given we are restricted on other conditions below?)
        # headcount agreement plus all ages that are present in the household
        # single person households also falls here
        return masters

    if household_row.household_headcount == 2:
        # the only left here are family_type == 1
        # choose the oldest generation
        if elderly:
            return masters[masters.elderly == 1]
        return masters[masters.middle == 1]
        # young only covered at the beginning

    if household_row.household_headcount >= 3 and household_row.family_type == 1:
        # family_type == 1
        if household_row.relationship == 'Bez osób spoza rodziny':  # MFC+, FCC+, MCC+
            if elderly and middle and young:
                # choose middle or elderly - parents are various age?
                return masters[masters.young == 0]
            elif elderly and middle and not young:
                # choose elderly, as the child is middle
                return masters[masters.elderly == 1]
            elif not elderly and middle and young:
                # choose middle
                return masters[masters.middle == 1]
            elif elderly and not middle and young:
                # choose elderly
                return masters[masters.elderly == 1]
        elif household_row.relationship == 'Z innymi osobami':
            # basically any adult
            # MF+O or MC+O or FC+O - other can be any age
            return masters
        else:  # Z krewnymi w linii prostej starszego pokolenia
            if household_row.house_master == 'członek rodziny':
                if elderly and middle:
                    return masters[masters.middle == 1]
                elif (elderly or middle) and young:
                    return masters[masters.young == 1]
            elif household_row.house_master == 'krewny starszego pokolenia':
                if elderly and (middle or young):
                    return masters[masters.elderly == 1]
                elif middle and young:
                    return masters[masters.middle == 1]
            else:  # inna osoba
                return masters

    if household_row.household_headcount >= 4 and household_row.family_type == 2:
        if household_row.relationship == 'Spokrewnione w linii prostej':
            if household_row.house_master == 'członek rodziny młodszego pokolenia ':
                if elderly and middle:
                    return masters[masters.middle == 1]
                elif (elderly or middle) and young:
                    return masters[masters.young == 1]
            elif household_row.house_master == 'członek rodziny starszego pokolenia':
                if elderly and (middle or young):
                    return masters[masters.elderly == 1]
                elif middle and young:
                    return masters[masters.middle == 1]
            else:  # inna osoba
                return masters
        elif household_row.relationship == 'Niespokrewnione w linii prostej':
            return masters

    raise ValueError(f'Couldn\'t find masters for {household_row}')


def _get_family_structure(families_and_children_df, headcount):
    df_fc = families_and_children_df.loc[families_and_children_df.nb_of_people == headcount]
    try:
        final_structure_idx = np.random.choice(df_fc.index.to_list(),
                                               p=df_fc.prob_with_young_adults_per_headcount)
        return df_fc.loc[final_structure_idx, 'structure']
    except ValueError:
        logging.exception(f'Something went wrong for {headcount}')


def generate_households(data_folder: Path, voivodship_folder: Path, output_folder: Path) -> pd.DataFrame:
    """
    Given a population size and the path to a folder with data, generates households for this population.
    :param data_folder: path to a folder with data
    :param voivodship_folder: path to a folder with voivodship data
    :param output_folder: path to a folder where housedhols should be saved
    :return: a pandas dataframe with households to lodge the population.
    """
    households_ready_xlsx = output_folder / datasets.households_xlsx.file_name
    if not households_ready_xlsx.is_file():

        households = pd.read_excel(str(data_folder / datasets.households_xlsx.file_name),
                                   sheet_name=datasets.households_xlsx.sheet_name)

        households['family1'] = ''
        households['family2'] = ''
        households['family3'] = ''

        masters_age = []
        masters_gender = []

        # household master
        # Age	Headcount	Count	Sum in headcount	Probability within headcount	young	middle	elderly
        household_by_master = pd.read_excel(str(voivodship_folder / datasets.households_by_master_xlsx.file_name),
                                            sheet_name=datasets.households_by_master_xlsx.sheet_name)

        # family structure
        # families_and_children_df = pd.read_excel(str(data_folder / datasets.families_and_children_xlsx.file_name),
        #                                         sheet_name=datasets.families_and_children_xlsx.sheet_name)

        for idx, household_row in households.iterrows():

            # household master
            # indices = indices_by_headcount[household.household_headcount]  # ok
            # proba = proba_by_headcount[household.household_headcount]
            masters = narrow_housemasters_by_headcount_and_age_group(household_by_master, household_row)
            masters['probability'] = masters['Count'] / masters['Count'].sum()
            index = np.random.choice(masters.index.tolist(), p=masters['probability'])
            masters_age.append(masters.loc[index, 'Age'])
            masters_gender.append(entities.gender_from_string(masters.loc[index, 'Gender']).value)

            # family structure
            """if household_row.family_type == 1:
                households.loc[idx, 'family1'] = _get_family_structure(families_and_children_df,
                                                                       household_row.household_headcount)
            elif household_row.family_type == 2:
                # this is wrong, because neglects the fact that there can be a 3,3 family or a 3,4
                households.loc[idx, 'family1'] = _get_family_structure(families_and_children_df, 2)
                households.loc[idx, 'family2'] = _get_family_structure(families_and_children_df,
                                                                       household_row.household_headcount - 2)
            elif household_row.family_type == 3:
                households.loc[idx, 'family1'] = _get_family_structure(families_and_children_df, 2)
                households.loc[idx, 'family2'] = _get_family_structure(families_and_children_df, 2)
                households.loc[idx, 'family3'] = _get_family_structure(families_and_children_df,
                                                                       household_row.household_headcount - 4)"""

        households['master_age'] = masters_age
        households['master_gender'] = masters_gender
        households.to_excel(str(households_ready_xlsx), index=False)
    else:
        households = pd.read_excel(str(households_ready_xlsx))

    return households


def _age_gender_population(age_gender_df: pd.DataFrame) -> pd.DataFrame:
    ages = []
    genders = []
    for idx, row in age_gender_df.iterrows():
        ages.extend([row.Age] * row.Total)
        genders.extend([entities.Gender.MALE.value] * row.Males)
        genders.extend([entities.Gender.FEMALE.value] * row.Females)
    return pd.DataFrame(data={entities.prop_age: ages, entities.prop_gender: genders})


def generate_public_transport_usage(pop_size):
    return sample_from_distribution(pop_size, 'bernoulli', 0.28)


def generate_public_transport_duration(pop):
    transport_users = pop[pop == 1]
    transport_users_idx = transport_users.index.tolist()
    transport_duration = pd.Series([0] * len(pop.index), index=pop.index)
    mean_duration_per_day = 1.7 * 32 * len(pop.index) / len(transport_users.index)
    x = sample_from_distribution(len(transport_users), 'norm', loc=0, scale=1)
    scaled_x = MinMaxScaler(feature_range=(0, 2 * mean_duration_per_day)).fit_transform(x.reshape(-1, 1))
    transport_duration.loc[transport_users_idx] = scaled_x[:, 0]
    return transport_duration


def generate_employment(data_folder, age_gender_pop):

    production_age = pd.read_excel(str(data_folder / datasets.production_age.file_name))

    # 4_kwartal_wroclaw_tablice
    average_employment = 187200
    merged = pd.merge(age_gender_pop, production_age, how='left', on=['age', 'gender'])
    work_force = merged[merged.economic_group == 'production']
    employed_idx = np.random.choice(work_force.index.tolist(), size=average_employment)

    vector = pd.Series(data=entities.EmploymentStatus.NOT_EMPLOYED.value, index=age_gender_pop.index)
    vector.loc[employed_idx] = entities.EmploymentStatus.EMPLOYED.value
    return vector


def generate_population(data_folder: Path, output_folder: Path, households: pd.DataFrame):
    population_ready_xlsx = output_folder / datasets.population_xlsx.file_name
    if not population_ready_xlsx.is_file():

        # get this age_gender dataframe and sample for each person
        # or ignore population_size and sum up all
        age_gender_df = pd.read_excel(str(data_folder / datasets.age_gender_xlsx.file_name),
                                      sheet_name=datasets.age_gender_xlsx.sheet_name)

        population = _age_gender_population(age_gender_df)
        population[entities.prop_household] = entities.HOUSEHOLD_NOT_ASSIGNED
        production_age_df = pd.read_excel(str(data_folder / datasets.production_age.file_name),
                                          sheet_name=datasets.production_age.sheet_name)
        population = pd.merge(population, production_age_df, on=['age', 'gender'], how='left')

        # get indices of households of a specific age, gender
        df23 = households.groupby(by=['master_age', 'master_gender'], sort=False).size() \
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
                    logging.info(f'THere are more masters than people in the population for {df23_row}. '
                                 f'Making all people within this cluster masters.')
                    masters_indices = subpopulation
                    households_indices = np.random.choice(households_indices, replace=False, size=len(masters_indices))
                else:
                    raise
            population.loc[masters_indices, entities.prop_household] = households_indices
            households.loc[households_indices, 'house_master'] = masters_indices

        # now we need to lodge other people
        for idx, household_row in households.iterrows():
            lodged_headcount = 1
            try:
                hm_generation = population.iloc[household_row.house_master]['generation']
            except ValueError as e:
                logging.error(f'ValueError ({str(e)}) for {household_row.household_index} (house_master={household_row.house_master})')
                continue
            except TypeError as e:
                logging.error(f'TypeError ({str(e)}) for {household_row.household_index} (house_master={household_row.house_master})')
                continue
            # at least one person from each generation
            if lodged_headcount < household_row.household_headcount:
                homeless = population[population[entities.prop_household] == entities.HOUSEHOLD_NOT_ASSIGNED]
                if household_row.young == 1 and hm_generation != 'young':
                    young_homeless_idx = np.random.choice(homeless[homeless.generation == 'young'].index.tolist())
                    population.loc[young_homeless_idx, entities.prop_household] = household_row.household_index
                    lodged_headcount += 1

                if household_row.middle == 1 and hm_generation != 'middle':
                    middle_homeless_idx = np.random.choice(homeless[homeless.generation == 'middle'].index.tolist())
                    population.loc[middle_homeless_idx, entities.prop_household] = household_row.household_index
                    lodged_headcount += 1

                if household_row.elderly == 1 and hm_generation != 'elderly':
                    homeless_idx = np.random.choice(homeless[homeless.generation == 'elderly'].index.tolist())
                    population.loc[homeless_idx, entities.prop_household] = household_row.household_index
                    lodged_headcount += 1

            age_groups_in_household = []
            if household_row.young == 1:
                age_groups_in_household.append('young')
            if household_row.middle == 1:
                age_groups_in_household.append('middle')
            if household_row.elderly == 1:
                age_groups_in_household.append('elderly')

            while lodged_headcount < household_row.household_headcount:
                if len(age_groups_in_household) == 0:
                    logging.info(f'Ups, no more admissible people. No generations left for {household_row}')
                    break
                generation = age_groups_in_household[np.random.choice(list(range(len(age_groups_in_household))))]
                homeless = population[(population[entities.prop_household] == entities.HOUSEHOLD_NOT_ASSIGNED)]
                if len(homeless) == 0:
                    logging.info('No more homeless people. Quiting lodging process.')
                    break
                homeless_gen = homeless[homeless.generation == generation].index.tolist()
                if len(homeless_gen) == 0:
                    logging.info(f'No more homeless within {generation} generation for household: \n{household_row}')
                    age_groups_in_household.remove(generation)
                    continue

                homeless_idx = np.random.choice(homeless_gen)
                population.loc[homeless_idx, entities.prop_household] = household_row.household_index
                lodged_headcount += 1

        households.to_excel(str(output_folder / datasets.households_xlsx.file_name),
                            sheet_name=datasets.households_xlsx.sheet_name, index=False)

        # social competence based on previous findings, probably to be changed
        population[entities.prop_social_competence] = generate_social_competence(len(population.index))
        # transportation
        population[entities.prop_public_transport_usage] = generate_public_transport_usage(len(population.index))
        # transportation duration
        population[entities.prop_public_transport_duration] = generate_public_transport_duration(
            population[entities.prop_public_transport_usage])

        population[entities.prop_employment_status] = generate_employment(data_folder,
            population[[entities.prop_age, entities.prop_gender]])

        population.to_excel(str(output_folder / datasets.population_xlsx.file_name), index=False)
    else:
        population = pd.read_excel(str(output_folder / datasets.population_xlsx.file_name))
    return population


def generate(data_folder: Path, population_size: int = 641607, simulations_folder: Path = None) -> pd.DataFrame:
    """
    Generates a population given the folder with data and the size of this population.
    :param data_folder: folder with data
    :param population_size: size of a population to generate; default is the size of the population of Wrocław
    :param simulations_folder: the path to a folder where population and households for this simulation are to be saved.
    If the folder already exists and contains households.xlsx then households are read from the file. If the folder
    already exists and contains population.xslx file then a population is read from the file.
    :return: a pandas dataframe with a population generated from the data in data_folder
    """
    voivodship = data_folder.name[0]
    voivodship_folder = data_folder.parents[0] / voivodship

    # simulations folder
    if simulations_folder is None:
        simulations_folder = project_dir / 'data' / 'simulations' / datetime.now().strftime('%Y%m%d_%H%M')
    if not simulations_folder.is_dir():
        simulations_folder.mkdir()

    households = generate_households(data_folder, voivodship_folder, simulations_folder)
    population = generate_population(data_folder, simulations_folder, households)
    return population


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]
    data_folder = project_dir / 'data' / 'processed' / 'poland' / 'DW'

    # To read population data from a file:
    # sim_dir = project_dir / 'data' / 'simulations' / '20200308_0010'
    # generate(data_folder, simulations_folder=sim_dir)

    # or to generate a new dataset
    generate(data_folder)

    # KNOWN ISSUES:
    # 1. age is in the range format (30-34, 35-39, etc. for exact values see data/processed/poland/DW/age_gender.xlsx)
    # 2. some people are homeless (mostly 50-59 year old, to be investigated)
