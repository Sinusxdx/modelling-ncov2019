"""
This is mostly based on references/infection_alg.pdf
"""
import ast
from collections import defaultdict
from functools import lru_cache
import heapq
import json
import logging
import random
from shutil import copyfile
from time import time_ns

import fire
from git import Repo
import pandas as pd
import scipy.optimize
import scipy.stats
from tqdm import tqdm
from matplotlib import pyplot as plt

from src.models.schemas import *
from src.models.defaults import *
from src.models.states_and_functions import *


class InfectionModel:
    def __init__(self, params_path: str, df_individuals_path: str) -> None:
        self.params_path = params_path
        self.df_individuals_path = df_individuals_path
        logger.info('Loading params...')
        with open(params_path, 'r') as params_file:
            params = json.loads(
                params_file.read()
            )  # TODO: check whether this should be moved to different place
        self._params = dict()
        logger.info('Parsing params...')
        for key, schema in infection_model_schemas.items():
            self._params[key] = schema.validate(params.get(key, defaults[key]))

        self._df_individuals = None
        self._df_households = None
        self._global_time = None
        self._max_time = None
        self._expected_case_severity = None
        self._affected_people = 0
        self._deaths = 0
        self.event_queue = []
        self._fear_factor = {}
        self._infections_dict = {}
        self._progression_times_dict = {}
        self._infection_status = defaultdict(lambda: InfectionStatus.Healthy)
        self._set_up_data_frames()
        self.event_schema = event_schema_fun(self._df_individuals)


    @staticmethod
    def parse_random_seed(random_seed):
        np.random.seed(random_seed)
        random.seed(random_seed)

    @property
    def household_path(self):
        return os.path.join(self._params[OUTPUT_ROOT_DIR], self._params[EXPERIMENT_ID],
                            'input_df_households.csv')  # TODO: ensure that households are valid!

    def _set_up_data_frames(self) -> None:
        """
        The purpose of this method is to set up two dataframes.
        One is self._df_individuals that stores features for the population
        Second is self._df_households that stores list of people idx per household
        building df_households is time consuming, therefore we try to reuse previously computed df_households
        :return:
        """
        logger.info('Set up data frames: Reading population csv...')
        self._df_individuals = pd.read_csv(self.df_individuals_path)
        self._df_individuals.index = self._df_individuals.idx
        logger.info('Set up data frames: Building households df...')

        if os.path.exists(self.household_path):
            self._df_households = pd.read_csv(self.household_path, index_col=HOUSEHOLD_ID,
                                              converters={ID: ast.literal_eval})
        else:
            self._df_households = pd.DataFrame({ID: self._df_individuals.groupby(HOUSEHOLD_ID)[ID].apply(list)})
            os.makedirs(os.path.dirname(self.household_path), exist_ok=True)
            self._df_households.to_csv(self.household_path)

    def _fill_queue_based_on_auxiliary_functions(self) -> None:
        """
        The purpose of this method is to mark some people of the population as sick according to provided function.
        Possible functions: see possible values of ImportIntensityFunctions enum
        Outcome of the function can be adjusted by overriding default parameters:
        multiplier, rate, cap, infectious_probability.
        :return:
        """
        def _generate_event_times(func, rate, multiplier, cap, root_buffer=100, root_guess=0) -> list:
            root_min = root_guess - root_buffer
            root_max = root_guess + root_buffer
            time_events_ = []
            for i in range(1, 1 + cap):
                bisect_fun = lambda x: func(x, rate=rate, multiplier=multiplier) - i
                root = scipy.optimize.bisect(bisect_fun, root_min, root_max)
                time_events_.append(root)
                root_min = root
                root_max = root + root_buffer
            return time_events_

        import_intensity = self._params[IMPORT_INTENSITY]
        f_choice = convert_import_intensity_functions(import_intensity[FUNCTION])
        if f_choice == ImportIntensityFunctions.NoImport:
            return
        func = import_intensity_functions[f_choice]
        multiplier = import_intensity[MULTIPLIER]
        rate = import_intensity[RATE]
        cap = import_intensity[CAP]
        infectious_prob = import_intensity[INFECTIOUS]
        event_times = _generate_event_times(func=func, rate=rate, multiplier=multiplier, cap=cap)
        for event_time in event_times:
            person_id = self.df_individuals.index[np.random.randint(len(self.df_individuals))]
            t_state = TMINUS1
            if np.random.rand() < infectious_prob:
                t_state = T0
            self.append_event(Event(event_time, person_id, t_state,
                                    None, IMPORT_INTENSITY, self.global_time,
                                    self.epidemic_status))

    def _fill_queue_based_on_initial_conditions(self):
        """
        The purpose of this method is to mark some people of the population as sick according to provided
        initial conditions.
        Conditions can be provided using one of two supported schemas.
        schema v1 is list with details per person, while schema v2 is dictionary specifying selection algorithm
        and cardinalities of each group of patients (per symptom).
        :return:
        """
        def _assign_t_state(status):
            if status == CONTRACTION:
                return TMINUS1
            if status == INFECTIOUS:
                return T0
            raise ValueError(f'invalid initial infection status {status}')

        initial_conditions = self._params[INITIAL_CONDITIONS]
        if isinstance(initial_conditions, list):  # schema v1
            for initial_condition in initial_conditions:
                person_idx = initial_condition[PERSON_INDEX]
                t_state = _assign_t_state(initial_condition[INFECTION_STATUS])
                if EXPECTED_CASE_SEVERITY in initial_condition:
                    self._expected_case_severity[person_idx] = convert_expected_case_severity(
                        initial_condition[EXPECTED_CASE_SEVERITY]
                    )
                self.append_event(Event(initial_condition[CONTRACTION_TIME], person_idx, t_state, None,
                                        INITIAL_CONDITIONS, self.global_time, self.epidemic_status))
        elif isinstance(initial_conditions, dict):  # schema v2
            if initial_conditions[SELECTION_ALGORITHM] == InitialConditionSelectionAlgorithms.RandomSelection.value:
                # initially all indices can be drawn
                choice_set = self._df_individuals.index.values
                for infection_status, cardinality in initial_conditions[CARDINALITIES].items():
                    if cardinality > 0:

                        r = range(choice_set.shape[0])
                        selected_rows_ids = random.sample(r, k=cardinality)
                        selected_rows = choice_set[selected_rows_ids]

                        # now only previously unselected indices can be drawn in next steps
                        choice_set = choice_set[list(set(r) - set(selected_rows))]
                        t_state = _assign_t_state(infection_status)
                        for row in selected_rows:
                            self.append_event(Event(self.global_time, row, t_state, None, INITIAL_CONDITIONS,
                                                    self.global_time, self.epidemic_status))
            else:
                err_msg = f'Unsupported selection algorithm provided {initial_conditions[SELECTION_ALGORITHM]}'
                logger.error(err_msg)
                raise ValueError(err_msg)
        else:
            err_msg = f'invalid schema provided {initial_conditions}'
            logger.error(err_msg)
            raise ValueError(err_msg)

    @property
    def global_time(self):
        return self._global_time

    @property
    def df_individuals(self):
        return self._df_individuals

    @property
    def epidemic_status(self):
        return self._params[EPIDEMIC_STATUS]

    @property
    def stop_simulation_threshold(self):
        return self._params[STOP_SIMULATION_THRESHOLD]

    @property
    def case_severity_distribution(self):
        return self._params[CASE_SEVERITY_DISTRIBUTION]

    @property
    def disease_progression(self):
        return self._params[DISEASE_PROGRESSION].get(self.epidemic_status, self._params[DISEASE_PROGRESSION][DEFAULT])

    @property
    def affected_people(self):
        return self._affected_people

    @property
    def deaths(self):
        return self._deaths

    def draw_expected_case_severity(self):
        # age_min, age_max(exclusively), fatality_prob
        age_induced_fatality_rates = [(0, 20, 0.002), (20, 40, 0.002), (40, 50, 0.004), (50, 60, 0.013),
                                      (60, 70, 0.036), (70, 80, 0.08), (80, 200, 0.148)]

        case_severity_dict = self.case_severity_distribution
        keys = [convert_expected_case_severity(x) for x in case_severity_dict]
        d = {}
        for age_min, age_max, fatality_prob in age_induced_fatality_rates:
            cond_lb = self._df_individuals[AGE] >= age_min
            cond_ub = self._df_individuals[AGE] < age_max
            cond = np.logical_and(cond_lb, cond_ub)
            age_induced_severity_distribution = dict()
            age_induced_severity_distribution[CRITICAL] = fatality_prob/self._params[DEATH_PROBABILITY][CRITICAL]
            for x in case_severity_dict:
                if x != CRITICAL:
                    age_induced_severity_distribution[x] = case_severity_dict[x] / (1 - case_severity_dict[CRITICAL]) * (1 - age_induced_severity_distribution[CRITICAL])
            distribution_hist = np.array([age_induced_severity_distribution[x] for x in case_severity_dict])
            dis = scipy.stats.rv_discrete(values=(
                np.arange(len(age_induced_severity_distribution)),
                distribution_hist
            ))
            realizations = dis.rvs(size=len(self._df_individuals[cond]))
            values = [keys[r] for r in realizations]
            df = pd.DataFrame(values, index=self._df_individuals[cond].index)
            d = {**d, **df.to_dict()[0]}
        return d

    @staticmethod
    def generate_random_sample(**kwargs) -> float:
        @lru_cache(maxsize=32)
        def cached_random_gen(**kwargs):
            distribution = kwargs.get('distribution', 'poisson')
            if distribution == FROM_FILE:
                filepath = kwargs.get('filepath', None).replace('$ROOT_DIR', config.ROOT_DIR)
                Schema(lambda x: os.path.exists(x)).validate(filepath)
                array = np.load(filepath)
                approximate_distribution = kwargs.get('approximate_distribution', None)
                if approximate_distribution == LOGNORMAL:
                    shape, loc, scale = scipy.stats.lognorm.fit(array, floc=0)
                    return scipy.stats.lognorm.rvs, [shape], {'loc': loc, 'scale': scale}
                elif approximate_distribution == GAMMA:
                    shape, loc, scale = scipy.stats.gamma.fit(array, floc=0)
                    return scipy.stats.gamma.rvs, [shape], {'loc': loc, 'scale': scale}
                if approximate_distribution:
                    raise ValueError(f'Approximating to this distribution {approximate_distribution}'
                                     f'is not yet supported but we can quickly add it if needed')
                # TODO: support no approximate distribution provided

            if distribution == LOGNORMAL:
                mean = kwargs.get('mean', 0.0)
                sigma = kwargs.get('sigma', 1.0)
                return np.random.lognormal, [], {'mean': mean, 'sigma': sigma}

            lambda_ = kwargs.get('lambda', 1.0)
            if distribution == 'exponential':
                return np.random.exponential, [], {'scale': 1/lambda_}
            if distribution == 'poisson':
                return np.random.poisson, [], {'lam': lambda_}
            raise ValueError(f'Sampling from distribution {distribution} is not yet supported but we can quickly add it')
        f, args, kwargs = cached_random_gen(**kwargs)
        return f(*args, **kwargs)

    def handle_t0(self, id):
        if self._infection_status[id] == InfectionStatus.Contraction:
            self._infection_status[id] = InfectionStatus.Infectious
        elif self._infection_status[id] != InfectionStatus.Infectious:
            logger.error(f'state machine failure. was {self._infection_status[id]} id: {id}')
        if self._df_individuals.loc[id, P_TRANSPORT] > 0:
            self.add_potential_contractions_from_transport_kernel(id)
        if self._df_individuals.loc[id, EMPLOYMENT_STATUS] > 0:
            self.add_potential_contractions_from_employment_kernel(id)
        if len(self._df_households.loc[self._df_individuals.loc[id, HOUSEHOLD_ID]][ID]) > 1:
            self.add_potential_contractions_from_household_kernel(id)
        self.add_potential_contractions_from_friendship_kernel(id)
        self.add_potential_contractions_from_sporadic_kernel(id)
        self.add_potential_contractions_from_constant_kernel(id)

    def generate_disease_progression(self, person_id, features, event_time: float,
                                     initial_infection_status: InfectionStatus) -> None:
        """Returns list of disease progression events
        "future" disease_progression should be recalculated when the disease will be recognised at the state level
        t0 - time when individual becomes infectious (Mild symptoms)
        t1 - time when individual stay home/visit doctor due to Mild/Serious? symptoms
        t2 - time when individual goes to hospital due to Serious symptoms
        """
        tminus1 = None
        t0 = None
        if initial_infection_status == InfectionStatus.Contraction:
            tminus1 = event_time
            t0 = tminus1 + self.generate_random_sample(**self.disease_progression[T0])
            self.append_event(Event(t0, person_id, T0, person_id, DISEASE_PROGRESSION,
                                    tminus1, self.epidemic_status))
        elif initial_infection_status == InfectionStatus.Infectious:
            t0 = event_time
        else:
            raise ValueError(f'invalid initial infection status {initial_infection_status}')
        t2 = None
        # t3 = None
        if self._expected_case_severity[person_id] in [
            ExpectedCaseSeverity.Severe,
            ExpectedCaseSeverity.Critical
        ]:
            t2 = t0 + self.generate_random_sample(**self.disease_progression[T2])
            self.append_event(Event(t2, person_id, T2, person_id, DISEASE_PROGRESSION, t0, self.epidemic_status))

        t1 = t0 + self.generate_random_sample(**self.disease_progression[T1])
        if not t2 or t1 < t2:
            self.append_event(Event(t1, person_id, T1, person_id, DISEASE_PROGRESSION, t0, self.epidemic_status))
        else:
            t1 = None
        #self._df_progression_times =
        tdetection = None
        trecovery = None
        tdeath = None
        if np.random.rand() <= self._params[DEATH_PROBABILITY][self._expected_case_severity[person_id].value]:
            tdeath = t0 + self.generate_random_sample(**self.disease_progression[TDEATH])
            self.append_event(Event(tdeath, person_id, TDEATH, person_id, DISEASE_PROGRESSION, t0, self.epidemic_status))
        else:
            #trecovery =
            pass
        self._progression_times_dict[person_id] = {ID: person_id, TMINUS1: tminus1, T0: t0, T1: t1, T2: t2,
                                                   TDEATH: tdeath}
                                                   #TDETECTION: tdetection, TRECOVERY: trecovery, TDEATH: tdeath}
        if initial_infection_status == InfectionStatus.Infectious:
            self.handle_t0(person_id)

    def doubling_time(self, simulation_output_dir):
        def doubling(x, y, window=100):
            x1 = x[:-window]
            x2 = x[window:]
            y1 = y[:-window]
            y2 = y[window:]
            a = (x2 - x1) * np.log(2)
            b = np.log(y2/y1)
            c = a / b
            return c # (x2 - x1) * np.log(2) / np.log(y2 / y1)

        def plot_doubling(x, window=100):
            if len(x) > window:
                xval = x[:-window]
                yval = doubling(x.values, np.arange(len(x)))
                plt.plot(xval[yval<28], yval[yval<28])
                return True
            return False

        df_r1 = self.df_progression_times
        df_r2 = self.df_infections

        plt.close()
        vals = df_r2.contraction_time.sort_values()
        legend = []
        if plot_doubling(vals):
            legend.append('Trend line for total # infected')
        cond1 = df_r2.contraction_time[df_r2.kernel == 'import_intensity'].sort_values()
        cond2 = df_r2.contraction_time[df_r2.kernel == 'constant'].sort_values()
        cond3 = df_r2.contraction_time[df_r2.kernel == 'household'].sort_values()
        if plot_doubling(cond1):
            legend.append('Trend line for # imported cases')
        if plot_doubling(cond2):
            legend.append('Trend line for Infected through constant kernel')
        if plot_doubling(cond3):
            legend.append('Trend line for Infected through household kernel')
        hospitalized_cases = df_r1[~df_r1.t2.isna()].sort_values(by='t2').t2
        ho_cases = hospitalized_cases[hospitalized_cases < df_r2.contraction_time.max(axis=0)].sort_values()
        death_cases = df_r1[~df_r1.tdeath.isna()].sort_values(by='tdeath').tdeath
        d_cases = death_cases[death_cases < df_r2.contraction_time.max(axis=0)].sort_values()
        if plot_doubling(ho_cases):
            legend.append('Trend line for # hospitalized cases')
        if plot_doubling(d_cases):
            legend.append('Trend line for # deceased cases')
        plt.legend(legend)
        plt.title(f'Doubling times for simulation of covid19 dynamics\n {self._params[EXPERIMENT_ID]}')
        plt.savefig(os.path.join(simulation_output_dir, 'doubling_times.png'))

    def draw_death_age_cohorts(self, simulation_output_dir):
        df_r1 = self.df_progression_times
        df_r2 = self.df_infections
        df_in = self.df_individuals
        plt.close()
        lims = [(0, 20, '[0-19]'), (20, 40, '[20-39]'), (40, 50, '[40-49]'), (50, 60, '[50-59]'), (60, 70, '[60-69]'),
                (70, 80, '[70-79]'), (80, 200, '[80+]')]
        legend = []
        for limm, limM, descr in lims:
            cond1 = df_in.age >= limm
            cond2 = df_in.age < limM
            cond = np.logical_and(cond1, cond2)
            filtered = df_r1[cond]
            death_cases = filtered[~filtered.tdeath.isna()].sort_values(by='tdeath').tdeath
            d_cases = death_cases[death_cases < df_r2.contraction_time.max(axis=0)].sort_values()
            d_times = np.arange(len(d_cases))
            plt.plot(np.append(d_cases, df_r2.contraction_time.max(axis=0)
                               ), np.append(d_times, len(d_cases)))
            legend.append(descr)

        plt.legend(legend)
        experiment_id = self._params[EXPERIMENT_ID]
        plt.title(f'cumulative deceased cases per age group \n {experiment_id}')
        plt.savefig(os.path.join(simulation_output_dir, 'deceased_cases_age_analysis.png'))

    def log_outputs(self):
        run_id = f'{time_ns()}_{self._params[RANDOM_SEED]}'
        simulation_output_dir = os.path.join(self._params[OUTPUT_ROOT_DIR],
                                             self._params[EXPERIMENT_ID],
                                             run_id)
        os.makedirs(simulation_output_dir)
        self.df_progression_times.to_csv(os.path.join(simulation_output_dir, 'output_df_progression_times.csv'))
        self.df_infections.to_csv(os.path.join(simulation_output_dir, 'output_df_potential_contractions.csv'))
        df_output_individuals = self._df_individuals.copy()
        df_output_individuals[EXPECTED_CASE_SEVERITY] = pd.Series(self._expected_case_severity)
        df_output_individuals[INFECTION_STATUS] = pd.Series(self._infection_status)
        df_output_individuals.to_csv(os.path.join(simulation_output_dir, 'output_df_individuals.csv'))
        if self._params[SAVE_INPUT_DATA]:

            copyfile(self.df_individuals_path, os.path.join(simulation_output_dir,
                                                            f'input_{os.path.basename(self.df_individuals_path)}'))
            copyfile(self.household_path, os.path.join(simulation_output_dir,
                                                       f'input_{os.path.basename(self.household_path)}'))
            copyfile(self.params_path, os.path.join(simulation_output_dir,
                                                    f'input_{os.path.basename(self.params_path)}'))
        repo = Repo(config.ROOT_DIR)
        git_active_branch_log = os.path.join(simulation_output_dir, 'git_active_branch_log.txt')
        with open(git_active_branch_log, 'w') as f:
            f.write(f'Active branch name {repo.active_branch.name}\n')
            f.write(str(repo.active_branch.log()))

        git_status = os.path.join(simulation_output_dir, 'git_status.txt')
        with open(git_status, 'w') as f:
            f.write(repo.git.status())

        self.store_graphs(simulation_output_dir)
        self.store_bins(simulation_output_dir)
        self.store_semilogy(simulation_output_dir)
        self.store_event_queue(simulation_output_dir)
        self.doubling_time(simulation_output_dir)
        self.icu_beds(simulation_output_dir)
        self.draw_death_age_cohorts(simulation_output_dir)

    def icu_beds(self, simulation_output_dir):
        df_r1 = self.df_progression_times
        df_r2 = self.df_infections
        individuals_severity = pd.Series(self._expected_case_severity)

        plt.close()
        critical = df_r1[individuals_severity == ExpectedCaseSeverity.Critical]
        plus = critical.t2.values
        deceased = critical[~critical.tdeath.isna()]
        survived = critical[critical.tdeath.isna()]
        FOUR_WEEKS = 28
        minus1 = survived.t2.values + FOUR_WEEKS
        minus2 = deceased.tdeath.values
        df = pd.DataFrame({'t': plus, 'd': np.ones_like(plus)}).append(
            pd.DataFrame({'t': minus1, 'd': -np.ones_like(minus1)})).append(
            pd.DataFrame({'t': minus2, 'd': -np.ones_like(minus2)})
        ).sort_values(by='t')
        df = df[df.t <= df_r2.contraction_time.max(axis=0)]
        cumv = df.d.cumsum().values
        plt.plot(df.t.values, cumv)
        death_cases = df_r1[~df_r1.tdeath.isna()].sort_values(by='tdeath').tdeath
        d_cases = death_cases[death_cases < df_r2.contraction_time.max(axis=0)].sort_values()
        plt.plot(d_cases, np.arange(len(d_cases)))
        icu_availability = 100
        plt.plot(d_cases, np.ones(len(d_cases)) * icu_availability)
        legend = ['ICU beds required', '# deceased cases', 'ICU beds available']
        if sum(cumv > 100) > 0:
            critical_t = df.t.values[cumv > 100].min()
            plt.plot([critical_t] * 2, [0, max(d_cases.max(), cumv.max())])
            legend.append(f'Critical time {critical_t:.1f}')
        plt.legend(legend, loc='upper left')
        plt.title(f'ICU beds needed assuming 4 weeks for recovery \n {self._params[EXPERIMENT_ID]}')
        plt.savefig(os.path.join(simulation_output_dir, 'icu_beds_analysis.png'))

    def store_event_queue(self, simulation_output_dir):
        import pickle
        with open(os.path.join(simulation_output_dir, 'save_state_event_queue.pkl'), 'wb') as f:
            pickle.dump(self.event_queue, f)

    def store_bins(self, simulation_output_dir):
        df_r1 = self.df_progression_times
        df_r2 = self.df_infections
        plt.close()
        bins = np.arange(1 + df_r2.contraction_time.max())
        cond1 = df_r2.contraction_time[df_r2.kernel == 'import_intensity'].sort_values()
        cond2 = df_r2.contraction_time[df_r2.kernel == 'constant'].sort_values()
        cond3 = df_r2.contraction_time[df_r2.kernel == 'household'].sort_values()
        cond1.hist(alpha=0.3, histtype='stepfilled', bins=bins)
        cond2.hist(alpha=0.3, histtype='stepfilled', bins=bins)
        cond3.hist(alpha=0.3, histtype='stepfilled', bins=bins)
        hospitalized_cases = df_r1[~df_r1.t2.isna()].sort_values(by='t2').t2
        ho_cases = hospitalized_cases[hospitalized_cases < df_r2.contraction_time.max(axis=0)].sort_values()
        death_cases = df_r1[~df_r1.tdeath.isna()].sort_values(by='tdeath').tdeath
        d_cases = death_cases[death_cases < df_r2.contraction_time.max(axis=0)].sort_values()
        ho_cases.hist(alpha=0.7, histtype='stepfilled', bins=bins)
        d_cases.hist(alpha=0.9, histtype='stepfilled', bins=bins)
        plt.legend(['# Imported cases', 'Infected through constant kernel',
                    'Infected through household kernel', '# hospitalized cases', '# deceased cases'])
        plt.title(f'1 day binning of simulated covid19\n {self._params[EXPERIMENT_ID]}')
        plt.savefig(os.path.join(simulation_output_dir, 'bins.png'))

    def store_graphs(self, simulation_output_dir):
        df_r1 = self.df_progression_times
        df_r2 = self.df_infections
        vals = df_r2.contraction_time.sort_values()
        plt.plot(vals, np.arange(len(vals)))
        cond1 = df_r2.contraction_time[df_r2.kernel == 'import_intensity'].sort_values()
        cond2 = df_r2.contraction_time[df_r2.kernel == 'constant'].sort_values()
        cond3 = df_r2.contraction_time[df_r2.kernel == 'household'].sort_values()
        plt.plot(cond1, np.arange(len(cond1)))
        plt.plot(cond2, np.arange(len(cond2)))
        plt.plot(cond3, np.arange(len(cond3)))
        hospitalized_cases = df_r1[~df_r1.t2.isna()].sort_values(by='t2').t2
        ho_cases = hospitalized_cases[hospitalized_cases < df_r2.contraction_time.max(axis=0)].sort_values()
        death_cases = df_r1[~df_r1.tdeath.isna()].sort_values(by='tdeath').tdeath
        d_cases = death_cases[death_cases < df_r2.contraction_time.max(axis=0)].sort_values()

        plt.plot(ho_cases, np.arange(len(ho_cases)))
        plt.plot(d_cases, np.arange(len(d_cases)))
        plt.legend(['Total # infected', '# Imported cases', 'Infected through constant kernel',
                    'Infected through household kernel', '# hospitalized cases', '# deceased cases'])
        plt.title(f'simulation of covid19 dynamics\n {self._params[EXPERIMENT_ID]}')
        plt.savefig(os.path.join(simulation_output_dir, 'summary.png'))

    def store_semilogy(self, simulation_output_dir):
        df_r1 = self.df_progression_times
        df_r2 = self.df_infections
        plt.close()
        vals = df_r2.contraction_time.sort_values()

        plt.semilogy(vals, np.arange(len(vals)))
        cond1 = df_r2.contraction_time[df_r2.kernel == 'import_intensity'].sort_values()
        cond2 = df_r2.contraction_time[df_r2.kernel == 'constant'].sort_values()
        cond3 = df_r2.contraction_time[df_r2.kernel == 'household'].sort_values()

        plt.semilogy(cond1, np.arange(len(cond1)))
        plt.semilogy(cond2, np.arange(len(cond2)))
        plt.semilogy(cond3, np.arange(len(cond3)))
        hospitalized_cases = df_r1[~df_r1.t2.isna()].sort_values(by='t2').t2
        ho_cases = hospitalized_cases[hospitalized_cases < df_r2.contraction_time.max(axis=0)].sort_values()
        death_cases = df_r1[~df_r1.tdeath.isna()].sort_values(by='tdeath').tdeath
        d_cases = death_cases[death_cases < df_r2.contraction_time.max(axis=0)].sort_values()
        plt.semilogy(ho_cases, np.arange(len(ho_cases)))
        plt.semilogy(d_cases, np.arange(len(d_cases)))
        plt.legend(['Total # infected', '# Imported cases', 'Infected through constant kernel',
                    'Infected through household kernel', '# hospitalized cases', '# deceased cases'])
        plt.title(f'simulation of covid19 dynamics\n {self._params[EXPERIMENT_ID]}')
        plt.savefig(os.path.join(simulation_output_dir, 'summary_semilogy.png'))

    def setup_simulation(self):
        self.event_queue = []

        self._affected_people = 0
        self._deaths = 0
        # TODO add more online stats like: self._active_people = 0
        # TODO  and think how to better group them, ie namedtuple state_stats?

        self._fear_factor = {}
        self._infection_status = defaultdict(lambda: InfectionStatus.Healthy)
        self._infections_dict = {}
        self._progression_times_dict = {}

        self._global_time = self._params[START_TIME]
        self._max_time = self._params[MAX_TIME]
        self._expected_case_severity = self.draw_expected_case_severity()

    def run_simulation(self):
        def _inner_loop(iter):
            with tqdm(total=None) as pbar:
                while self.pop_and_apply_event():
                    affected = self.affected_people
                    pbar.set_description(f'Iter: {iter} - Time: {self.global_time:.2f} - Affected: {affected}') # - fear constant: {self.fear("constant"):.3f} - fear household: {self.fear("household"):.3f}')
                    if affected >= self.stop_simulation_threshold:
                        logging.info(f"The outbreak reached a high number {self.stop_simulation_threshold}")
                        return True
                return False

        seeds = None
        if isinstance(self._params[RANDOM_SEED], str):
            seeds = eval(self._params[RANDOM_SEED])
        elif isinstance(self._params[RANDOM_SEED], int):
            seeds = [self._params[RANDOM_SEED]]
        outbreak_proba = 0.0
        mean_time_when_outbreak = 0.0
        mean_affected_when_no_outbreak = 0.0
        outbreaks = 0
        for i, seed in enumerate(seeds):
            self.parse_random_seed(seed)
            self.setup_simulation()
            logger.info('Filling queue based on initial conditions...')
            self._fill_queue_based_on_initial_conditions()
            logger.info('Filling queue based on auxiliary functions...')
            self._fill_queue_based_on_auxiliary_functions()
            logger.info('Initialization step is done!')
            outbreak = _inner_loop(i + 1)
            outbreak_proba = (i * outbreak_proba + outbreak) / (i + 1)
            if outbreak:
                mean_time_when_outbreak  = (mean_time_when_outbreak * outbreaks + self._global_time) / (outbreaks + 1)
                outbreaks += 1
            else:
                no_outbreaks = i - outbreaks
                mean_affected_when_no_outbreak = (mean_affected_when_no_outbreak * no_outbreaks + self._affected_people) / (no_outbreaks + 1)
            if self._params[LOG_OUTPUTS]:
                self.log_outputs()
        parsed_comment = self._params[COMMENT]
        try:
            parsed_comment = eval(self._params[COMMENT])
        except:
            pass
        logger.info(f'\nExperiment id: {self._params[EXPERIMENT_ID]}'
                    f'\nExperiment comment: {parsed_comment}'
                    f'\nOutbreak proba: {outbreak_proba}'
                    f'\nMean time if outbreak: {mean_time_when_outbreak}'
                    f'\nMean affected when no outbreak: {mean_affected_when_no_outbreak}')

    def append_event(self, event: Event) -> None:
        heapq.heappush(self.event_queue, event)

    @property
    def df_infections(self):
        return pd.DataFrame.from_dict(self._infections_dict, orient='index') #, ignore_index=True) #orient='index', columns=columns)

    @property
    def df_progression_times(self):
        return pd.DataFrame.from_dict(self._progression_times_dict, orient='index') #, ignore_index=True)

    def add_new_infection(self, person_id, infection_status,
                          initiated_by, initiated_through):
        self._infection_status[person_id] = infection_status

        self._infections_dict[len(self._infections_dict)] = {
            SOURCE: initiated_by,
            TARGET: person_id,
            CONTRACTION_TIME: self.global_time,
            KERNEL: initiated_through
        }

        self._affected_people += 1
        self.generate_disease_progression(person_id,
                                          self._df_individuals.loc[person_id],
                                          self.global_time,
                                          infection_status)

    def add_potential_contractions_from_transport_kernel(self, id):
        pass

    def fear_factor(self, kernel_id):
        if kernel_id not in self._fear_factor:
            fear_factors = self._params[FEAR_FACTORS]
            self._fear_factor[kernel_id] = fear_factor_schema.validate(fear_factors.get(kernel_id, fear_factors.get(DEFAULT)))
        return self._fear_factor[kernel_id]

    def fear(self, kernel_id) -> float:
        if self.fear_factor(kernel_id) == FearFunctions.FearDisabled.value:
            return 1.0

        f = fear_functions[convert_fear_functions(self.fear_factor(kernel_id)[FEAR_FUNCTION])]
        limit_value = self.fear_factor(kernel_id)[LIMIT_VALUE]
        scale = self.fear_factor(kernel_id)[SCALE_FACTOR]
        weights_deaths = self.fear_factor(kernel_id)[DEATHS_MULTIPLIER]
        weights_detected = self.fear_factor(kernel_id)[DETECTED_MULTIPLIER]
        detected = self.affected_people
        deaths = self.deaths
        return f(detected, deaths, weights_detected, weights_deaths, scale, limit_value)

    def gamma(self, kernel_id):
        return self._params[TRANSMISSION_PROBABILITIES][kernel_id] * self.fear(kernel_id)

    def add_potential_contractions_from_household_kernel(self, id):
        prog_times = self._progression_times_dict[id]
        start = prog_times[T0]
        end = prog_times[T2]
        if end is None:
            end = start + prog_times[T0] + 14 # TODO: Fix the bug, this should Recovery Time
        total_infection_rate = (end - start) * self.gamma('household')
        household_id = self._df_individuals.loc[id, HOUSEHOLD_ID]
        inhabitants = self._df_households.loc[household_id][ID]
        possibly_affected_household_members = list(set(inhabitants) - {id})
        infected = np.minimum(np.random.poisson(total_infection_rate, size=1),
                              len(possibly_affected_household_members))[0]
        if infected == 0:
            return
        possible_choices = possibly_affected_household_members #.index.values

        '''r = range(len(possible_choices))
        selected_rows_ids = random.sample(r, k=infected)
        selected_rows = possible_choices[selected_rows_ids]
        '''
        selected_rows = np.random.choice(possible_choices, infected, replace=False)
        for row in selected_rows:
            person_idx = self._df_individuals.loc[row, ID]
            if self._infection_status[person_idx] == InfectionStatus.Healthy:
                contraction_time = np.random.uniform(low=start, high=end)
                self.append_event(Event(contraction_time, person_idx, TMINUS1,
                                        id, HOUSEHOLD, self.global_time,
                                        self.epidemic_status))

    def add_potential_contractions_from_employment_kernel(self, id):
        pass

    def add_potential_contractions_from_sporadic_kernel(self, id):
        pass

    def add_potential_contractions_from_friendship_kernel(self, id):
        pass

    def add_potential_contractions_from_constant_kernel(self, id):
        prog_times = self._progression_times_dict[id]
        start = prog_times[T0]
        end = prog_times[T1]
        if end is None:
            end = prog_times[T2]
        total_infection_rate = (end - start) * self.gamma('constant')
        infected = np.random.poisson(total_infection_rate, size=1)[0]
        if infected == 0:
            return
        possible_choices = self._df_individuals.index.values
        possible_choices = possible_choices[possible_choices != id]
        r = range(possible_choices.shape[0])
        selected_rows_ids = random.sample(r, k=infected)
        selected_rows = possible_choices[selected_rows_ids]
        for row in selected_rows:
            person_idx = self._df_individuals.loc[row, ID]
            if self._infection_status[person_idx] == InfectionStatus.Healthy:
                contraction_time = np.random.uniform(low=start, high=end)
                self.append_event(Event(contraction_time, person_idx, TMINUS1,
                                        id, CONSTANT, self.global_time,
                                        self.epidemic_status))

    # 'Event', [TIME, PERSON_INDEX, TYPE, INITIATED_BY, INITIATED_THROUGH, ISSUED_TIME, EPIDEMIC_STATUS])
    def pop_and_apply_event(self) -> bool:
        try:
            event = heapq.heappop(self.event_queue)
            type_ = getattr(event, TYPE)
            time = getattr(event, TIME)
            self._global_time = time
            if self._global_time > self._max_time:
                return False

            id = getattr(event, PERSON_INDEX)
            initiated_by = getattr(event, INITIATED_BY)
            initiated_through = getattr(event, INITIATED_THROUGH)

            # TODO the remaining two attributes will be useful when we will take into account
            #  change of the social network state to EPIDEMIC mode
            # issued_time = getattr(event, ISSUED_TIME)
            # epidemic_status = getattr(event, EPIDEMIC_STATUS)
            if initiated_by is None and initiated_through != DISEASE_PROGRESSION:
                if type_ == TMINUS1:
                    if self._infection_status[id] == InfectionStatus.Healthy:
                        self.add_new_infection(id, InfectionStatus.Contraction,
                                               initiated_by, initiated_through)
                if type_ == T0:
                    if self._infection_status[id] in [InfectionStatus.Healthy, InfectionStatus.Contraction]:
                            self.add_new_infection(id, InfectionStatus.Infectious,
                                                   initiated_by, initiated_through)
                return True
            if type_ == TMINUS1:
                # check if this action is still valid first
                initiated_inf_status = self._infection_status[initiated_by]
                current_status = self._infection_status[id]
                if current_status == InfectionStatus.Healthy:
                    if initiated_inf_status in active_states:
                        if initiated_through != HOUSEHOLD:
                            if initiated_inf_status != InfectionStatus.StayHome:
                                self.add_new_infection(id, InfectionStatus.Contraction,
                                                       initiated_by, initiated_through)
                        else:
                            self.add_new_infection(id, InfectionStatus.Contraction,
                                                   initiated_by, initiated_through)
            elif type_ == T0:
                self.handle_t0(id)
            elif type_ == T1:
                if self._infection_status[id] == InfectionStatus.Infectious:
                    self._infection_status[id] = InfectionStatus.StayHome
            elif type_ == T2:
                if self._infection_status[id] in [
                    InfectionStatus.StayHome,
                    InfectionStatus.Infectious
                ]:
                    self._infection_status[id] = InfectionStatus.Hospital
            elif type_ == TDEATH:
                if self._infection_status[id] != InfectionStatus.Death:
                    self._infection_status[id] = InfectionStatus.Death
                    self._deaths += 1

            # TODO: add more important logic
            return True
        except IndexError:
            return False

    def recalculate_event_queue(self):
        # TODO -> this will be important with state actions implemented like quarantine at home
        pass


logger = logging.getLogger(__name__)


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    pd.set_option('display.max_columns', None)
    fire.Fire(InfectionModel)