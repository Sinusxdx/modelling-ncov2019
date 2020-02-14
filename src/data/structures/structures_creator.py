import logging


class StructCreator:
    def __init__(self):
        pass

    @staticmethod
    def create_node():
        node_structure = {
                            'id': 'numeric',
                            'age': 'numeric',
                            'gender': 'male/female',
                            'family_index': 'numeric',
                            'infection_status': 'healthy/infected_undetected/infected_detected',
                            'employment_status': 'bool',
                            'profession_index': 'numeric',
                            'social': 'numeric',
                            'p_transport': 'bool'
                          }

        return node_structure
