from collections import deque
from typing import Dict, Optional

import numpy as np

try:
    import torch
except ImportError:
    torch = None


def _to_numpy(value):
    type_ = type(value)

    if type_ in [float, int]:
        return np.array(value).ravel()

    if isinstance(value, np.number):
        return np.array(value.item()).ravel()

    if type_ == list:
        return np.array(value).ravel()

    if type_ == np.ndarray:
        return value.ravel()

    if torch is not None:
        if type_ == torch.nn.parameter.Parameter:
            return value.data.cpu().numpy().ravel()
        if type_ == torch.Tensor:
            return value.data.cpu().numpy().ravel()

    assert False, f"Unknown type {type_}"


class Indicator:
    def __init__(self, *, name: str, is_print: bool):
        self.is_print = is_print
        self.name = name

    def clear(self):
        pass

    def is_empty(self) -> bool:
        raise NotImplementedError()

    def to_dict(self) -> Dict:
        return dict(class_name=self.__class__.__name__,
                    name=self.name,
                    is_print=self.is_print)

    def collect_value(self, value):
        raise NotImplementedError()

    def get_mean(self) -> Optional[float]:
        return None

    def get_histogram(self):
        return None

    @property
    def mean_key(self):
        return f'{self.name}'

    def get_index_mean(self):
        return None, None


class Queue(Indicator):
    def __init__(self, name: str, queue_size=10, is_print=False):
        super().__init__(name=name, is_print=is_print)
        self._values = deque(maxlen=queue_size)

    def collect_value(self, value):
        self._values.append(_to_numpy(value))

    def to_dict(self) -> Dict:
        res = super().to_dict().copy()
        res.update({'queue_size': self._values.maxlen})
        return res

    def is_empty(self) -> bool:
        return len(self._values) == 0

    def get_mean(self) -> float:
        return float(np.mean(self._values))

    def get_histogram(self):
        return self._values

    @property
    def mean_key(self):
        return f'{self.name}.mean'


class _Collection(Indicator):
    def __init__(self, name: str, is_print=False):
        super().__init__(name=name, is_print=is_print)
        self._values = []

    def collect_value(self, value):
        self._values.append(_to_numpy(value))

    def clear(self):
        self._values = []

    def is_empty(self) -> bool:
        return len(self._values) == 0

    def get_mean(self) -> float:
        return float(np.mean(self._values))

    def get_histogram(self):
        return self._values


class Histogram(_Collection):
    @property
    def mean_key(self):
        return f'{self.name}.mean'


class Scalar(_Collection):
    def get_histogram(self):
        return None


class _IndexedCollection(Indicator):
    def __init__(self, name: str):
        super().__init__(name=name, is_print=False)
        self._values = []
        self._indexes = []

    def clear(self):
        self._values = []
        self._indexes = []

    def collect_value(self, value):
        if type(value) == tuple:
            assert len(value) == 2
            if type(value[0]) == int:
                self._indexes.append(value[0])
                self._values.append(value[1])
            else:
                assert type(value[0]) == list
                assert len(value[0]) == len(value[1])
                self._indexes += value[0]
                self._values += value[1]
        else:
            assert type(value) == list
            self._indexes += [v[0] for v in value]
            self._values += [v[1] for v in value]

    def is_empty(self) -> bool:
        return len(self._values) == 0

    def get_mean(self) -> float:
        return float(np.mean(self._values))

    def get_index_mean(self):
        summary = {}
        for ind, values in zip(self._indexes, self._values):
            if ind not in summary:
                summary[ind] = []
            summary[ind].append(values)

        indexes = []
        means = []
        for ind, values in summary.items():
            indexes.append(ind)
            means.append(float(np.mean(values)))

        return indexes, means


class IndexedScalar(_IndexedCollection):
    def get_histogram(self):
        return None
