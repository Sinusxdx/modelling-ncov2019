# -*- coding: utf-8 -*-
import click
import logging
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
from dummy_data.runner.dummy_runner import DummyRunner


@click.command()
@click.argument('input_filepath', type=click.Path(exists=True))
@click.argument('output_filepath', type=click.Path())
@click.option('--dummy', is_flag=True)
def main(input_filepath, output_filepath, dummy):
    """ Runs data processing scripts to turn raw data from (../raw) into
        cleaned json data ready to be analyzed (saved in ../processed).
    """
    logger = logging.getLogger(__name__)

    if dummy:
        nodes = click.prompt('How many dummy nodes do you need?', type=int)
        runner = DummyRunner(nodes, output_filepath)

        msg = 'making dummy data...'
        logger.info(msg)

        runner.run()

    else:
        msg = 'making final data set from raw data is not supported'
        logger.warning(msg)


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    main()
