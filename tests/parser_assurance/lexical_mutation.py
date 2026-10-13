"""Independent private lexical protocol and bounded selected-fault controls."""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import reprlib
import stat
import sys
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import CodeType, FunctionType, MappingProxyType, ModuleType
from typing import Literal, Protocol, cast

from hypothesis import strategies as st

LexicalTrace = tuple[str, ...]
_MODES = ("normal", "yaml", "code", "query", "drawer")
_FIELDS = ("mode", "frontmatter_active", "properties_allowed", "returned_value")


class TraceProtocolError(ValueError):
    """Malformed recipe or observation, never evidence of a mutant detection."""


@dataclass(frozen=True)
class LexicalSnapshot:
    mode: str
    frontmatter_active: bool
    properties_allowed: bool
    returned_value: bool | None

    def __post_init__(self) -> None:
        if type(self.mode) is not str or self.mode not in _MODES:
            raise TraceProtocolError("invalid observed mode")
        if type(self.frontmatter_active) is not bool or type(self.properties_allowed) is not bool:
            raise TraceProtocolError("observed flags must be actual booleans")
        if self.returned_value is not None and type(self.returned_value) is not bool:
            raise TraceProtocolError("observed return must be None or an actual boolean")


@dataclass(frozen=True)
class _Transition:
    from_mode: str
    to_mode: str | None = None
    frontmatter: bool | None = None
    properties: bool | None = None
    returned: bool | None = None
    first_only: bool = False


# Independent, hand-authored expectations. Product values are never read here.
_TRANSITIONS = MappingProxyType(
    {
        "yaml_open": _Transition("normal", "yaml", first_only=True),
        "yaml_close": _Transition("yaml", "normal", False),
        "code_open": _Transition("normal", "code", False, False),
        "code_continue": _Transition("normal", "code", False, False),
        "code_payload": _Transition("code", frontmatter=False),
        "code_close": _Transition("code", "normal", False, True),
        "query_open": _Transition("normal", "query", False, False),
        "query_continue": _Transition("normal", "query", False, False),
        "query_payload": _Transition("query", frontmatter=False),
        "query_close": _Transition("query", "normal", False),
        "drawer_open": _Transition("normal", "drawer"),
        "drawer_payload": _Transition("drawer", returned=True),
        "drawer_end": _Transition("drawer", "normal", returned=False),
        "drawer_bullet": _Transition("drawer", "normal", returned=False),
        "structural": _Transition("normal", frontmatter=False, properties=True),
        "property": _Transition("normal", frontmatter=False),
        "plain_continue": _Transition("normal", frontmatter=False, properties=False),
        "pre_node_prose": _Transition("normal", frontmatter=False, first_only=True),
    }
)

_DISPATCH = MappingProxyType(
    {
        "yaml_open": ("begin_yaml_frontmatter", ()),
        "yaml_close": ("finish_yaml_frontmatter", ()),
        "code_open": ("begin_code_block", ()),
        "code_continue": (
            "observe_continuation",
            (("is_code_fence", True), ("is_query_begin", False)),
        ),
        "code_payload": ("consume_code_line", (("is_code_fence", False),)),
        "code_close": ("consume_code_line", (("is_code_fence", True),)),
        "query_open": ("begin_query_block", ()),
        "query_continue": (
            "observe_continuation",
            (("is_code_fence", False), ("is_query_begin", True)),
        ),
        "query_payload": ("consume_query_line", (("is_query_end", False),)),
        "query_close": ("consume_query_line", (("is_query_end", True),)),
        "drawer_open": ("begin_drawer", ()),
        "drawer_payload": ("consume_drawer_line", (("is_drawer_end", False), ("is_bullet", False))),
        "drawer_end": ("consume_drawer_line", (("is_drawer_end", True), ("is_bullet", False))),
        "drawer_bullet": ("consume_drawer_line", (("is_drawer_end", False), ("is_bullet", True))),
        "structural": ("observe_structural_node", ()),
        "property": ("observe_property", ()),
        "plain_continue": (
            "observe_continuation",
            (("is_code_fence", False), ("is_query_begin", False)),
        ),
        "pre_node_prose": ("observe_nonstructural_line_without_node", ()),
    }
)


