import os
import pandas as pd
from pathlib import Path

families_per_household_xlsx = 'households_with_families.xlsx'
household_family_structure_xlsx = 'household_family_structure.xlsx'


def prepare_family_structure_from_voivodship(data_folder):
    family_structure_input_sheet = 'processed'
    voivodship = os.path.basename(data_folder)[0]
    families_per_household_df = pd.read_excel(os.path.join(data_folder, families_per_household_xlsx))

    family_structure_df = pd.read_excel(os.path.join(data_folder, os.pardir, voivodship, household_family_structure_xlsx),
                                        sheet_name=family_structure_input_sheet)

    columns = family_structure_df.columns[1:]
    for col in columns:
        family_structure_df[col] = round(
            family_structure_df[col] * families_per_household_df.loc[0, col] / family_structure_df[col].sum())\
            .astype(int)

    family_structure_df.to_excel(os.path.join(data_folder, household_family_structure_xlsx), index=False)


def generate_household_indices(data_folder):
    headcount2 = []
    family_type = []

    family_structure_df = pd.read_excel(os.path.join(data_folder, household_family_structure_xlsx))

    for i, row in family_structure_df.iterrows():
        headcount2.extend([row['Household size']] * int(row['One family']))
        family_type.extend([1] * row['One family'])
        headcount2.extend([row['Household size']] * int(row['Two families']))
        family_type.extend([2] * row['Two families'])
        headcount2.extend([row['Household size']] * int(row['Three families']))
        family_type.extend([3] * row['Three families'])
        headcount2.extend([row['Household size']] * int(row['One person']))
        family_type.extend([0] * row['One person'])
        headcount2.extend([row['Household size']] * int(row['Nonfamily']))
        family_type.extend([0] * row['Nonfamily'])

    household_df = pd.DataFrame(
        data={'headcount': headcount2, 'family_type': family_type, 'household_index': list(range(len(headcount2)))})
    household_df.set_index('household_index').to_excel(os.path.join(data_folder, 'households.xlsx'))


if __name__ == '__main__':
    project_dir = Path(__file__).resolve().parents[2]
    data_folder = os.path.join(project_dir, 'data', 'processed', 'poland', 'DW')
    prepare_family_structure_from_voivodship(data_folder)
    generate_household_indices(data_folder)
