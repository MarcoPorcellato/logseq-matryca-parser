"""Independent finite semantic anchors and parser-free oracle calibration."""

from __future__ import annotations

import pytest

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import serialize_logseq_page
from tests.parser_assurance.invariants import assert_tree_invariants
from tests.parser_assurance.projection import IdentityPolicy, project_page
from tests.parser_assurance.semantic_anchors import ANCHORS, Anchor, assert_anchor, validate_anchor


def _hand_constructed_baselines() -> tuple[LogseqPage, ...]:
    """Build literal observations without reading expected facts or parsing."""
    return (
        LogseqPage(
            title="s1-nested-crlf",
            raw_content=(
                "- TODO [#A] root [[Body]]\r\n"
                "  zeta:: kept\r\n"
                "  alpha:: [[Property]]\r\n"
                "  id:: 11111111-1111-1111-1111-111111111111\r\n"
                "  continuation 東京\r\n"
                "  - TODO [#B] child\r\n"
                "    beta:: child-value"
            ),
            properties={},
            properties_order=[],
            refs=["Body", "Property", "A", "B"],
            root_nodes=[
                LogseqNode(
                    uuid="calibration-a1-root",
                    source_uuid="11111111-1111-1111-1111-111111111111",
                    synthetic_id=False,
                    content="TODO [#A] root [[Body]]\n  continuation 東京",
                    indent_level=0,
                    properties={
                        "zeta": "kept",
                        "alpha": "[[Property]]",
                        "id": "11111111-1111-1111-1111-111111111111",
                    },
                    properties_order=["zeta", "alpha", "id"],
                    wikilinks=["Body", "Property"],
                    tags=["A"],
                    refs=["Body", "Property", "A"],
                    task_status="TODO",
                    task_priority="A",
                    line_start=1,
                    line_end=5,
                    path=["calibration-a1-root"],
                    outline_path=[1],
                    children=[
                        LogseqNode(
                            uuid="calibration-a1-child",
                            source_uuid=None,
                            synthetic_id=True,
                            content="TODO [#B] child",
                            indent_level=1,
                            properties={"beta": "child-value"},
                            properties_order=["beta"],
                            wikilinks=[],
                            tags=["B"],
                            refs=["B"],
                            task_status="TODO",
                            task_priority="B",
                            parent_id="calibration-a1-root",
                            line_start=6,
                            line_end=7,
                            path=["calibration-a1-root", "calibration-a1-child"],
                            outline_path=[1, 1],
                        )
                    ],
                )
            ],
        ),
        LogseqPage(
            title="s1-equal-content",
            raw_content=(
                "- TODO repeated [[Shared]]\n"
                "  id:: 11111111-1111-1111-1111-111111111111\n"
                "  zeta:: kept\n"
                "- TODO repeated [[Shared]]\n"
                "  zeta:: kept\n"
                "  id:: 22222222-2222-2222-2222-222222222222\n"
            ),
            properties={},
            properties_order=[],
            refs=["Shared"],
            root_nodes=[
                LogseqNode(
                    uuid="calibration-a2-first",
                    source_uuid="11111111-1111-1111-1111-111111111111",
                    synthetic_id=False,
                    content="TODO repeated [[Shared]]",
                    indent_level=0,
                    properties={
                        "id": "11111111-1111-1111-1111-111111111111",
                        "zeta": "kept",
                    },
                    properties_order=["id", "zeta"],
                    wikilinks=["Shared"],
                    tags=[],
                    refs=["Shared"],
                    task_status="TODO",
                    task_priority=None,
                    line_start=1,
                    line_end=3,
                    path=["calibration-a2-first"],
                    outline_path=[1],
                ),
                LogseqNode(
                    uuid="calibration-a2-second",
                    source_uuid="22222222-2222-2222-2222-222222222222",
                    synthetic_id=False,
                    content="TODO repeated [[Shared]]",
                    indent_level=0,
                    properties={
                        "zeta": "kept",
                        "id": "22222222-2222-2222-2222-222222222222",
                    },
                    properties_order=["zeta", "id"],
                    wikilinks=["Shared"],
                    tags=[],
                    refs=["Shared"],
                    task_status="TODO",
                    task_priority=None,
                    left_id="calibration-a2-first",
                    line_start=4,
                    line_end=6,
                    path=["calibration-a2-second"],
                    outline_path=[2],
                ),
            ],
        ),
        LogseqPage(
            title="s1-fenced-native",
            raw_content=(
                "- TODO [[Visible]]\n"
                "  id:: 11111111-1111-1111-1111-111111111111\n"
                "  zeta:: kept\n"
                "  alpha:: plain\n"
                "  ```\n"
                "  id:: 22222222-2222-2222-2222-222222222222\n"
                "  zeta:: [[Hidden]] #hidden\n"
                "  ```\n"
                "  [[Visible]]\n"
            ),
            properties={},
            properties_order=[],
            refs=["Visible"],
            root_nodes=[
                LogseqNode(
                    uuid="calibration-a3-root",
                    source_uuid="11111111-1111-1111-1111-111111111111",
                    synthetic_id=False,
                    content=(
                        "TODO [[Visible]]\n"
                        "  ```\n"
                        "  id:: 22222222-2222-2222-2222-222222222222\n"
                        "  zeta:: [[Hidden]] #hidden\n"
                        "  ```\n"
                        "  [[Visible]]"
                    ),
                    indent_level=0,
                    properties={
                        "id": "11111111-1111-1111-1111-111111111111",
                        "zeta": "kept",
                        "alpha": "plain",
                    },
                    properties_order=["id", "zeta", "alpha"],
                    wikilinks=["Visible", "Visible"],
                    tags=[],
                    refs=["Visible"],
                    task_status="TODO",
                    task_priority=None,
                    line_start=1,
                    line_end=9,
                    path=["calibration-a3-root"],
                    outline_path=[1],
                )
            ],
        ),
        LogseqPage(
            title="S1 metadata",
            raw_content=(
                "title:: S1 metadata\r\n"
                "alias:: Board\r\n"
                "related:: [[Alpha]] and [[Beta]]"
            ),
            properties={
                "title": "S1 metadata",
                "alias": "Board",
                "related": "[[Alpha]] and [[Beta]]",
            },
            properties_order=["title", "alias", "related"],
            refs=["Board", "Alpha", "Beta"],
            root_nodes=[],
        ),
    )


