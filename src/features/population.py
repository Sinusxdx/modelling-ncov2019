from typing import List, Callable, Dict, Tuple, Any
import networkx as nx

Node_Type = Tuple[Any, Dict[str, Any]]


def generate(population_size: int, decorators: List[Tuple[Callable[..., Node_Type], Tuple[Any]]]) -> nx.MultiGraph:
    """

    :param population_size: size of a population to generate
    :param decorators: list of tuples, where each tuple consists of a callable (a function) and a tuple of
    additional arguments that should be passed to this function. The signature of the function should be similar to
    this one:
    ``` def function_name(node: Node_Type, *args: Any) -> Node_Type ```
    :return: an undirected graph of type nx.MultiGraph
    """

    # fake implementation
    p = 1/6
    graph = nx.fast_gnp_random_graph(population_size, p, directed=False)
    for node in graph.nodes(data=True):
        for decorator, args in decorators:
            node = decorator(node, *args)
    return graph
