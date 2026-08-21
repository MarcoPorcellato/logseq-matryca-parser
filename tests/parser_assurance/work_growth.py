"""Deterministic, test-only parser work-growth laboratory.

This module counts Python-owned parser operations through a test-only subclass.
It is not a profiler, benchmark, runtime API, or performance claim.  Its timing
and resident-memory observations are labelled diagnostics only; deterministic
operation counts remain the acceptance signal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from typing import Any, Final, Literal

try:  # pragma: no cover - exercised on platforms without the Unix-only module.
    import resource
except ImportError:  # Windows has no resource module; RSS is diagnostic only.
    resource = None  # type: ignore[assignment]

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import serialize_logseq_page
from tests.parser_assurance.invariants import assert_tree_invariants, walk_nodes
from tests.parser_assurance.projection import IdentityPolicy, project_page

WORK_MODEL_SCHEMA_VERSION: Final = 1
WORK_GENERATOR_VERSION: Final = 1
FIXED_SEED: Final = 104
SIZE_STEPS: Final = (8, 16, 32, 64)
MAX_CASE_BYTES: Final = 32_768
DEFAULT_TIMEOUT_SECONDS: Final = 3.0
LINEAR_RATIO_NUMERATOR: Final = 5
LINEAR_RATIO_DENOMINATOR: Final = 2

WorkFamily = Literal["flat-blocks", "deep-chain", "fenced-continuations", "properties"]
GrowthPolicy = Literal["linear-v1", "immutable-ancestor-rebuild-v1"]
Classification = Literal[
    "parsed",
    "invariant_failure",
    "semantic_roundtrip_failure",
    "unexpected_exception",
    "timeout",
    "runner_failure",
]

IDENTITY_POLICY: Final[IdentityPolicy] = {
    "synthetic_uuid": "recomputed",
    "source_uuid": "absent",
    "relations": "outline_paths",
}


@dataclass(frozen=True)
class WorkCase:
    """One bounded, project-authored input at a declared size."""

    case_id: str
    family: WorkFamily
    seed: int
    size: int
    growth_policy: GrowthPolicy
    source: str

    @property
    def source_sha256(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()

    @property
    def source_bytes(self) -> int:
        return len(self.source.encode("utf-8"))


@dataclass(frozen=True)
class WorkVector:
    """Python-owned logical work, intentionally separate from elapsed time."""

    input_lines: int = 0
    indent_resolutions: int = 0
    node_builds: int = 0
    node_initializations: int = 0
    node_attachments: int = 0
    node_refreshes: int = 0
    replacement_events: int = 0
    normalization_node_visits: int = 0
    reference_collection_node_visits: int = 0
    immutable_ancestor_rebuild_steps: int = 0

    def linear_operation_counts(self) -> dict[str, int]:
        """Return each independently gated operation in the linear work vector."""
        return {
            "input_lines": self.input_lines,
            "indent_resolutions": self.indent_resolutions,
            "node_builds": self.node_builds,
            "node_initializations": self.node_initializations,
            "node_attachments": self.node_attachments,
            "node_refreshes": self.node_refreshes,
            "replacement_events": self.replacement_events,
            "normalization_node_visits": self.normalization_node_visits,
            "reference_collection_node_visits": self.reference_collection_node_visits,
        }

    @property
    def linear_work(self) -> int:
        """Return work expected to remain linear for every declared family."""
        return sum(
            (
                self.input_lines,
                self.indent_resolutions,
                self.node_builds,
                self.node_initializations,
                self.node_attachments,
                self.node_refreshes,
                self.replacement_events,
                self.normalization_node_visits,
                self.reference_collection_node_visits,
            )
        )


@dataclass(frozen=True)
class WorkReceipt:
    """Source-free receipt for one deterministic parser-work observation."""

    work_model_schema_version: int
    work_generator_version: int
    case_id: str
    family: WorkFamily
    seed: int
    size: int
    growth_policy: GrowthPolicy
    source_sha256: str
    source_bytes: int
    bounded: bool
    timeout_seconds: float | None
    classification: Classification
    exception_type: str | None
    work: WorkVector | None
    structural_invariants_checked: bool
    semantic_roundtrip_checked: bool
    elapsed_seconds: float | None
    resident_high_water: int | None
    resident_high_water_unit: str | None
    platform_system: str
    platform_machine: str
    python_version: str
    replay_command: str


def _case_id(family: WorkFamily, size: int) -> str:
    return f"m4-{family}-{FIXED_SEED}-{size}"


def _bounded_case(family: WorkFamily, size: int, policy: GrowthPolicy, source: str) -> WorkCase:
    if size < 1:
        raise ValueError("work-growth size must be positive")
    if len(source.encode("utf-8")) > MAX_CASE_BYTES:
        raise ValueError(f"generated {family} case exceeds {MAX_CASE_BYTES} byte budget")
    return WorkCase(
        case_id=_case_id(family, size),
        family=family,
        seed=FIXED_SEED,
        size=size,
        growth_policy=policy,
        source=source,
    )


def _flat_blocks(size: int) -> WorkCase:
    source = "".join(f"- flat-{index} [[Page{index}]]\n" for index in range(size))
    return _bounded_case("flat-blocks", size, "linear-v1", source)


def _deep_chain(size: int) -> WorkCase:
    source = "".join(
        f"{'  ' * index}- deep-{index} [[Depth{index}]]\n" for index in range(size)
    )
    return _bounded_case("deep-chain", size, "immutable-ancestor-rebuild-v1", source)


def _fenced_continuations(size: int) -> WorkCase:
    source = "- fenced-root [[Visible]]\n  ```text\n"
    source += "".join(f"  literal-{index} [[Shielded{index}]]\n" for index in range(size))
    source += "  ```\n"
    return _bounded_case("fenced-continuations", size, "linear-v1", source)


def _properties(size: int) -> WorkCase:
    source = "- property-root [[Visible]]\n"
    source += "".join(f"  key-{index}:: value-{index}\n" for index in range(size))
    return _bounded_case("properties", size, "linear-v1", source)


FAMILY_GENERATORS: Final[dict[WorkFamily, Any]] = {
    "deep-chain": _deep_chain,
    "fenced-continuations": _fenced_continuations,
    "flat-blocks": _flat_blocks,
    "properties": _properties,
}


def cases_for_profile(profile: Literal["fixed"]) -> tuple[WorkCase, ...]:
    """Return canonical fixed-seed cases, independent of dictionary insertion order."""
    if profile != "fixed":
        raise ValueError(f"unknown work-growth profile: {profile}")
    return tuple(
        FAMILY_GENERATORS[family](size)
        for family in sorted(FAMILY_GENERATORS)
        for size in SIZE_STEPS
    )


class InstrumentedStackMachineParser(StackMachineParser):
    """Count selected parser operations without changing runtime parser code."""

    def __init__(self) -> None:
        super().__init__()
        self.work = WorkVector()

    def _add(self, **increments: int) -> None:
        values = asdict(self.work)
        for name, amount in increments.items():
            values[name] += amount
        self.work = WorkVector(**values)

    def parse(self, text: str, page_title: str = "untitled") -> LogseqPage:
        self._add(input_lines=len(text.splitlines()))
        return super().parse(text, page_title=page_title)

    def _compute_indent_level(self, indent: str) -> int:
        self._add(indent_resolutions=1)
        return super()._compute_indent_level(indent)

    def _build_node(
        self,
        block_text: str,
        indent_level: int,
        page_title: str,
        line_start: int,
        parent_uuid: str | None,
    ) -> LogseqNode:
        self._add(node_builds=1)
        return super()._build_node(block_text, indent_level, page_title, line_start, parent_uuid)

    def _initialize_node_graph_fields(
        self,
        node: LogseqNode,
        stack: list[LogseqNode],
        root_nodes: list[LogseqNode],
    ) -> LogseqNode:
        self._add(node_initializations=1)
        return super()._initialize_node_graph_fields(node, stack, root_nodes)

    def _attach_node_to_parent(
        self,
        stack: list[LogseqNode],
        root_nodes: list[LogseqNode],
        node: LogseqNode,
    ) -> LogseqNode:
        self._add(node_attachments=1)
        return super()._attach_node_to_parent(stack, root_nodes, node)

    def _refresh_node(
        self,
        node: LogseqNode,
        content: str,
        properties_override: dict[str, Any] | None = None,
        properties_order_override: list[str] | None = None,
        line_end: int | None = None,
        *,
        refresh_derived: bool = False,
    ) -> LogseqNode:
        self._add(node_refreshes=1)
        return super()._refresh_node(
            node,
            content,
            properties_override=properties_override,
            properties_order_override=properties_order_override,
            line_end=line_end,
            refresh_derived=refresh_derived,
        )

    def _replace_stack_tail_node(
        self,
        stack: list[LogseqNode],
        root_nodes: list[LogseqNode],
        updated_node: LogseqNode,
    ) -> None:
        self._add(replacement_events=1)
        super()._replace_stack_tail_node(stack, root_nodes, updated_node)

    def _normalize_indent_levels(
        self, nodes: list[LogseqNode], depth: int = 0
    ) -> list[LogseqNode]:
        self._add(normalization_node_visits=len(nodes))
        return super()._normalize_indent_levels(nodes, depth)

    def _collect_page_refs(self, roots: list[LogseqNode]) -> list[str]:
        self._add(reference_collection_node_visits=sum(1 for _ in walk_nodes(roots)))
        return super()._collect_page_refs(roots)


def _resident_observation() -> tuple[int | None, str | None]:
    """Return a labelled process high-water observation without normalization claims."""
    if resource is None:
        return None, None
    try:
        observation = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (AttributeError, OSError):
        return None, None
    unit = "bytes" if platform.system() == "Darwin" else "KiB"
    return observation, unit


def _replay_command(
    case: WorkCase,
    *,
    bounded: bool,
    timeout_seconds: float | None,
) -> str:
    """Return a source-free command that selects exactly one fixed case."""
    command = f"uv run python -m tests.parser_assurance.work_growth --profile fixed --case-id {case.case_id}"
    if bounded:
        assert timeout_seconds is not None
        command += f" --bounded --timeout-seconds {timeout_seconds:g}"
    return command


def evaluate_case(case: WorkCase) -> WorkReceipt:
    """Evaluate one valid case and emit a source-free deterministic receipt."""
    started = time.perf_counter()
    parser = InstrumentedStackMachineParser()
    try:
        page = parser.parse(case.source, page_title=f"work-growth/{case.family}")
        assert_tree_invariants(page)
        rendered = serialize_logseq_page(page)
        reparsed = StackMachineParser().parse(rendered, page_title=page.title)
        assert_tree_invariants(reparsed)
        semantic_matches = project_page(
            page,
            profile="semantic_roundtrip_v1",
            identity_policy=IDENTITY_POLICY,
        ) == project_page(
            reparsed,
            profile="semantic_roundtrip_v1",
            identity_policy=IDENTITY_POLICY,
        )
        classification: Classification = "parsed" if semantic_matches else "semantic_roundtrip_failure"
        exception_type = None if semantic_matches else "SemanticRoundtripMismatch"
        invariants_checked = True
    except AssertionError:
        classification = "invariant_failure"
        exception_type = "AssertionError"
        semantic_matches = False
        invariants_checked = False
    except Exception as error:  # Defensive test-only classification boundary.
        classification = "unexpected_exception"
        exception_type = type(error).__name__
        semantic_matches = False
        invariants_checked = False
    resident_high_water, resident_high_water_unit = _resident_observation()
    return WorkReceipt(
        work_model_schema_version=WORK_MODEL_SCHEMA_VERSION,
        work_generator_version=WORK_GENERATOR_VERSION,
        case_id=case.case_id,
        family=case.family,
        seed=case.seed,
        size=case.size,
        growth_policy=case.growth_policy,
        source_sha256=case.source_sha256,
        source_bytes=case.source_bytes,
        bounded=False,
        timeout_seconds=None,
        classification=classification,
        exception_type=exception_type,
        work=parser.work if classification in {"parsed", "semantic_roundtrip_failure"} else None,
        structural_invariants_checked=invariants_checked,
        semantic_roundtrip_checked=semantic_matches,
        elapsed_seconds=time.perf_counter() - started,
        resident_high_water=resident_high_water,
        resident_high_water_unit=resident_high_water_unit,
        platform_system=platform.system(),
        platform_machine=platform.machine(),
        python_version=platform.python_version(),
        replay_command=_replay_command(case, bounded=False, timeout_seconds=None),
    )


def _case_payload(case: WorkCase) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "family": case.family,
        "seed": case.seed,
        "size": case.size,
        "growth_policy": case.growth_policy,
        "source": case.source,
    }


def _case_from_payload(payload: object) -> WorkCase:
    if not isinstance(payload, dict):
        raise ValueError("worker payload must be an object")
    family = payload.get("family")
    policy = payload.get("growth_policy")
    if family not in FAMILY_GENERATORS or policy not in {
        "linear-v1",
        "immutable-ancestor-rebuild-v1",
    }:
        raise ValueError("worker payload has an unsupported family or growth policy")
    return WorkCase(
        case_id=str(payload["case_id"]),
        family=family,
        seed=int(payload["seed"]),
        size=int(payload["size"]),
        growth_policy=policy,
        source=str(payload["source"]),
    )


def _receipt_from_payload(payload: object) -> WorkReceipt:
    if not isinstance(payload, dict):
        raise ValueError("worker receipt must be an object")
    work_payload = payload.get("work")
    work = WorkVector(**work_payload) if isinstance(work_payload, dict) else None
    family = payload["family"]
    policy = payload["growth_policy"]
    classification = payload["classification"]
    if (
        family not in FAMILY_GENERATORS
        or policy not in {"linear-v1", "immutable-ancestor-rebuild-v1"}
        or classification not in {
            "parsed",
            "invariant_failure",
            "semantic_roundtrip_failure",
            "unexpected_exception",
            "timeout",
            "runner_failure",
        }
    ):
        raise ValueError("worker receipt has an unsupported enum value")
    return WorkReceipt(
        work_model_schema_version=int(payload["work_model_schema_version"]),
        work_generator_version=int(payload["work_generator_version"]),
        case_id=str(payload["case_id"]),
        family=family,
        seed=int(payload["seed"]),
        size=int(payload["size"]),
        growth_policy=policy,
        source_sha256=str(payload["source_sha256"]),
        source_bytes=int(payload["source_bytes"]),
        bounded=bool(payload["bounded"]),
        timeout_seconds=(
            float(payload["timeout_seconds"]) if payload["timeout_seconds"] is not None else None
        ),
        classification=classification,
        exception_type=payload["exception_type"] if isinstance(payload["exception_type"], str) else None,
        work=work,
        structural_invariants_checked=bool(payload["structural_invariants_checked"]),
        semantic_roundtrip_checked=bool(payload["semantic_roundtrip_checked"]),
        elapsed_seconds=(float(payload["elapsed_seconds"]) if payload["elapsed_seconds"] is not None else None),
        resident_high_water=(
            int(payload["resident_high_water"]) if payload["resident_high_water"] is not None else None
        ),
        resident_high_water_unit=(
            payload["resident_high_water_unit"]
            if isinstance(payload["resident_high_water_unit"], str)
            else None
        ),
        platform_system=str(payload["platform_system"]),
        platform_machine=str(payload["platform_machine"]),
        python_version=str(payload["python_version"]),
        replay_command=str(payload["replay_command"]),
    )


def _timeout_receipt(
    case: WorkCase,
    classification: Classification,
    exception_type: str | None,
    *,
    timeout_seconds: float,
) -> WorkReceipt:
    return WorkReceipt(
        work_model_schema_version=WORK_MODEL_SCHEMA_VERSION,
        work_generator_version=WORK_GENERATOR_VERSION,
        case_id=case.case_id,
        family=case.family,
        seed=case.seed,
        size=case.size,
        growth_policy=case.growth_policy,
        source_sha256=case.source_sha256,
        source_bytes=case.source_bytes,
        bounded=True,
        timeout_seconds=timeout_seconds,
        classification=classification,
        exception_type=exception_type,
        work=None,
        structural_invariants_checked=False,
        semantic_roundtrip_checked=False,
        elapsed_seconds=None,
        resident_high_water=None,
        resident_high_water_unit=None,
        platform_system=platform.system(),
        platform_machine=platform.machine(),
        python_version=platform.python_version(),
        replay_command=_replay_command(case, bounded=True, timeout_seconds=timeout_seconds),
    )


def run_bounded_case(case: WorkCase, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> WorkReceipt:
    """Run one case in a fresh process with a parent-enforced timeout."""
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "tests.parser_assurance.work_growth", "--worker"],
            input=json.dumps(_case_payload(case)),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _timeout_receipt(case, "timeout", None, timeout_seconds=timeout_seconds)
    if completed.returncode != 0:
        return _timeout_receipt(
            case,
            "runner_failure",
            f"exit-{completed.returncode}",
            timeout_seconds=timeout_seconds,
        )
    try:
        return replace(
            _receipt_from_payload(json.loads(completed.stdout)),
            bounded=True,
            timeout_seconds=timeout_seconds,
            replay_command=_replay_command(case, bounded=True, timeout_seconds=timeout_seconds),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _timeout_receipt(
            case,
            "runner_failure",
            "InvalidWorkerReceipt",
            timeout_seconds=timeout_seconds,
        )


def run_profile(
    profile: Literal["fixed"],
    *,
    bounded: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    case_id: str | None = None,
) -> tuple[WorkReceipt, ...]:
    """Run the fixed matrix directly or through bounded fresh subprocesses."""
    cases = cases_for_profile(profile)
    if case_id is not None:
        cases = tuple(case for case in cases if case.case_id == case_id)
        if not cases:
            raise ValueError(f"case not found in {profile} profile: {case_id}")
    if bounded:
        return tuple(run_bounded_case(case, timeout_seconds=timeout_seconds) for case in cases)
    return tuple(evaluate_case(case) for case in cases)


def assert_growth_contract(receipts: Sequence[WorkReceipt]) -> None:
    """Reject unexplained superlinear deterministic work in the declared matrix."""
    by_family: dict[WorkFamily, list[WorkReceipt]] = {}
    for receipt in receipts:
        if receipt.classification != "parsed" or receipt.work is None:
            raise AssertionError(f"{receipt.case_id}: work case did not parse cleanly")
        if not receipt.structural_invariants_checked or not receipt.semantic_roundtrip_checked:
            raise AssertionError(f"{receipt.case_id}: semantic or structural gate did not pass")
        by_family.setdefault(receipt.family, []).append(receipt)

    if set(by_family) != set(FAMILY_GENERATORS):
        raise AssertionError("work-growth matrix is missing a declared family")

    for family, family_receipts in by_family.items():
        ordered = sorted(family_receipts, key=lambda receipt: receipt.size)
        if tuple(receipt.size for receipt in ordered) != SIZE_STEPS:
            raise AssertionError(f"{family}: work-growth matrix has unexpected sizes")
        for previous, current in zip(ordered[:-1], ordered[1:], strict=True):
            assert previous.work is not None and current.work is not None
            for operation, previous_count in previous.work.linear_operation_counts().items():
                current_count = current.work.linear_operation_counts()[operation]
                if current_count * LINEAR_RATIO_DENOMINATOR > (
                    previous_count * LINEAR_RATIO_NUMERATOR
                ):
                    raise AssertionError(
                        f"{family}: {operation} work exceeded the documented 2.5x envelope"
                    )
        if any(receipt.work and receipt.work.immutable_ancestor_rebuild_steps for receipt in ordered):
            raise AssertionError(f"{family}: immutable ancestor rebuild work is forbidden")


def _worker_main() -> int:
    """Read one private source payload and emit one source-free work receipt."""
    try:
        receipt = evaluate_case(_case_from_payload(json.loads(sys.stdin.read())))
        print(json.dumps(asdict(receipt), sort_keys=True))
    except Exception as error:  # A malformed protocol is a runner failure.
        print(json.dumps({"error": type(error).__name__}, sort_keys=True))
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the deterministic parser work-growth laboratory.")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--profile", choices=("fixed",), default="fixed")
    parser.add_argument("--bounded", action="store_true", help="Use a fresh subprocess per case.")
    parser.add_argument("--case-id", help="Replay exactly one generated case from the selected profile.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Positive parent-enforced timeout used only with --bounded.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Print safe deterministic receipts; elapsed and RSS fields are diagnostic only."""
    args = _parse_args(argv)
    if args.worker:
        return _worker_main()
    if args.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    receipts = run_profile(
        args.profile,
        bounded=args.bounded,
        timeout_seconds=args.timeout_seconds,
        case_id=args.case_id,
    )
    if args.case_id is None:
        assert_growth_contract(receipts)
    print(
        json.dumps(
            {
                "work_model_schema_version": WORK_MODEL_SCHEMA_VERSION,
                "work_generator_version": WORK_GENERATOR_VERSION,
                "profile": args.profile,
                "bounded": args.bounded,
                "receipts": [asdict(receipt) for receipt in receipts],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
