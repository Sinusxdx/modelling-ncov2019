import string


class StructureCreator:
    @staticmethod
    def create_structure() -> dict:
        structure = dict()
        return structure


class NodeCreator(StructureCreator):
    @staticmethod
    def create_structure():
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


class HouseholdCreator(StructureCreator):
    @staticmethod
    def create_structure():
        household_structure = {
            'id': 'numeric',
            'members': 'index_list',
            'incomes': 'numeric',
            'location': 'string'
        }

        return household_structure


class ContainerCreator(StructureCreator):
    @staticmethod
    def create_structure():
        container_structure = {
            'households': {
                'household_id': 'household_structure'
            }, 'nodes': {
                'node_id': 'node_structure'
            }
        }

        return container_structure


class ProfessionsCreator(StructureCreator):
    @staticmethod
    def create_structure():
        professions_structure = dict()
        profession_structure = {
            'risk': 'numeric',
            'percentage_of_the_population': 'numeric'
        }
        for letter in string.ascii_uppercase[0:21]:
            professions_structure[letter] = profession_structure

        return professions_structure