def legal_actions(snapshot: LexicalSnapshot, index: int) -> tuple[str, ...]:
    return tuple(
        action
        for action, step in _TRANSITIONS.items()
        if step.from_mode == snapshot.mode and (not step.first_only or index == 0)
    )


def _model_step(snapshot: LexicalSnapshot, action: str, index: int) -> LexicalSnapshot:
    if type(action) is not str or action not in legal_actions(snapshot, index):
        raise TraceProtocolError("unknown action or illegal transition")
    step = _TRANSITIONS[action]
    return LexicalSnapshot(
        snapshot.mode if step.to_mode is None else step.to_mode,
        snapshot.frontmatter_active if step.frontmatter is None else step.frontmatter,
        snapshot.properties_allowed if step.properties is None else step.properties,
        step.returned,
    )


def model_trace(trace: LexicalTrace) -> tuple[LexicalSnapshot, ...]:
    if type(trace) is not tuple or not 1 <= len(trace) <= 8:
        raise TraceProtocolError("a trace must contain one through eight actions")
    result = [LexicalSnapshot("normal", True, True, None)]
    for index, action in enumerate(trace):
        result.append(_model_step(result[-1], action, index))
    return tuple(result)


def _reject_number(value: str) -> object:
    raise TraceProtocolError("numeric or nonfinite JSON form is not admitted")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TraceProtocolError("duplicate JSON key")
        result[key] = value
    return result


def admit_trace(data: bytes) -> LexicalTrace:
    if type(data) is not bytes or not 1 <= len(data) <= 512:
        raise TraceProtocolError("recipe must be one through 512 UTF-8 bytes")
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_float=_reject_number,
            parse_int=_reject_number,
            parse_constant=_reject_number,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise TraceProtocolError("invalid JSON encoding or shape") from error
    if type(value) is not dict or set(value) != {"schema", "actions"}:
        raise TraceProtocolError("recipe fields must be exactly schema and actions")
    if value["schema"] != "lexical_trace_v1" or type(value["actions"]) is not list:
        raise TraceProtocolError("invalid schema or actions type")
    trace = tuple(value["actions"])
    model_trace(trace)
    return trace


