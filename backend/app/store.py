"""In-memory dataset store.

For V1 we keep uploaded datasets in memory keyed by a dataset id. This is
deliberately simple (no persistence, no auth) and is the smallest thing that
works for a single-user demo. A real product would swap this for a database
or object storage.
"""
import hashlib
import threading
import uuid
from typing import Dict, Optional

from .frame import Dataframe


class DatasetStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._datasets: Dict[str, Dataframe] = {}

    def put(self, df: Dataframe) -> str:
        dataset_id = uuid.uuid4().hex
        with self._lock:
            self._datasets[dataset_id] = df
        return dataset_id

    def get(self, dataset_id: str) -> Optional[Dataframe]:
        with self._lock:
            return self._datasets.get(dataset_id)


store = DatasetStore()
