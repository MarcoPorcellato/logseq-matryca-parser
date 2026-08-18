"""Deterministic, test-only adversarial parser laboratory.

The laboratory is deliberately independent of the valid-fixture manifest.  It
generates original bounded inputs, executes each one in a fresh subprocess, and
prints safe replay receipts instead of source text.  It is not a public API or
a benchmark harness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from typing import Final, Literal

from logseq_matryca_parser.exceptions import LogseqParserError
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import serialize_logseq_page
from tests.parser_assurance.invariants import assert_tree_invariants
from tests.parser_assurance.projection import IdentityPolicy, project_page

GENERATOR_SCHEMA_VERSION: Final = 1
FAST_SEEDS: Final = (104,)
BROAD_SEEDS: Final = (104, 417, 911)
MAX_CASE_BYTES: Final = 16_384
DEFAULT_TIMEOUT_SECONDS: Final = 3.0

Classification = Literal[
    "parsed",
    "expected_parser_error",
    "unexpected_exception",
    "invariant_failure",
    "semantic_roundtrip_failure",
    "timeout",
    "runner_failure",
]
InputKind = Literal["valid", "malformed"]

IDENTITY_POLICY: Final[IdentityPolicy] = {
    "synthetic_uuid": "recomputed",
    "source_uuid": "absent",
    "relations": "outline_paths",
}


@dataclass(frozen=True)
class GeneratedCase:
    """One original generated input and the contract expected of its execution."""

    case_id: str
    family: str
    seed: int
    index: int
    source: str
    input_kind: InputKind
    strict_refs: bool
    semantic_roundtrip: bool
    expected_classifications: tuple[Classification, ...]

    @property
    def source_sha256(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()

    @property
    def source_bytes(self) -> int:
        return len(self.source.encode("utf-8"))


@dataclass(frozen=True)
class CaseResult:
    """A source-free classification receipt returned by the parent runner."""

    case_id: str
    family: str
    seed: int
    index: int
    input_kind: InputKind
    source_sha256: str
    source_bytes: int
    classification: Classification
    exception_type: str | None
    semantic_roundtrip_checked: bool
    python_version: str
    minimized_source_sha256: str | None = None
    minimized_source_bytes: int | None = None

    def is_expected_for(self, case: GeneratedCase) -> bool:
        return self.classification in case.expected_classifications


def _case_id(family: str, seed: int, index: int) -> str:
    return f"m3-{family}-{seed}-{index}"


def _bounded_case(
    *,
    family: str,
    seed: int,
    index: int,
    source: str,
    input_kind: InputKind,
    strict_refs: bool = False,
    semantic_roundtrip: bool = False,
    expected_classifications: tuple[Classification, ...] = ("parsed",),
) -> GeneratedCase:
    if len(source.encode("utf-8")) > MAX_CASE_BYTES:
        raise ValueError(f"generated {family} case exceeds {MAX_CASE_BYTES} byte budget")
    return GeneratedCase(
        case_id=_case_id(family, seed, index),
        family=family,
        seed=seed,
        index=index,
        source=source,
        input_kind=input_kind,
        strict_refs=strict_refs,
        semantic_roundtrip=semantic_roundtrip,
        expected_classifications=expected_classifications,
    )


def _indentation_case(seed: int, index: int, rng: random.Random) -> GeneratedCase:
    depth = 2 + rng.randrange(5)
    lines = [f"{'  ' * level}- depth-{level} [[Depth{level}]]" for level in range(depth)]
    return _bounded_case(
        family="indentation-depth",
        seed=seed,
        index=index,
        source="\n".join(lines) + "\n",
        input_kind="valid",
        semantic_roundtrip=True,
    )


def _fence_case(seed: int, index: int, rng: random.Random) -> GeneratedCase:
    fence = rng.choice(("```", "~~~"))
    if index % 2 == 0:
        source = f"- open-fence\n  {fence}text\n  [[LiteralOnly]]\n"
        return _bounded_case(
            family="fences",
            seed=seed,
            index=index,
            source=source,
            input_kind="malformed",
        )
    source = f"- closed-fence [[Visible]]\n  {fence}text\n  [[LiteralOnly]]\n  {fence}\n"
    return _bounded_case(
        family="fences",
        seed=seed,
        index=index,
        source=source,
        input_kind="valid",
        semantic_roundtrip=True,
    )


def _delimiter_case(seed: int, index: int, rng: random.Random) -> GeneratedCase:
    if index % 3 == 1:
        return _bounded_case(
            family="escapes-delimiters",
            seed=seed,
            index=index,
            source="- mixed `a `` [[Hidden]] ` [[Visible]]\n",
            input_kind="malformed",
        )
    if index % 3 == 2:
        return _bounded_case(
            family="escapes-delimiters",
            seed=seed,
            index=index,
            source="- overlap ``outer `[[Hidden]]` [[Visible]]`` [[Tail]]\n",
            input_kind="malformed",
        )
    delimiter = "`" * (1 + rng.randrange(3))
    source = (
        f"- escaped \\[[Hidden]] {delimiter}[[Literal]]{delimiter} [[Visible]]\n"
        "  {{query [[MacroTarget]]}}\n"
    )
    return _bounded_case(
        family="escapes-delimiters",
        seed=seed,
        index=index,
        source=source,
        input_kind="valid",
        semantic_roundtrip=True,
    )


def _property_case(seed: int, index: int, rng: random.Random) -> GeneratedCase:
    marker = rng.randrange(10_000)
    source = (
        f"tags:: [[Alpha {marker}]], [[Beta {marker}]]\n"
        f"- properties [[Visible {marker}]]\n"
        f"  aliases:: [[Alias {marker}]], Alias {marker}\n"
        f"  - child #[[Tag {marker}]]\n"
    )
    return _bounded_case(
        family="properties-references",
        seed=seed,
        index=index,
        source=source,
        input_kind="valid",
        semantic_roundtrip=True,
    )


def _unicode_newline_case(seed: int, index: int, rng: random.Random) -> GeneratedCase:
    newline = "\r\n" if index % 2 else "\n"
    token = rng.choice(("caffè", "東京", "naïve", "🙂"))
    source = newline.join(
        (
            f"- {token} [[Unicode {index}]]",
            f"  - child {token} #[[Tag {index}]]",
            "",
        )
    )
    return _bounded_case(
        family="unicode-newlines",
        seed=seed,
        index=index,
        source=source,
        input_kind="valid",
        semantic_roundtrip=True,
    )


def _large_line_case(seed: int, index: int, rng: random.Random) -> GeneratedCase:
    width = 1_024 + (rng.randrange(4) * 512)
    source = f"- {'x' * width} [[LongLine {index}]]\n"
    return _bounded_case(
        family="large-lines",
        seed=seed,
        index=index,
        source=source,
        input_kind="valid",
        semantic_roundtrip=True,
    )


def _strict_reference_case(seed: int, index: int, _rng: random.Random) -> GeneratedCase:
    missing_uuid = f"{seed:08x}-aaaa-bbbb-cccc-{index:012x}"
    source = f"- unresolved (({missing_uuid}))\n"
    return _bounded_case(
        family="strict-references",
        seed=seed,
        index=index,
        source=source,
        input_kind="malformed",
        strict_refs=True,
        expected_classifications=("expected_parser_error",),
    )


FAMILY_GENERATORS: Final = {
    "delimiter-escapes": _delimiter_case,
    "fences": _fence_case,
    "indentation-depth": _indentation_case,
    "large-lines": _large_line_case,
    "properties-references": _property_case,
    "strict-references": _strict_reference_case,
    "unicode-newlines": _unicode_newline_case,
}


def generate_cases(
    seed: int,
    *,
    cases_per_family: int,
    families: Sequence[str] | None = None,
) -> tuple[GeneratedCase, ...]:
    """Generate a canonical sequence, independent of the caller's family order."""
    if cases_per_family < 1:
        raise ValueError("cases_per_family must be positive")
    selected = tuple(sorted(set(families or tuple(FAMILY_GENERATORS))))
    unknown = set(selected) - FAMILY_GENERATORS.keys()
    if unknown:
        raise ValueError(f"unknown generator families: {sorted(unknown)}")
    cases: list[GeneratedCase] = []
    for family in selected:
        generator = FAMILY_GENERATORS[family]
        for index in range(cases_per_family):
            family_seed = int.from_bytes(
                hashlib.sha256(f"{GENERATOR_SCHEMA_VERSION}:{seed}:{family}:{index}".encode()).digest()[:8],
                "big",
            )
            cases.append(generator(seed, index, random.Random(family_seed)))
    return tuple(cases)


