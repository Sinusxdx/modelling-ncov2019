import random
import copy


class ContentCreator:
    def __init__(self, nodes):
        self._nodes = nodes

    def create_data(self):
        nodes_dict = {'people': list()}
        node_structure = {'id': None, 'age': None, 'gender': None, 'employment_status': None, 'social': None,
                          'p_transport': None, 'family_index': None, 'profession_index': None}

        for node in range(self._nodes):
            node_structure['id'] = node
            self.rand_values(node_structure)
            nodes_dict['people'].append(copy.copy(node_structure))

        return nodes_dict

    def rand_values(self, node_structure):
        self.rand_age(node_structure)
        self.rand_gender(node_structure)
        self.rand_employment_status(node_structure)
        self.rand_social_param(node_structure)
        self.rand_public_transport(node_structure)
        self.rand_family(node_structure)
        self.rand_profession(node_structure)

    def rand_family(self, node_structure):
        # TODO: Don't let child lives alone
        node_structure['family_index'] = random.randint(0, self._nodes // 3)

    @staticmethod
    def rand_age(node_structure):
        node_structure['age'] = random.randint(1, 80)

    @staticmethod
    def rand_gender(node_structure):
        node_structure['gender'] = random.choice([1, 2])

    @staticmethod
    def rand_profession(node_structure):
        if node_structure['employment_status']:
            # TODO: hardcoded 5 number ---> list with professions and probability
            node_structure['profession_index'] = random.randint(0, 5)
        else:
            node_structure['profession_index'] = None

    @staticmethod
    def rand_public_transport(node_structure):
        if node_structure['age'] >= 10:
            node_structure['p_transport'] = random.choice([True, False])
        else:
            node_structure['p_transport'] = False

    @staticmethod
    def rand_social_param(node_structure):
        node_structure['social'] = random.randint(0, 100)

    @staticmethod
    def rand_employment_status(node_structure):
        if 18 <= node_structure['age'] <= 65:
            random_num = random.random()
            node_structure['employment_status'] = True if random_num < 0.95 else False
        else:
            node_structure['employment_status'] = False
