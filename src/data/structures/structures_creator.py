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
                            'household_id': 'numeric',
                            'infection_status': 'healthy/infected_undetected/infected_detected',
                            'employment_status': 'bool',
                            'profession_index': 'numeric',
                            'social': 'numeric',
                            'p_transport': 'bool'
                        }

        return node_structure

    @staticmethod
    def create_household():
        household_structure = {
                                'id': 'numeric',
                                'members': 'index_list',
                                'incomes': 'numeric',
                                'location': 'string'
                            }

        return household_structure