def cases_for_profile(profile: Literal["fast", "broad"]) -> tuple[GeneratedCase, ...]:
    """Return the bounded fixed or scheduled case matrix."""
    seeds = FAST_SEEDS if profile == "fast" else BROAD_SEEDS
    cases_per_family = 3
    return tuple(
        case
        for seed in seeds
        for case in generate_cases(seed, cases_per_family=cases_per_family)
    )


def _worker_result(case: GeneratedCase) -> tuple[Classification, str | None, bool]:
    """Parse one case in a child process and never emit source text."""
    try:
        page = StackMachineParser(strict_refs=case.strict_refs).parse(
            case.source,
            page_title=f"adversarial/{case.family}",
        )
        assert_tree_invariants(page)
        if case.semantic_roundtrip:
            rendered = serialize_logseq_page(page)
            reparsed = StackMachineParser(strict_refs=case.strict_refs).parse(
                rendered,
                page_title=page.title,
            )
            assert_tree_invariants(reparsed)
            if project_page(
                reparsed,
                profile="semantic_roundtrip_v1",
                identity_policy=IDENTITY_POLICY,
            ) != project_page(
                page,
                profile="semantic_roundtrip_v1",
                identity_policy=IDENTITY_POLICY,
            ):
                return "semantic_roundtrip_failure", "SemanticRoundtripMismatch", True
    except LogseqParserError as error:
        return "expected_parser_error", type(error).__name__, False
    except AssertionError:
        return "invariant_failure", "AssertionError", False
    except Exception as error:  # Defensive classification boundary for generated input.
        return "unexpected_exception", type(error).__name__, False
    return "parsed", None, case.semantic_roundtrip


