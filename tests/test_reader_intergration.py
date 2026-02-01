import pytest
from textual.strip import Strip
from textual.widgets import ProgressBar

from bread.app.controller import ReaderController
from bread.app.state import ReadMode
from bread.domain.ir import Block, BlockType, Span
from bread.domain.model import DocumentPosition
from bread.engines.linewrap import LineWrappingLayoutEngine
from bread.ui.app import BreadReaderApp


def block_for_text(text: str) -> list[Block]:
    return [Block(type=BlockType.P, inlines=(Span(text=text),))]


def make_controller_for_text(text: str):
    def get_blocks(*_, **__) -> list[Block]:
        return block_for_text(text)

    engine = LineWrappingLayoutEngine(get_blocks_for_spine=get_blocks)
    controller = ReaderController(
        initial_position=DocumentPosition(0, 0, 0, 0),
        engines={ReadMode.NORMAL: engine},
    )
    return controller


def strip_to_text(strip: Strip) -> str:
    # Convert to just the visible characters
    return "".join(segment.text for segment in strip._segments).rstrip()


@pytest.mark.asyncio
async def test_app_boots_and_renders_first_line():
    controller = make_controller_for_text(
        "Hello world. " * 30
    )
    app = BreadReaderApp(controller)


    async with app.run_test():
        reader = app.query_one("#reader")
        line0 = strip_to_text(reader.render_line(0))
        assert line0.strip() != ""


@pytest.mark.asyncio
async def test_scroll_down_changes_top_line_hint_and_content():
    # Many paragraphs => definitely many wrapped lines
    text = "\n\n".join(
        f"Paragraph {i}: " + ("word " * 40)
        for i in range(30)
    )

    controller = make_controller_for_text(text)
    app = BreadReaderApp(controller)

    async with app.run_test() as pilot:
        reader = app.query_one("#reader")

        # Ensure view/engine knows viewport
        controller.set_viewport(reader.size.width, reader.size.height)

        slice_obj = controller.current_slice()
        total = slice_obj.total_lines(controller.state)  # if your slice needs state
        assert total > reader.size.height, "Test requires content longer than viewport"

        before_hint = controller.state.top_line_hint
        before_line0 = strip_to_text(reader.render_line(0))

        await pilot.press("j")
        await pilot.pause()

        after_hint = controller.state.top_line_hint
        after_line0 = strip_to_text(reader.render_line(0))

        assert after_hint == before_hint + 1
        assert before_line0 != after_line0


@pytest.mark.asyncio
async def test_scroll_down_changes_rendered_content():
    text = "\n\n".join(f"Paragraph {i}: " + ("word " * 40) for i in range(30))
    controller = make_controller_for_text(
        text
    )
    app = BreadReaderApp(controller)

    async with app.run_test() as pilot:
        reader = app.query_one("#reader")

        before = strip_to_text(reader.render_line(0))
        await pilot.press("j")
        await pilot.pause()  # allow reactive updates

        after = strip_to_text(reader.render_line(0))
        assert before != after


@pytest.mark.asyncio
async def test_page_down_moves_further_than_single_line():
    controller = make_controller_for_text(
        "Start " + ("word " * 2000)
    )
    app = BreadReaderApp(controller)

    async with app.run_test() as pilot:
        reader = app.query_one("#reader")

        before = strip_to_text(reader.render_line(0))
        await pilot.press("f")      # page down
        await pilot.pause()

        after = strip_to_text(reader.render_line(0))
        assert before != after


@pytest.mark.asyncio
async def test_progress_updates_on_scroll():
    controller = make_controller_for_text(
        "Start " + ("word " * 2000)
    )
    app = BreadReaderApp(controller)

    async with app.run_test() as pilot:
        progress = app.query_one("#progress")
        assert isinstance(progress, ProgressBar)
        before = progress.progress

        await pilot.press("f")
        await pilot.pause()

        after = progress.progress
        assert after != before
