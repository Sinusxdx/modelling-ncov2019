# -*- coding: utf-8 -*-
import click
import logging
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
from src.data.runner.data_runner import Runner


@click.command()
@click.argument('output_filepath', type=click.Path())
@click.option('--node-structure', is_flag=True)
@click.option('--household-structure', is_flag=True)
@click.option('--container-structure', is_flag=True)
@click.option('--professions-structure', is_flag=True)
def main(**kwargs):
    """ Runs script to create files with structures in the json format."""
    logger = logging.getLogger(__name__)
    logger.info('Creating structures...')
    runner = Runner(**kwargs)
    runner.structures()
    logger.info('Structures have been created')


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    main()