def _case_from_payload(payload: object) -> GeneratedCase:
    if not isinstance(payload, dict):
        raise ValueError("worker payload must be an object")
    expected = payload.get("expected_classifications")
    if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
        raise ValueError("worker expected classifications must be strings")
    return GeneratedCase(
        case_id=str(payload["case_id"]),
        family=str(payload["family"]),
        seed=int(payload["seed"]),
        index=int(payload["index"]),
        source=str(payload["source"]),
        input_kind=payload["input_kind"],
        strict_refs=bool(payload["strict_refs"]),
        semantic_roundtrip=bool(payload["semantic_roundtrip"]),
        expected_classifications=tuple(expected),
    )


def _worker_main() -> int:
    """Read one case from stdin and print one source-free JSON result."""
    try:
        case = _case_from_payload(json.loads(sys.stdin.read()))
        classification, exception_type, semantic_checked = _worker_result(case)
        print(
            json.dumps(
                {
                    "classification": classification,
                    "exception_type": exception_type,
                    "semantic_roundtrip_checked": semantic_checked,
                },
                sort_keys=True,
            )
        )
    except Exception as error:  # A malformed worker protocol is a runner failure.
        print(
            json.dumps(
                {
                    "classification": "runner_failure",
                    "exception_type": type(error).__name__,
                    "semantic_roundtrip_checked": False,
                },
                sort_keys=True,
            )
        )
    return 0


def _base_result(
    case: GeneratedCase,
    *,
    classification: Classification,
    exception_type: str | None,
    semantic_roundtrip_checked: bool,
) -> CaseResult:
    return CaseResult(
        case_id=case.case_id,
        family=case.family,
        seed=case.seed,
        index=case.index,
        input_kind=case.input_kind,
        source_sha256=case.source_sha256,
        source_bytes=case.source_bytes,
        classification=classification,
        exception_type=exception_type,
        semantic_roundtrip_checked=semantic_roundtrip_checked,
        python_version=platform.python_version(),
    )


