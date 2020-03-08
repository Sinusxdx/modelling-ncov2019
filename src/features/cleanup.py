from pathlib import Path
import shutil
from src.data import datasets
from src.features import entities
import pandas as pd
import numpy as np


def backup(src_dir: Path, dst_dir: Path, xlsx: datasets.XlsxFile) -> bool:
    if not (dst_dir / xlsx.file_name).is_file():
        return shutil.copy2(str(src_dir / xlsx.file_name), str(dst_dir)) != ''
    return False


def remove_homeless(df: pd.DataFrame) -> pd.DataFrame:
    return df[df[entities.prop_household] != -1]


def drop_obsolete_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns = df.columns.tolist()
    to_drop = [col for col in columns if col not in entities.columns]
    return df.drop(columns=to_drop)


def age_range_to_age(df: pd.DataFrame) -> pd.DataFrame:
    idx = df[df.age.str.len() > 2].index.tolist()
    df.loc[idx, 'age'] = df.loc[idx].age.str.slice(0, 2).astype(int)
    df.loc[idx, 'age'] += np.random.choice(list(range(0, 5)), size=len(idx))
    return df


if __name__ == '__main__':

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]
    data_folder = project_dir / 'data' / 'processed' / 'poland' / 'DW'

    # To read population data from a file:
    sim_dir = project_dir / 'data' / 'simulations' / '20200308_0010'

    backup_dir = project_dir / 'data' / 'simulations' / 'backup'

    if backup(sim_dir, backup_dir, datasets.output_population_xlsx):

        df = pd.read_excel(str(sim_dir / datasets.output_population_xlsx.file_name))
        df = age_range_to_age(drop_obsolete_columns(remove_homeless(df)))
        df.to_excel(str(sim_dir / datasets.output_population_xlsx.file_name))

    else:
        print('Backup failed. Aborting')