def canonical_trace(trace: LexicalTrace) -> bytes:
    model_trace(trace)
    data = json.dumps(
        {"schema": "lexical_trace_v1", "actions": trace},
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if len(data) > 512:
        raise TraceProtocolError("canonical recipe exceeds its byte ceiling")
    return data


class _ObservedFields(Protocol):
    mode: str
    frontmatter_active: bool
    properties_allowed: bool


def _snapshot(target: object, returned: object = None) -> LexicalSnapshot:
    fields = cast(_ObservedFields, target)
    return LexicalSnapshot(
        fields.mode,
        fields.frontmatter_active,
        fields.properties_allowed,
        cast(bool | None, returned),
    )


def observe_trace(
    factory: Callable[[], object],
    trace: LexicalTrace,
    *,
    budget: TraceBudget | None = None,
    phase: str = "baseline",
) -> tuple[LexicalSnapshot, ...]:
    model_trace(trace)  # Complete admission before construction or dispatch.
    counter = TraceBudget() if budget is None else budget
    counter.begin_trace(phase, trace)
    target = factory()
    counter.factory_completed += 1
    result = [_snapshot(target)]
    for index, action in enumerate(trace):
        method_name, keywords = _DISPATCH[action]
        counter.before_dispatch(index)
        returned = getattr(target, method_name)(**dict(keywords))
        counter.after_dispatch()
        if action.startswith("drawer_") and action != "drawer_open":
            if type(returned) is not bool:
                raise TraceProtocolError("drawer consumption must return an actual boolean")
        elif returned is not None:
            raise TraceProtocolError("non-drawer action must return None")
        result.append(_snapshot(target, returned))
    counter.trace_completed += 1
    return tuple(result)


class TraceMismatch(AssertionError):
    """First complete-prefix disagreement with explicit trace/action evidence."""

    def __init__(
        self,
        trace: LexicalTrace,
        snapshot_index: int,
        field: str,
        actual: LexicalSnapshot,
        expected: LexicalSnapshot,
    ) -> None:
        self.snapshot_index = snapshot_index
        self.action_index = None if snapshot_index == 0 else snapshot_index - 1
        self.action_name = "initial" if self.action_index is None else trace[self.action_index]
        self.field = field
        self.actual = actual
        self.expected = expected
        super().__init__(
            f"snapshot {snapshot_index}, action {self.action_name}, field {field} differs"
        )


def assert_trace(
    trace: LexicalTrace,
    actual: tuple[LexicalSnapshot, ...],
    expected: tuple[LexicalSnapshot, ...],
) -> None:
    model_trace(trace)
    if len(actual) != len(trace) + 1 or len(expected) != len(trace) + 1:
        raise TraceProtocolError("observation must include the initial state and every prefix")
    for index, (observed, wanted) in enumerate(zip(actual, expected, strict=True)):
        if type(observed) is not LexicalSnapshot or type(wanted) is not LexicalSnapshot:
            raise TraceProtocolError("observation has an invalid snapshot type")
        for field_name in _FIELDS:
            if getattr(observed, field_name) != getattr(wanted, field_name):
                raise TraceMismatch(trace, index, field_name, observed, wanted)


def replay_trace(
    factory: Callable[[], object],
    recipe: bytes,
    *,
    budget: TraceBudget | None = None,
) -> tuple[LexicalSnapshot, ...]:
    trace = admit_trace(recipe)
    counter = TraceBudget() if budget is None else budget
    actual = observe_trace(factory, trace, budget=counter)
    try:
        assert_trace(trace, actual, model_trace(trace))
    except TraceMismatch as mismatch:
        counter.save_first_failure(
            trace,
            mismatch.action_index,
            mismatch.action_name,
            mismatch.field,
            mismatch.actual,
            mismatch.expected,
        )
        raise
    return actual


MutationID = Literal["M1", "M2", "M3", "M4", "M5", "M6"]
MUTATION_IDS: tuple[MutationID, ...] = ("M1", "M2", "M3", "M4", "M5", "M6")
_CANONICAL_SOURCE = "1b14077d0294861859b4ce26aa4573589d3067b08a342467b6a1e9a9b209344b"
_SOURCE_METHODS = (
    "begin_yaml_frontmatter",
    "finish_yaml_frontmatter",
    "begin_code_block",
    "consume_code_line",
    "begin_query_block",
    "consume_query_line",
    "begin_drawer",
    "consume_drawer_line",
    "observe_structural_node",
    "observe_property",
    "observe_continuation",
    "observe_nonstructural_line_without_node",
)


class MutationAdmissionError(ValueError):
    """Invalid trusted source or edit; never a successful mutant detection."""


class CloneOwnershipError(RuntimeError):
    """A synthetic module entry is not positively owned by this context."""


class CloneAttributionError(RuntimeError):
    """A copy's executable code claims an inappropriate source identity."""


class MutationEvidenceError(AssertionError):
    """Missing, inconsistent or incorrectly located selected-fault evidence."""


class TraceBudgetExceeded(RuntimeError):
    """A proposed next operation exceeds this invocation's admitted budget."""


@dataclass(frozen=True)
class FirstFailure:
    trace: LexicalTrace
    recipe: str
    action_index: int | None
    action_name: str
    field: str
    actual: LexicalSnapshot
    expected: LexicalSnapshot

    def mismatch(self) -> TraceMismatch:
        index = 0 if self.action_index is None else self.action_index + 1
        return TraceMismatch(self.trace, index, self.field, self.actual, self.expected)


class TraceAccountingError(AssertionError):
    """An operation attempt must not be conflated with successful completion."""


@dataclass
class TraceBudget:
    compilations: int = 0
    completed_compilations: int = 0
    compilation_labels: list[str] = field(default_factory=list)
    trace_attempted: int = 0
    factory_completed: int = 0
    trace_completed: int = 0
    dispatch_attempted: int = 0
    dispatch_completed: int = 0
    baseline_attempted: int = 0
    mutant_attempted: int = 0
    generated_attempted: int = 0
    generated_recipes: list[str] = field(default_factory=list)
    first_failure: FirstFailure | None = None

    def reserve_compilation(self) -> None:
        if self.compilations >= 9:
            raise TraceBudgetExceeded("outer executable AST compilation ceiling exceeded")
        self.compilations += 1

    def begin_trace(self, phase: str, trace: LexicalTrace) -> None:
        if self.first_failure is not None:
            raise self.first_failure.mismatch()
        if phase not in ("baseline", "mutant", "generated"):
            raise TraceProtocolError("unknown trace accounting phase")
        count = getattr(self, f"{phase}_attempted")
        ceiling = {"baseline": 16, "mutant": 48, "generated": 48}[phase]
        if self.trace_attempted >= 112 or count >= ceiling:
            raise TraceBudgetExceeded("target trace admission ceiling exceeded")
        self.trace_attempted += 1
        setattr(self, f"{phase}_attempted", count + 1)
        if phase == "generated":
            self.generated_recipes.append(canonical_trace(trace).decode("utf-8"))

    def before_dispatch(self, index: int) -> None:
        if index >= 8 or self.dispatch_attempted >= 896:
            raise TraceBudgetExceeded("seam dispatch ceiling exceeded")
        self.dispatch_attempted += 1

    def after_dispatch(self) -> None:
        if self.dispatch_completed >= self.dispatch_attempted:
            raise TraceAccountingError("completion has no preceding dispatch attempt")
        self.dispatch_completed += 1

    def save_first_failure(
        self,
        trace: LexicalTrace,
        action_index: int | None,
        action_name: str,
        field: str,
        actual: LexicalSnapshot,
        expected: LexicalSnapshot,
    ) -> FirstFailure:
        if self.first_failure is not None:
            return self.first_failure
        recipe = canonical_trace(trace).decode("utf-8")
        if field not in _FIELDS:
            raise TraceProtocolError("unknown disagreement field")
        if action_index is None:
            if action_name != "initial":
                raise TraceProtocolError("initial failure must have the initial marker")
        elif type(action_index) is not int or not 0 <= action_index < len(trace):
            raise TraceProtocolError("failure action index outside its original trace")
        elif action_name != trace[action_index]:
            raise TraceProtocolError("failure action name does not match its trace")
        self.first_failure = FirstFailure(
            trace, recipe, action_index, action_name, field, actual, expected
        )
        return self.first_failure

    def accounting_gaps(self) -> tuple[str, ...]:
        """Inspect incomplete work without suppressing the diagnostic emission."""
        return tuple(
            stage
            for stage, attempted, completed in (
                ("factory", self.trace_attempted, self.factory_completed),
                ("trace", self.trace_attempted, self.trace_completed),
                ("dispatch", self.dispatch_attempted, self.dispatch_completed),
                ("compilation", self.compilations, self.completed_compilations),
            )
            if attempted != completed
        )

    def assert_balanced(self) -> None:
        if self.accounting_gaps():
            raise TraceAccountingError("attempted/completed operation accounting differs")


@dataclass(frozen=True)
class AdmittedSource:
    text: str
    raw_digest: str
    canonical_digest: str
    tree: ast.Module


def selected_source_path() -> Path:
    return Path(__file__).resolve().parents[2] / "src/logseq_matryca_parser/_lexical_state.py"


def read_selected_source() -> bytes:
    """The owner selects this tracked path; verify regular type and bounded bytes."""
    path = selected_source_path()
    if not stat.S_ISREG(path.lstat().st_mode):
        raise MutationAdmissionError("selected source is not a regular file")
    with path.open("rb") as stream:
        data = stream.read(16385)
    if not 1 <= len(data) <= 16384:
        raise MutationAdmissionError("selected source exceeds its byte ceiling")
    return data


def admit_source(source_bytes: bytes) -> AdmittedSource:
    if type(source_bytes) is not bytes or not 1 <= len(source_bytes) <= 16384:
        raise MutationAdmissionError("trusted source must be at most 16 KiB")
    try:
        text = source_bytes.decode("utf-8", errors="strict").replace("\r\n", "\n")
    except UnicodeDecodeError as error:
        raise MutationAdmissionError("trusted source is not UTF-8") from error
    if "\r" in text:
        raise MutationAdmissionError("bare CR in trusted Python source")
    canonical_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if canonical_digest != _CANONICAL_SOURCE:
        raise MutationAdmissionError("trusted canonical source hash mismatch")
    tree = ast.parse(text, filename="<s4-lexical-source-data>")
    imports = [
        (node.module, tuple(alias.name for alias in node.names))
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ]
    if imports != [
        ("__future__", ("annotations",)),
        ("dataclasses", ("dataclass",)),
        ("typing", ("Literal",)),
    ] or any(isinstance(node, ast.Import) for node in ast.walk(tree)):
        raise MutationAdmissionError("unexpected trusted import surface")
    return AdmittedSource(text, hashlib.sha256(source_bytes).hexdigest(), canonical_digest, tree)


@lru_cache(maxsize=1)
def _trusted_ast_dump() -> str:
    return ast.dump(admit_source(read_selected_source()).tree, include_attributes=False)


def _one[T](nodes: list[T], label: str) -> T:
    if len(nodes) != 1:
        raise MutationAdmissionError(f"{label} must match exactly once")
    return nodes[0]


def _method(tree: ast.Module, name: str) -> ast.FunctionDef:
    owner = _one(
        [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "_LexicalState"
        ],
        "selected class",
    )
    return _one(
        [node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name],
        "selected method",
    )


def _is_assignment(node: ast.AST, name: str, value: bool) -> bool:
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Attribute)
        and isinstance(node.targets[0].value, ast.Name)
        and node.targets[0].value.id == "self"
        and node.targets[0].attr == name
        and isinstance(node.value, ast.Constant)
        and type(node.value.value) is bool
        and node.value.value is value
    )


