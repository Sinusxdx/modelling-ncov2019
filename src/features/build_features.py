# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from pathlib import Path
from . import entities
from typing import Tuple
import os


project_dir = Path(__file__).resolve().parents[2]
data_dir = os.path.join(project_dir, 'data', 'processed')


def sample_age_gender() -> Tuple[int, entities.Gender]:

    age_gender_df = pd.read_excel(os.path.join(data_dir, 'age_gender.xlsx'), sheet_name='processed')
    age_gender_df['age_probability'] = age_gender_df.Total / age_gender_df.Total.sum()

    index = np.random.choice(age_gender_df.index.tolist(), p=age_gender_df.age_probability)
    row = age_gender_df.iloc[index]
    age = int(row.Age)
    female_probability = row.Females / (row.Females + row.Males)
    genders = [entities.Gender.FEMALE, entities.Gender.MALE]
    gender = genders[np.random.choice([0, 1], p=[female_probability, 1-female_probability])]
    return age, gender

def sample_household(n):
    pass