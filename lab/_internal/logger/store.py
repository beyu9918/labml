from pathlib import PurePath
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .internal import LoggerInternal
from .. import util
from .artifacts import Artifact
from .indicators import Indicator, Scalar
from .writers import Writer


class Store:
    artifacts: Dict[str, Artifact]
    indicators: Dict[str, Indicator]

    def __init__(self, logger: 'LoggerInternal'):
        self.values = {}
        # self.queues = {}
        # self.histograms = {}
        # self.pairs: Dict[str, List[Tuple[int, int]]] = {}
        # self.scalars = {}
        self.__logger = logger
        self.indicators = {}
        self.artifacts = {}
        self.__indicators_file = None
        self.__artifacts_file = None

    def save_indicators(self, file: PurePath):
        self.__indicators_file = file

        indicators = {k: ind.to_dict() for k, ind in self.indicators.items()}
        with open(str(file), "w") as file:
            file.write(util.yaml_dump(indicators))

    def save_artifactors(self, file: PurePath):
        self.__artifacts_file = file

        artifacts = {k: art.to_dict() for k, art in self.artifacts.items()}
        with open(str(file), "w") as file:
            file.write(util.yaml_dump(artifacts))

    def __assert_name(self, name: str):
        assert name not in self.indicators, f"{name} already used"
        assert name not in self.artifacts, f"{name} already used"

    def add_indicator(self, indicator: Indicator):
        self.__assert_name(indicator.name)
        self.indicators[indicator.name] = indicator
        indicator.clear()

        if self.__indicators_file is not None:
            self.save_indicators(self.__indicators_file)

    def add_artifact(self, artifact: Artifact):
        self.__assert_name(artifact.name)
        self.artifacts[artifact.name] = artifact
        artifact.clear()

        if self.__artifacts_file is not None:
            self.save_artifactors(self.__artifacts_file)

    def _store_kv(self, k, v):
        if k not in self.indicators and k not in self.artifacts:
            self.__logger.add_indicator(Scalar(k, True))

        if k in self.artifacts:
            self.artifacts[k].collect_value(None, v)
        else:
            self.indicators[k].collect_value(v)

    def _store_kvs(self, **kwargs):
        for k, v in kwargs.items():
            self._store_kv(k, v)

    def store(self, *args, **kwargs):
        """
        ### Stores a value in the logger.

        This may be added to a queue, a list or stored as
        a TensorBoard histogram depending on the
        type of the indicator.
        """
        assert len(args) <= 2

        if len(args) == 0:
            self._store_kvs(**kwargs)
        elif len(args) == 1:
            assert not kwargs
            assert isinstance(args[0], dict)
            self._store_kvs(**args[0])
        elif len(args) == 2:
            assert not kwargs
            assert isinstance(args[0], str)
            self._store_kv(args[0], args[1])

    def clear(self):
        for k, v in self.indicators.items():
            v.clear()
        for k, v in self.artifacts.items():
            v.clear()

    def write(self, writer: Writer, global_step):
        return writer.write(global_step=global_step,
                            indicators=self.indicators,
                            artifacts=self.artifacts)