def _flag_assignment(name: str, value: bool) -> ast.Assign:
    return ast.Assign(
        targets=[
            ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr=name, ctx=ast.Store())
        ],
        value=ast.Constant(value=value),
    )


def _name_if(method: ast.FunctionDef, name: str) -> ast.If:
    return _one(
        [
            node
            for node in method.body
            if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == name
        ],
        "selected branch",
    )


def _edit_once(tree: ast.Module, mutation: MutationID, *, reverse: bool = False) -> None:
    if mutation not in MUTATION_IDS:
        raise MutationAdmissionError("unknown mutation ID")
    if mutation == "M1":
        branch = _name_if(_method(tree, "consume_code_line"), "is_code_fence")
        assignment = _one(
            [
                node
                for node in branch.body
                if _is_assignment(node, "properties_allowed", not reverse)
            ],
            "closing property assignment",
        )
        assert isinstance(assignment, ast.Assign)
        assignment.value = ast.copy_location(ast.Constant(value=reverse), assignment.value)
    elif mutation == "M2":
        branch = _name_if(_method(tree, "consume_query_line"), "is_query_end")
        if reverse:
            assignment = _one(
                [node for node in branch.body if _is_assignment(node, "properties_allowed", True)],
                "added query property assignment",
            )
            if branch.body[-1] is not assignment:
                raise MutationAdmissionError("query assignment is not in its catalog position")
            branch.body.remove(assignment)
        else:
            if any(
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Attribute) and target.attr == "properties_allowed"
                    for target in node.targets
                )
                for node in branch.body
            ):
                raise MutationAdmissionError("query branch already has a property assignment")
            branch.body.append(_flag_assignment("properties_allowed", True))
    elif mutation == "M3":
        method = _method(tree, "consume_drawer_line")
        branch = _one([node for node in method.body if isinstance(node, ast.If)], "drawer branch")
        expected = ast.And if reverse else ast.Or
        if not (
            isinstance(branch.test, ast.BoolOp)
            and isinstance(branch.test.op, expected)
            and [node.id for node in branch.test.values if isinstance(node, ast.Name)]
            == ["is_drawer_end", "is_bullet"]
            and len(branch.test.values) == 2
        ):
            raise MutationAdmissionError("drawer Boolean selector mismatch")
        branch.test.op = ast.Or() if reverse else ast.And()
    elif mutation == "M4":
        method = _method(tree, "observe_structural_node")
        if reverse:
            if len(method.body) != 1 or not _is_assignment(
                method.body[0], "frontmatter_active", False
            ):
                raise MutationAdmissionError("structural deletion shape mismatch")
            method.body.insert(1, _flag_assignment("properties_allowed", True))
        else:
            assignment = _one(
                [node for node in method.body if _is_assignment(node, "properties_allowed", True)],
                "structural property assignment",
            )
            method.body.remove(assignment)
    elif mutation == "M5":
        method = _method(tree, "observe_continuation")
        if reverse:
            branch = _one(
                [
                    node
                    for node in method.body
                    if isinstance(node, ast.If)
                    and isinstance(node.test, ast.UnaryOp)
                    and isinstance(node.test.op, ast.Not)
                    and isinstance(node.test.operand, ast.Name)
                    and node.test.operand.id == "is_query_begin"
                ],
                "negated query guard",
            )
            assert isinstance(branch.test, ast.UnaryOp)
            branch.test = branch.test.operand
        else:
            branch = _name_if(method, "is_query_begin")
            branch.test = ast.copy_location(
                ast.UnaryOp(op=ast.Not(), operand=branch.test), branch.test
            )
    else:
        method = _method(tree, "observe_nonstructural_line_without_node")
        assignment = _one(
            [node for node in method.body if _is_assignment(node, "frontmatter_active", reverse)],
            "prose frontmatter assignment",
        )
        assert isinstance(assignment, ast.Assign)
        assignment.value = ast.copy_location(ast.Constant(value=not reverse), assignment.value)


