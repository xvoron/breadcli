
import re

from rich.style import Style
from rich.text import Text
from textual.events import Resize
from textual.geometry import Size
from textual.message import Message
from textual.widget import Widget

from bread.app.commands import RSVPNext
from bread.app.controller import ReaderController


def orp_index(core_word: str) -> int:
    n = len(core_word)
    if n <= 1:
        return 0
    if n <= 5:
        return 1
    if n <= 9:
        return 2
    if n <= 13:
        return 3
    return 4


class RSVPReaderViewWidget(Widget):
    COMPONENT_CLASSES = {"pivot"}

    DEFAULT_CSS = """
    RSVPReaderViewWidget {
        width: 100%;
        height: 100%;
        background: $background;
        color: $foreground;
    }

    RSVPReaderViewWidget .pivot {
        color: $accent;
        text-style: bold;
    }
    """

    class Ticked(Message):
        pass

    def __init__(self, controller: ReaderController, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.controller = controller
        self._timer = None

        self.virtual_size = Size(1, 1)

    def on_mount(self):
        self._timer = self.set_interval(self._interval_secondes(), self._tick, pause=False)
        self.refresh()

    def on_resize(self, _: Resize) -> None:
        self.refresh()

    def _interval_secondes(self) -> float:
        return max(60 / max(1, self.controller.state.wpm), 0.03)

    def _retime(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self._timer = self.set_interval(
            self._interval_secondes(), self._tick, pause=False
        )

    def _tick(self) -> None:
        if not self.controller.state.playing:
            return
        self.controller.dispatch(RSVPNext(delta=1))
        self.post_message(self.Ticked())
        self.refresh()

    def sync_from_state(self) -> None:
        self._retime()
        self.refresh()

    def render(self) -> Text:
        engine = self.controller.current_slice()
        word = engine.current_token(self.controller.state)

        # ORP alignment: align pivot to center column
        core = core_for_orp(word)
        pivot_i = orp_index(core)

        # Find pivot index in the original token (with punctuation)
        # MVP: approximate by searching through letters
        letters_seen = 0
        pivot_in_token = 0
        for i, ch in enumerate(word):
            if re.match(r"[^\W_]", ch, flags=re.UNICODE):
                if letters_seen == pivot_i:
                    pivot_in_token = i
                    break
                letters_seen += 1

        left = word[:pivot_in_token]
        pivot = word[pivot_in_token:pivot_in_token + 1] if word else ""
        right = word[pivot_in_token + 1:] if word else ""

        width = max(self.content_size.width, 1)
        height = max(self.content_size.height, 1)

        anchor_col = width // 2
        pad_left = max(anchor_col - len(left), 0)
        pad_top = max((height // 2), 0)

        text = Text("\n" * pad_top)
        text.append(" " * pad_left)
        text.append(left)
        text.append(
            pivot,
            style=Style(
                color=self.get_component_rich_style("pivot").color or "red",
                bold=True,
            ),
        )
        text.append(right)
        return text

def core_for_orp(token: str) -> str:
    return re.sub(r"[^\w’']+", "", token, flags=re.UNICODE).replace("_", "")
