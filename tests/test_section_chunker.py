from nexus.indexing.chunker import split_text
from nexus.indexing.section_chunker import merge_small_sections, split_into_sections


def test_sections_start_at_headings():
    sections = split_into_sections("Intro\n## First\ntext\n### Second\nmore")
    assert len(sections) == 3
    assert sections[1].startswith("## First")


def test_heading_inside_code_block_is_not_a_section():
    sections = split_into_sections("## Real\n```\n## a comment in code\n```\nafter")
    assert len(sections) == 1


def test_each_issue_comment_is_a_section():
    sections = split_into_sections("Body\nComment by alice:\nhello\nComment by bob:\nworld")
    assert len(sections) == 3


def test_small_sections_are_merged():
    merged = merge_small_sections(["a" * 300, "b" * 400, "c" * 100])
    assert len(merged) == 1
    assert "c" in merged[0]


def test_chunks_overlap_and_keep_their_size():
    pieces = split_text("x" * 650 + "y" * 650, 700, 100)
    assert len(pieces) > 1
    assert len(pieces[0]) == 700
    assert pieces[1][:100] == pieces[0][-100:]