def apply_mutation(source_tree: ast.Module, mutation_id: MutationID) -> ast.Module:
    mutated = deepcopy(source_tree)
    _edit_once(mutated, mutation_id)
    if ast.dump(source_tree, include_attributes=False) != _trusted_ast_dump():
        raise MutationAdmissionError("original tree differs from the admitted trusted source")
    return ast.fix_missing_locations(mutated)


def validate_mutation(original: ast.Module, mutated: ast.Module, mutation_id: MutationID) -> None:
    if ast.dump(original, include_attributes=False) != _trusted_ast_dump():
        raise MutationAdmissionError("original tree is not the trusted baseline")
    restored = deepcopy(mutated)
    _edit_once(restored, mutation_id, reverse=True)
    if ast.dump(restored, include_attributes=False) != ast.dump(original, include_attributes=False):
        raise MutationAdmissionError("AST delta includes an unauthorized edit")


def variant_module_name(mutation_id: MutationID | None) -> str:
    if mutation_id is not None and mutation_id not in MUTATION_IDS:
        raise MutationAdmissionError("unknown mutation ID")
    return f"_parser_assurance_s4_lexical_{mutation_id or 'unmodified'}"


def _compile_copy(tree: ast.Module, label: str) -> CodeType:
    return compile(tree, label, "exec", dont_inherit=True)


