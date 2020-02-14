import json


class FileCreator:
    def __init__(self, output_path):
        self._output_path = output_path

    def create_json_file(self, data, file_name):
        json_data = json.dumps(data)

        full_path = "{}/{}.json".format(self._output_path, file_name)
        with open(full_path, 'w') as output_file:
            output_file.write(json_data)
