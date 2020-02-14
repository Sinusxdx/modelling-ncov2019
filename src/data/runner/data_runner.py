import logging
from src.data.structures.structures_creator import StructCreator
from src.data.file_manager.file_creator import FileCreator


class Runner:
    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self._structures = StructCreator()
        self._file_manager = FileCreator(kwargs['output_filepath'])

    def run(self):
        if self._kwargs['node_structure']:
            msg = 'Creating a node structure...'
            logging.info(msg)

            created_data = self._structures.create_node()
            self._file_manager.create_json_file(created_data, 'node_structure')

            msg = 'The node structure has been created'
            logging.info(msg)

        if self._kwargs['household_structure']:
            msg = 'Creating a household structure...'
            logging.info(msg)

            created_data = self._structures.create_household()
            self._file_manager.create_json_file(created_data, 'household_structure')

            msg = 'The household structure has been created'
            logging.info(msg)

        if self._kwargs['container_structure']:
            msg = 'Creating a container structure...'
            logging.info(msg)

            created_data = self._structures.create_container()
            self._file_manager.create_json_file(created_data, 'container_structure')

            msg = 'The container structure has been created'
            logging.info(msg)