def validate_copy_code(code: CodeType, label: str) -> None:
    if not (label.startswith("<") and label.endswith(">")):
        raise CloneAttributionError("copy label must be synthetic")
    if code.co_filename != label:
        raise CloneAttributionError("copy code filename is not its synthetic label")
    for constant in code.co_consts:
        if isinstance(constant, CodeType):
            validate_copy_code(constant, label)


@dataclasses.dataclass
class _DataclassCodeReference:
    """Obtain the active standard library's representation wrapper identity."""


_REPR_WRAPPER_CODES = (
    cast(FunctionType, _DataclassCodeReference.__repr__).__code__,
    cast(FunctionType, reprlib.recursive_repr()(lambda self: "")).__code__,
)


def validate_copy_module(module: ModuleType, label: str) -> None:
    if module.__file__ != label:
        raise CloneAttributionError("copy file label is not synthetic")
    factory = getattr(module, "_LexicalState", None)
    if not isinstance(factory, type):
        raise CloneAttributionError("copy has no selected class")
    for name in _SOURCE_METHODS:
        code = getattr(getattr(factory, name, None), "__code__", None)
        if not isinstance(code, CodeType):
            raise CloneAttributionError("copy is missing a source-derived method")
        validate_copy_code(code, label)
    for name in ("__init__", "__repr__", "__eq__"):
        method = getattr(factory, name, None)
        code = getattr(method, "__code__", None)
        if name == "__repr__" and any(code is known for known in _REPR_WRAPPER_CODES):
            if not isinstance(method, FunctionType) or not isinstance(code, CodeType):
                raise CloneAttributionError("invalid standard-library representation wrapper")
            closure = method.__closure__ or ()
            if len(closure) != len(code.co_freevars):
                raise CloneAttributionError("representation wrapper closure is incomplete")
            try:
                cells = dict(zip(code.co_freevars, closure, strict=True))
                wrapped = cells["user_function"].cell_contents
            except (AttributeError, KeyError, ValueError) as error:
                raise CloneAttributionError("representation wrapper has no captured target") from error
            if not isinstance(wrapped, FunctionType) or getattr(method, "__wrapped__", wrapped) is not wrapped:
                raise CloneAttributionError("representation wrapper metadata does not match its target")
            code = wrapped.__code__
        if (
            not isinstance(code, CodeType)
            or code.co_filename not in {"<string>", label}
        ):
            raise CloneAttributionError("dataclass code claims an inappropriate source identity")
        validate_copy_code(code, code.co_filename)


