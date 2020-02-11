import logging
from dummy_data.creator.content_creator import ContentCreator
from dummy_data.creator.file_creator import FileCreator


class DummyRunner:
    def __init__(self, nodes, output_path):
        self._file_creator = FileCreator(output_path)
        self._content_creator = ContentCreator(nodes)

    def run(self):
        # TODO: Create a family list
        rand_data = self._content_creator.create_data()
        self._file_creator.create_file(rand_data)

        msg = 'dummy data have been created'
        logging.info(msg)

