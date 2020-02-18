import json


class FileCreator:
    def __init__(self, output_path):
        self._output_path = output_path

    def create_json_file(self, data, file_name):
        json_data = json.dumps(data)

        full_path = os.path.join(self._output_path, '{}.json'.format(file_name))
        with open(full_path, 'w') as output_file:
            output_file.write(json_data)