@contextmanager
def isolated_variant(
    source_bytes: bytes, mutation_id: MutationID | None, *, budget: TraceBudget
) -> Iterator[Callable[[], object]]:
    """Execute only admitted reviewed-source copies; this is not a sandbox."""
    name = variant_module_name(mutation_id)
    if name in sys.modules:
        raise CloneOwnershipError("synthetic module identity already exists")
    source = admit_source(source_bytes)
    tree = source.tree
    if mutation_id is not None:
        tree = apply_mutation(tree, mutation_id)
        validate_mutation(source.tree, tree, mutation_id)
    label = f"<s4-lexical-copy:{mutation_id or 'unmodified'}>"
    budget.reserve_compilation()
    code = _compile_copy(tree, label)
    validate_copy_code(code, label)
    budget.completed_compilations += 1
    budget.compilation_labels.append(label)
    if name in sys.modules:
        raise CloneOwnershipError("synthetic identity changed before registration")
    module = ModuleType(name)
    module.__file__ = label
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
        validate_copy_module(module, label)
        yield cast(Callable[[], object], module._LexicalState)
    finally:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        else:
            raise CloneOwnershipError("synthetic module ownership changed")


_WITNESSES = MappingProxyType(
    {
        "M1": frozenset({("A2", 3, "code_close", "properties_allowed")}),
        "M2": frozenset({("A3", 3, "query_close", "properties_allowed")}),
        "M3": frozenset({("A4", 3, "drawer_end", "mode"), ("A5", 2, "drawer_bullet", "mode")}),
        "M4": frozenset({("A6", 2, "structural", "properties_allowed")}),
        "M5": frozenset({("A7", 1, "query_continue", "mode")}),
        "M6": frozenset({("A8", 0, "pre_node_prose", "frontmatter_active")}),
    }
)
_MUTANT_FIELDS = MappingProxyType(
    {
        "M1": "properties_allowed",
        "M2": "properties_allowed",
        "M3": "mode",
        "M4": "properties_allowed",
        "M5": "mode",
        "M6": "frontmatter_active",
    }
)


