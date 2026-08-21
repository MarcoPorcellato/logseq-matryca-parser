from logseq_matryca_parser._lexical_state import _LexicalState


def test_yaml_frontmatter_close_disables_page_frontmatter() -> None:
    state = _LexicalState()
    assert state.frontmatter_active is True
    assert state.properties_allowed is True

    state.begin_yaml_frontmatter()
    assert state.mode == "yaml"

    state.finish_yaml_frontmatter()
    assert state.mode == "normal"
    assert state.frontmatter_active is False


def test_code_and_query_closures_restore_existing_eligibility() -> None:
    state = _LexicalState()
    state.begin_code_block()
    state.consume_code_line(is_code_fence=True)
    assert state.mode == "normal"
    assert state.properties_allowed is True

    state.begin_query_block()
    state.consume_query_line(is_query_end=True)
    assert state.mode == "normal"
    assert state.frontmatter_active is False


def test_drawer_bullet_returns_to_normal_processing() -> None:
    state = _LexicalState()
    state.begin_drawer()
    assert state.mode == "drawer"

    assert state.consume_drawer_line(is_drawer_end=False, is_bullet=True) is False
    assert state.mode == "normal"


def test_structural_property_and_continuation_events_match_current_flags() -> None:
    state = _LexicalState()
    state.observe_structural_node()
    assert state.frontmatter_active is False
    assert state.properties_allowed is True

    state.observe_continuation(is_code_fence=True, is_query_begin=False)
    assert state.mode == "code"
    assert state.properties_allowed is False
