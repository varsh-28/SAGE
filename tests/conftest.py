import pytest

from opsgraph.generate_data import ensure
from opsgraph.graph_builder import build_graph


@pytest.fixture(scope="session")
def dataset():
    return ensure()


@pytest.fixture(scope="session")
def graph(dataset):
    return build_graph(dataset)
