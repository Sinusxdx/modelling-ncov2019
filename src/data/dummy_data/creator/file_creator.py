import json


class FileCreator:
    def __init__(self, output_path):
        self._output_path = output_path

    def create_file(self, data):
        json_data = json.dumps(data)

        with open(self._output_path + '/dummy_data.json', 'w') as output_file:
            output_file.write(json_data)
