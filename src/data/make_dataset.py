# -*- coding: utf-8 -*-
import click
import logging
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
from src.data.runner.data_runner import Runner


@click.command()
@click.argument('output_filepath', type=click.Path())
@click.option('--node-structure', is_flag=True)
def main(**kwargs):
    """ Runs data processing scripts to turn raw data from (../raw) into
        cleaned json data ready to be analyzed (saved in ../processed).
    """
    logger = logging.getLogger(__name__)

    runner = Runner(**kwargs)
    runner.run()


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    main()
