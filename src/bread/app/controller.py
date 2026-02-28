from threading import Thread
from typing import cast

from bread.app.commands import Command, ToggleMode
from bread.app.state import ReaderState, ReadMode
from bread.domain.model import DocumentPosition
from bread.engines.core import LayoutEngine
from bread.engines.linewrap import LineWrappingLayoutEngine
from bread.engines.rsvp import RSVPLayoutEngine


class ReaderController:
    def __init__(
        self,
        initial_position: DocumentPosition,
        engines: dict[ReadMode, LayoutEngine],
        spine_count: int,
    ) -> None:
        self.state = ReaderState(
            position=initial_position,
            mode = ReadMode.NORMAL
        )
        self.engines = engines
        self.spine_count = spine_count

        self.viewport_width = 80
        self.viewport_height = 24
        self._spines_size_per_mode: dict[ReadMode, list[int]] = {}

        for engine in self.engines.values():
            engine.set_spine_count(spine_count)
            engine.set_viewport(self.viewport_width, self.viewport_height)

        # Prime the normal engine so the initial position is honoured on first render.
        self.engines[ReadMode.NORMAL].seek_to(initial_position)
        
        # Precompute global progress in background for smooth mode toggling
        self._precompute_global_totals()

    @property
    def normal_engine(self) -> LineWrappingLayoutEngine:
        return cast(LineWrappingLayoutEngine, self.engines[ReadMode.NORMAL])

    @property
    def rsvp_engine(self) -> RSVPLayoutEngine:
        return cast(RSVPLayoutEngine, self.engines[ReadMode.RSVP])

    def set_viewport(self, width: int, height: int) -> None:
        self.viewport_width = max(20, width)
        self.viewport_height = max(1, height)

        for engine in self.engines.values():
            engine.set_viewport(width, height)

        if (
            self.state.mode == ReadMode.NORMAL
            and ReadMode.NORMAL in self._spines_size_per_mode
        ):
            # Normal mode layout may change with viewport width, so invalidate progress cache.
            del self._spines_size_per_mode[ReadMode.NORMAL]

    def dispatch(self, cmd: Command) -> None:
        if isinstance(cmd, ToggleMode):
            self._toggle_mode()
            return

        engine = self.engines[self.state.mode]
        old_spine = self.state.position.spine

        new_state = engine.apply(self.state, cmd)
        new_state.position = new_state.position.clamp_non_negative()

        if new_state.position.spine != old_spine:
            actual_pos = engine.seek_to(new_state.position)
            new_state.position = actual_pos

        self.state = new_state

    def _toggle_mode(self) -> None:
        self.state.playing = False
        # Ask the OUTGOING engine for its true current position.
        # state.position may be stale (e.g. never scrolled since init or last seek).
        outgoing_pos = self.engines[self.state.mode].current_position(self.state)
        new_mode = ReadMode.RSVP if self.state.mode == ReadMode.NORMAL else ReadMode.NORMAL
        self.state.position = self.engines[new_mode].seek_to(outgoing_pos)
        self.state.mode = new_mode

    def _compute_spine_size(self, spine_index: int) -> int:
        """Compute the total number of tokens/blocks in the given spine across all engines.

        This is used for global progress calculation and mode toggling.
        """
        tmp_state = ReaderState(
            position=DocumentPosition(spine=spine_index, block=0, span=0, offset=0),
            mode=self.state.mode,
        )

        if self.state.mode == ReadMode.NORMAL:
            return self.normal_engine.get_total_wrapped_lines(tmp_state)
        elif self.state.mode == ReadMode.RSVP:
            self.rsvp_engine._ensure_tokens(spine_index)
            return len(self.rsvp_engine._cache_tokens)
        else:
            raise ValueError(f"Unknown mode: {self.state.mode}")

    def get_local_progress(self) -> float:
        """Fast progress within current spine only."""
        if self.state.mode == ReadMode.NORMAL:
            tmp_state = ReaderState(
                position=self.state.position,
                mode=ReadMode.NORMAL,
            )
            total = self.normal_engine.get_total_wrapped_lines(tmp_state)
            current = self.normal_engine.top_line
        elif self.state.mode == ReadMode.RSVP:
            self.rsvp_engine._ensure_tokens(self.state.position.spine)
            total = len(self.rsvp_engine._cache_tokens)
            current = self.rsvp_engine._token_idx_for(self.state)
        else:
            raise ValueError(f"Unknown mode: {self.state.mode}")

        if total == 0:
            return 0.0
        return min(1.0, current / total)

    def get_global_progress(self) -> float:
        """Global progress across all spines.

        Falls back to local progress if global totals not computed yet.
        """
        # If global totals not cached for this mode, use local progress
        if self.state.mode not in self._spines_size_per_mode:
            return self.get_local_progress()

        spine_sizes = self._spines_size_per_mode[self.state.mode]
        total = sum(spine_sizes)

        if total == 0:
            return 0.0

        # Sum up all units before current spine
        units_before = sum(
            spine_sizes[i]
            for i in range(self.state.position.spine)
        )

        # Get current position within spine
        if self.state.mode == ReadMode.NORMAL:
            current_unit = self.normal_engine.top_line
        elif self.state.mode == ReadMode.RSVP:
            self.rsvp_engine._ensure_tokens(self.state.position.spine)
            current_unit = self.rsvp_engine._token_idx_for(self.state)
        else:
            raise ValueError(f"Unknown mode: {self.state.mode}")

        return min(1.0, (units_before + current_unit) / total)

    def get_spine_info(self) -> str:
        return f"Chapter {self.state.position.spine + 1} / {self.spine_count}"

    def _precompute_global_totals(self) -> None:
        """Precompute global totals for both modes in background thread.

        This prevents lag when toggling modes for the first time.
        """
        def compute():
            # Precompute for both modes
            for mode in [ReadMode.NORMAL, ReadMode.RSVP]:
                if mode not in self._spines_size_per_mode:
                    # Create a temporary state for computing
                    sizes = []
                    for i in range(self.spine_count):
                        tmp_state = ReaderState(
                            position=DocumentPosition(spine=i, block=0, span=0, offset=0),
                            mode=mode,
                        )
                        if mode == ReadMode.NORMAL:
                            size = self.normal_engine.get_total_wrapped_lines(tmp_state)
                        else:  # RSVP
                            self.rsvp_engine._ensure_tokens(i)
                            size = len(self.rsvp_engine._cache_tokens)
                        sizes.append(size)

                    self._spines_size_per_mode[mode] = sizes

        thread = Thread(target=compute, daemon=True, name="precompute-progress")
        thread.start()
