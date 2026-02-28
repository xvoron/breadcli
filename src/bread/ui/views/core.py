from typing import Generic, TypeVar

from textual.widget import Widget

from bread.app.controller import ReaderController
from bread.engines.core import LayoutEngine

T_Engine = TypeVar("T_Engine", bound=LayoutEngine)


class CoreReaderView(Widget, Generic[T_Engine]):
    def __init__(self, controller: ReaderController, engine: T_Engine, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.controller = controller
        self._engine = engine

    @property
    def engine(self) -> T_Engine:
        return self._engine
