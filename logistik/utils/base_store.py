from abc import ABC
from typing import AbstractSet
from typing import Tuple
from typing import Any


class IDataStore(ABC):
    def init_done(self) -> bool:
        raise NotImplementedError()

    def get_scores_for(self, user_id: int) -> list:
        raise NotImplementedError()

    def all_score_items(self) -> AbstractSet[Tuple[Any, Any]]:
        raise NotImplementedError()

    def get_all_answers(self):
        raise NotImplementedError()

    def update_score(self, user_id: int, category_id: str, scores: Tuple[float, float, float, float]) -> None:
        raise NotImplementedError()