@dataclass(frozen=True)
class MutationObservation:
    mutation_id: MutationID
    trace_id: str
    classification: Literal["DETECTED", "MATCH", "INVALID", "HARNESS_ERROR"]
    action_index: int | None
    action_name: str | None
    field: str | None
    required_witness_matched: bool


def classify_mutant(
    mutation_id: MutationID, trace_id: str, mismatch: TraceMismatch | None
) -> MutationObservation:
    if mutation_id not in MUTATION_IDS or trace_id not in {f"A{i}" for i in range(1, 9)}:
        raise MutationEvidenceError("unknown mutation or anchor identity")
    if mismatch is None:
        return MutationObservation(mutation_id, trace_id, "MATCH", None, None, None, False)
    if type(mismatch) is not TraceMismatch:
        raise MutationEvidenceError("only an own TraceMismatch is a detection candidate")
    coordinate = (trace_id, mismatch.action_index, mismatch.action_name, mismatch.field)
    status: Literal["DETECTED", "HARNESS_ERROR"] = (
        "DETECTED" if mismatch.field == _MUTANT_FIELDS[mutation_id] else "HARNESS_ERROR"
    )
    return MutationObservation(
        mutation_id,
        trace_id,
        status,
        mismatch.action_index,
        mismatch.action_name,
        mismatch.field,
        status == "DETECTED" and coordinate in _WITNESSES[mutation_id],
    )


def require_required_witnesses(rows: tuple[MutationObservation, ...]) -> None:
    expected_pairs = {(mutation, f"A{i}") for mutation in MUTATION_IDS for i in range(1, 9)}
    if len(rows) != 48 or {(row.mutation_id, row.trace_id) for row in rows} != expected_pairs:
        raise MutationEvidenceError("matrix must contain each of the 48 distinct selected rows")
    detected: set[str] = set()
    for row in rows:
        if row.classification not in ("MATCH", "DETECTED"):
            raise MutationEvidenceError("invalid or harness-error matrix row")
        coordinate = (row.trace_id, row.action_index, row.action_name, row.field)
        matched = row.classification == "DETECTED" and coordinate in _WITNESSES[row.mutation_id]
        if row.required_witness_matched is not matched:
            raise MutationEvidenceError("inconsistent required-witness evidence")
        if row.classification == "DETECTED" and row.field != _MUTANT_FIELDS[row.mutation_id]:
            raise MutationEvidenceError("unrelated field was credited as a kill")
        if matched:
            detected.add(row.mutation_id)
    if detected != set(MUTATION_IDS):
        raise MutationEvidenceError("one or more selected faults lacks its full required witness")


def lexical_traces() -> st.SearchStrategy[LexicalTrace]:
    """Draw only model-legal actions; never select from product observations."""

    @st.composite
    def traces(draw: st.DrawFn) -> LexicalTrace:
        length = draw(st.integers(min_value=1, max_value=8))
        snapshot = LexicalSnapshot("normal", True, True, None)
        result: list[str] = []
        for index in range(length):
            action = draw(st.sampled_from(legal_actions(snapshot, index)))
            result.append(action)
            snapshot = _model_step(snapshot, action, index)
        return tuple(result)

    return traces()


def summary_json(summary: Mapping[str, object]) -> str:
    text = json.dumps(
        summary, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )
    if len(text.encode("utf-8")) > 65536:
        raise TraceBudgetExceeded("structured summary exceeds 64 KiB")
    return text
