from dataclasses import dataclass


@dataclass
class XlsxFile:
    file_name: str
    sheet_name: str


age_gender_xlsx = XlsxFile('age_gender.xlsx', 'processed')
families_and_childer_xlsx = XlsxFile('families_and_children.xlsx', 'processed')
families_per_household_xlsx = XlsxFile('families_per_household.xlsx', 'Sheet1')
generations_configuration_xlsx = XlsxFile('generations_configuration.xlsx', 'processed')
household_family_structure_xlsx = XlsxFile('household_family_structure.xlsx', 'Sheet1')
household_family_structure_old_xlsx = XlsxFile('household_family_structure_old.xlsx', 'Sheet1')
households_xlsx = XlsxFile('households.xlsx', 'Sheet1')
households_count_xlsx = XlsxFile('households_count.xlsx', 'processed')
households_old_xlsx = XlsxFile('households_old.xlsx', 'Sheet1')

households_by_master_xlsx = XlsxFile('households_by_master.xlsx', 'House_Master')