def run_case(case: GeneratedCase, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> CaseResult:
    """Execute a case in a fresh process and classify timeout or runner failure."""
    payload = asdict(case)
    payload["expected_classifications"] = list(case.expected_classifications)
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "tests.parser_assurance.adversarial", "--worker"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _base_result(
            case,
            classification="timeout",
            exception_type=None,
            semantic_roundtrip_checked=False,
        )
    if completed.returncode != 0:
        return _base_result(
            case,
            classification="runner_failure",
            exception_type=f"exit-{completed.returncode}",
            semantic_roundtrip_checked=False,
        )
    try:
        payload_result = json.loads(completed.stdout)
        classification = payload_result["classification"]
        exception_type = payload_result["exception_type"]
        semantic_checked = payload_result["semantic_roundtrip_checked"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return _base_result(
            case,
            classification="runner_failure",
            exception_type="InvalidWorkerReceipt",
            semantic_roundtrip_checked=False,
        )
    if classification not in {
        "parsed",
        "expected_parser_error",
        "unexpected_exception",
        "invariant_failure",
        "semantic_roundtrip_failure",
        "timeout",
        "runner_failure",
    }:
        return _base_result(
            case,
            classification="runner_failure",
            exception_type="UnknownClassification",
            semantic_roundtrip_checked=False,
        )
    if exception_type is not None and not isinstance(exception_type, str):
        return _base_result(
            case,
            classification="runner_failure",
            exception_type="InvalidExceptionType",
            semantic_roundtrip_checked=False,
        )
    if not isinstance(semantic_checked, bool):
        return _base_result(
            case,
            classification="runner_failure",
            exception_type="InvalidSemanticFlag",
            semantic_roundtrip_checked=False,
        )
    return _base_result(
        case,
        classification=classification,
        exception_type=exception_type,
        semantic_roundtrip_checked=semantic_checked,
    )


def minimize_source(
    case: GeneratedCase,
    *,
    preserves_failure: Callable[[str], bool],
) -> GeneratedCase:
    """Greedily delete lines while an exact caller-defined failure persists."""
    lines = case.source.splitlines(keepends=True)
    changed = True
    while changed and len(lines) > 1:
        changed = False
        for index in range(len(lines)):
            candidate = "".join([*lines[:index], *lines[index + 1 :]])
            if candidate and preserves_failure(candidate):
                lines = candidate.splitlines(keepends=True)
                changed = True
                break
    return replace(case, source="".join(lines))


def _minimize_unexpected(case: GeneratedCase, result: CaseResult, timeout_seconds: float) -> CaseResult:
    """Return a receipt with safe minimized-input metadata for a failing case."""

    def preserves_failure(source: str) -> bool:
        candidate = replace(case, source=source)
        replay = run_case(candidate, timeout_seconds=timeout_seconds)
        return (
            replay.classification == result.classification
            and replay.exception_type == result.exception_type
        )

    minimized = minimize_source(case, preserves_failure=preserves_failure)
    return replace(
        result,
        minimized_source_sha256=minimized.source_sha256,
        minimized_source_bytes=minimized.source_bytes,
    )


def run_profile(
    profile: Literal["fast", "broad"],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    case_id: str | None = None,
) -> tuple[CaseResult, ...]:
    """Run one reproducible profile and minimize only unexpected failures."""
    cases = cases_for_profile(profile)
    if case_id is not None:
        cases = tuple(case for case in cases if case.case_id == case_id)
        if not cases:
            raise ValueError(f"case not found in {profile} profile: {case_id}")
    results: list[CaseResult] = []
    for case in cases:
        result = run_case(case, timeout_seconds=timeout_seconds)
        if not result.is_expected_for(case):
            result = _minimize_unexpected(case, result, timeout_seconds)
        results.append(result)
    return tuple(results)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the deterministic parser adversarial laboratory.")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--profile", choices=("fast", "broad"), default="fast")
    parser.add_argument("--case-id", help="Replay exactly one generated case from the selected profile.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Positive parent-enforced subprocess timeout per case.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested profile and print deterministic, source-free receipts."""
    args = _parse_args(argv)
    if args.worker:
        return _worker_main()
    if args.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    results = run_profile(
        args.profile,
        timeout_seconds=args.timeout_seconds,
        case_id=args.case_id,
    )
    receipt = {
        "generator_schema_version": GENERATOR_SCHEMA_VERSION,
        "profile": args.profile,
        "results": [asdict(result) for result in results],
    }
    print(json.dumps(receipt, sort_keys=True))
    cases = cases_for_profile(args.profile)
    if args.case_id is not None:
        cases = tuple(case for case in cases if case.case_id == args.case_id)
    return 0 if all(result.is_expected_for(case) for case, result in zip(cases, results, strict=True)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