def test_anchor_literals_obey_declared_bounds() -> None:
    assert len(ANCHORS) == 4
    assert len({anchor.case_id for anchor in ANCHORS}) == len(ANCHORS)
    for anchor in ANCHORS:
        validate_anchor(anchor)


@pytest.mark.parametrize("anchor_index", range(4), ids=lambda index: ANCHORS[index].case_id)
def test_anchor_oracle_accepts_hand_constructed_baselines(anchor_index: int) -> None:
    anchor: Anchor = ANCHORS[anchor_index]
    assert_anchor(_hand_constructed_baselines()[anchor_index], anchor)


@pytest.mark.parametrize(
    ("anchor_index", "scope", "field", "value", "expected_message"),
    (
        (0, "node", "properties_order", ["alpha", "zeta", "id"], "anchor.node.properties_order"),
        (3, "page", "properties_order", ["alias", "title", "related"], "anchor.page.properties_order"),
        (0, "node", "source_uuid", "22222222-2222-2222-2222-222222222222", "anchor.node.source_uuid"),
        (0, "node", "synthetic_id", True, "anchor.node.synthetic_id"),
    ),
    ids=("node-property-order", "page-property-order", "native-id", "synthetic-flag"),
)
def test_anchor_oracle_rejects_selected_observation_corruption(
    anchor_index: int, scope: str, field: str, value: object, expected_message: str
) -> None:
    anchor = ANCHORS[anchor_index]
    baseline = _hand_constructed_baselines()[anchor_index]
    assert_anchor(baseline, anchor)
    if scope == "page":
        corrupted = baseline.model_copy(update={field: value})
    else:
        root = baseline.root_nodes[0].model_copy(update={field: value})
        corrupted = baseline.model_copy(update={"root_nodes": [root, *baseline.root_nodes[1:]]})
    with pytest.raises(AssertionError) as exc:
        assert_anchor(corrupted, anchor)
    assert str(exc.value) == expected_message


@pytest.mark.parametrize("anchor", ANCHORS, ids=lambda anchor: anchor.case_id)
def test_parser_semantic_anchor_independent_replay_and_roundtrip(anchor: Anchor) -> None:
    parsed = StackMachineParser(tab_size=2).parse(anchor.source, page_title=anchor.input_title)
    assert_anchor(parsed, anchor)

    replay = StackMachineParser(tab_size=2).parse(anchor.source, page_title=anchor.input_title)
    assert_anchor(replay, anchor)
    assert project_page(parsed, profile="exact_parse_v1") == project_page(
        replay, profile="exact_parse_v1"
    )

    if anchor.roundtrip:
        serialized = serialize_logseq_page(parsed, tab_size=2)
        reparsed = StackMachineParser(tab_size=2).parse(serialized, page_title=parsed.title)
        assert_tree_invariants(reparsed)
        identity_policy = IdentityPolicy(
            synthetic_uuid="recomputed",
            source_uuid="preserve",
            relations="outline_paths",
        )
        assert project_page(
            parsed, profile="semantic_roundtrip_v1", identity_policy=identity_policy
        ) == project_page(
            reparsed, profile="semantic_roundtrip_v1", identity_policy=identity_policy
        )
