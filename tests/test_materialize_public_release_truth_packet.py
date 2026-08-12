from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "tests"))
from release_authority_fixture import default_artifacts, write_authority_fixture


SCRIPT_PATH = REPO_ROOT / "scripts" / "materialize_public_release_truth_packet.py"
SPEC = importlib.util.spec_from_file_location("materialize_public_release_truth_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _resolve(fixture, *, expected_status: str | None = None):
    return MODULE.resolve_release_authority(
        fixture.current_path,
        registry_commit=fixture.registry_commit,
        expected_release_decision_status=expected_status or str(fixture.snapshot["releaseDecisionStatus"]),
    )


def _linux_gate() -> dict[str, object]:
    return {
        "docker_image": "debian:bookworm-slim",
        "generated_at_utc": "20260718T120000Z",
        "output": {"archive_sha256": "a" * 64, "executable_sha256": "b" * 64, "rid": "linux-x64"},
        "status": "passed",
    }


def _macos_contract() -> dict[str, object]:
    return {
        "generated_at_utc": "2026-07-18T12:00:00Z",
        "policy": {
            "doc_marks_second_script_install": True,
            "maintenance_policy_marks_real_build_as_macos_only": True,
            "maintenance_policy_requires_two_step_install": True,
        },
        "real_macos_runtime_proof_required": True,
        "runtime_coverage": "not_run_on_non_macos_host",
        "scope": "script_contract_only",
        "status": "passed",
    }


def test_stable_snapshot_materializes_one_normalized_gold_projection() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        fixture = write_authority_fixture(Path(temp_dir), decision_status="stable_ready")
        resolved = _resolve(fixture)
        packet = MODULE.build_packet(
            resolved.release_payload,
            _linux_gate(),
            _macos_contract(),
            resolved.authority,
            resolved.authority_source,
            resolved.served_mirror,
        )
        expected_snapshot_sha256 = hashlib.sha256(fixture.snapshot_path.read_bytes()).hexdigest()

    assert packet["authority"] == fixture.snapshot
    assert packet["authority_source"]["snapshotSha256"] == expected_snapshot_sha256
    assert packet["available_platforms"] == ["Linux", "Windows"]
    assert packet["primary_head"] == "Chummer.Avalonia"
    assert packet["release_posture"] == "stable_ready"
    assert packet["phase_label"] == "Gold-supported release"
    assert packet["generated_from"] == MODULE.CANONICAL_RELEASE_CHANNEL_SOURCE
    assert packet["served_mirror"] == MODULE.CANONICAL_RELEASE_CHANNEL_SOURCE


def test_gold_copy_fails_closed_without_stable_ready_decision() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        fixture = write_authority_fixture(Path(temp_dir), decision_status="stable_ready")
        resolved = _resolve(fixture)
        downgraded_authority = copy.deepcopy(resolved.authority)
        downgraded_authority["releaseDecisionStatus"] = "preview_ready"
        packet = MODULE.build_packet(
            resolved.release_payload,
            _linux_gate(),
            _macos_contract(),
            downgraded_authority,
            resolved.authority_source,
            resolved.served_mirror,
        )

    assert packet["release_posture"] == "preview_ready"
    assert packet["phase_label"] == "Preview-ready release"
    assert "gold-supported" not in packet["quality_gap_line"].casefold()


def test_canonical_output_requires_all_immutable_authority_flags(tmp_path: Path) -> None:
    original_output = MODULE.OUTPUT_PATH
    MODULE.OUTPUT_PATH = tmp_path / "must-not-exist.json"
    try:
        with pytest.raises(SystemExit) as raised:
            MODULE.main([])
    finally:
        MODULE.OUTPUT_PATH = original_output
    assert raised.value.code == 2
    assert not (tmp_path / "must-not-exist.json").exists()


def test_checked_in_unbound_placeholder_is_explicitly_review_required(tmp_path: Path) -> None:
    original_output = MODULE.OUTPUT_PATH
    MODULE.OUTPUT_PATH = tmp_path / "placeholder.json"
    try:
        assert MODULE.main(["--unbound-review-placeholder"]) == 0
        packet = json.loads(MODULE.OUTPUT_PATH.read_text(encoding="utf-8"))
    finally:
        MODULE.OUTPUT_PATH = original_output

    assert packet["authority_binding_status"] == "unbound_review_placeholder"
    assert packet["release_posture"] == "review_required"
    assert packet["available_platforms"] == []
    assert packet["authority"]["artifacts"] == []
    assert packet["review_required_banner"].startswith("Release review required.")
    public_copy = " ".join(
        str(packet[key])
        for key in (
            "architecture_scope_line",
            "desktop_pick_line",
            "known_issue_summary",
            "missing_installer_lane_line",
            "quality_gap_line",
            "release_verification_summary",
            "shelf_truth_line",
        )
    ).casefold()
    assert "repository projection" not in public_copy
    assert "unbound" not in public_copy


def test_unbound_placeholder_is_forbidden_in_release_mode() -> None:
    with pytest.raises(SystemExit) as raised:
        MODULE.main(["--release", "--unbound-review-placeholder"])
    assert raised.value.code == 2


def test_preview_snapshot_resolves_exact_siblings_and_repository_identity(tmp_path: Path) -> None:
    fixture = write_authority_fixture(tmp_path)
    resolved = _resolve(fixture)

    assert resolved.authority == fixture.snapshot
    assert resolved.authority_source["registryRepository"] == "ArchonMegalon/chummer6-hub-registry"
    assert resolved.authority_source["snapshotPath"].startswith("snapshots/run-20260718-120000/")
    assert resolved.authority_source["manifestPath"].endswith("/RELEASE_CHANNEL.json")
    assert resolved.authority_source["releaseDecisionPath"].endswith("/RELEASE_DECISION.json")
    assert resolved.authority_source["currentPath"] == "CURRENT.json"
    assert resolved.authority_source["currentStatus"] == "preview_ready"
    assert resolved.authority_source["manifestVersion"] == "run-20260718-120000"
    assert resolved.authority_source["manifestSchemaVersion"] == 2


def test_runtime_authority_root_does_not_require_a_git_checkout(tmp_path: Path) -> None:
    fixture = write_authority_fixture(tmp_path / "source")
    runtime_root = tmp_path / "runtime-authority"
    shutil.copytree(fixture.repo_root, runtime_root, ignore=shutil.ignore_patterns(".git"))

    resolved = MODULE.resolve_release_authority(
        runtime_root / "CURRENT.json",
        registry_commit=fixture.registry_commit,
        expected_release_decision_status="preview_ready",
    )

    assert resolved.authority == fixture.snapshot
    assert resolved.authority_source["currentPath"] == "CURRENT.json"


def test_content_addressed_snapshot_path_mismatch_is_rejected(tmp_path: Path) -> None:
    fixture = write_authority_fixture(tmp_path, path_digest="0" * 64)
    with pytest.raises((ValueError, FileNotFoundError)):
        _resolve(fixture)


def test_current_pointer_property_set_is_exact(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        current_mutator=lambda current: current.__setitem__("generatedAt", "forbidden"),
    )
    with pytest.raises(ValueError, match="CURRENT.json property set"):
        _resolve(fixture)


def test_manifest_byte_drift_is_rejected(tmp_path: Path) -> None:
    fixture = write_authority_fixture(tmp_path)
    fixture.manifest_path.write_bytes(fixture.manifest_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="manifestSha256"):
        _resolve(fixture)


def test_decision_byte_drift_is_rejected(tmp_path: Path) -> None:
    fixture = write_authority_fixture(tmp_path)
    fixture.decision_path.write_bytes(fixture.decision_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="releaseDecisionSha256"):
        _resolve(fixture)


def test_snapshot_property_set_is_exact(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        snapshot_mutator=lambda snapshot: snapshot.__setitem__("generatedAt", "forbidden"),
    )
    with pytest.raises(ValueError, match="property set"):
        _resolve(fixture)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda decision: decision.__setitem__("contractName", "unknown/v9"), "decision contract"),
        (lambda decision: decision.__setitem__("releaseVersion", "wrong-version"), "does not exactly bind"),
        (lambda decision: decision.__setitem__("manifestSha256", "f" * 64), "does not exactly bind"),
        (lambda decision: decision.__setitem__("registryCommit", "f" * 40), "does not exactly bind"),
        (lambda decision: decision.__setitem__("platforms", ["linux"]), "platform scope"),
        (
            lambda decision: decision.__setitem__(
                "primaryHeadByPlatform", {"linux": "wrong", "windows": "avalonia"}
            ),
            "primaryHeadByPlatform",
        ),
        (lambda decision: decision.__setitem__("supportOwner", "Someone else"), "supportOwner"),
    ],
)
def test_preview_decision_contract_and_bindings_are_exact(tmp_path: Path, mutator, message: str) -> None:
    fixture = write_authority_fixture(tmp_path, decision_mutator=mutator)
    with pytest.raises(ValueError, match=message):
        _resolve(fixture)


def test_unknown_snapshot_decision_status_is_rejected(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        snapshot_mutator=lambda snapshot: snapshot.__setitem__("releaseDecisionStatus", "candidate"),
    )
    with pytest.raises(ValueError, match="CURRENT.json status"):
        _resolve(fixture, expected_status="preview_ready")


def test_missing_primary_head_scope_is_rejected(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        snapshot_mutator=lambda snapshot: snapshot.__setitem__("primaryHeadByPlatform", {}),
    )
    with pytest.raises(ValueError, match="primaryHeadByPlatform"):
        _resolve(fixture)


@pytest.mark.parametrize("mode", ["unpromoted", "incompatible", "revoked"])
def test_snapshot_cannot_publish_ineligible_manifest_artifacts(tmp_path: Path, mode: str) -> None:
    def mutate(manifest: dict[str, object]) -> None:
        if mode == "unpromoted":
            coverage = manifest["desktopTupleCoverage"]
            assert isinstance(coverage, dict)
            routes = coverage["desktopRouteTruth"]
            assert isinstance(routes, list) and isinstance(routes[0], dict)
            routes[0]["promotionState"] = "candidate"
        elif mode == "incompatible":
            artifacts = manifest["artifacts"]
            assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
            artifacts[0]["compatibilityState"] = "incompatible"
        else:
            trust = manifest["publicTrustMetrics"]
            assert isinstance(trust, dict)
            facts = trust["revocationFacts"]
            assert isinstance(facts, dict)
            facts["activeRevocationCount"] = 1
            facts["activeRevocations"] = [{"artifactId": "avalonia-linux-x64-installer"}]

    fixture = write_authority_fixture(tmp_path, manifest_mutator=mutate)
    with pytest.raises(ValueError, match="canonical Registry manifest projection|public shelf|compatible and non-revoked"):
        _resolve(fixture)


def test_legacy_route_publication_scope_cannot_replace_registry_binding(tmp_path: Path) -> None:
    def mutate(manifest: dict[str, object]) -> None:
        coverage = manifest["desktopTupleCoverage"]
        assert isinstance(coverage, dict)
        routes = coverage["desktopRouteTruth"]
        bindings = manifest["artifactPublicationBindings"]
        assert isinstance(routes, list) and isinstance(routes[0], dict)
        assert isinstance(bindings, list) and isinstance(bindings[0], dict)
        routes[0]["publicationScope"] = "signed-in-and-public"
        bindings[0]["publicationScope"] = "private"

    fixture = write_authority_fixture(tmp_path, manifest_mutator=mutate)
    with pytest.raises(ValueError, match="canonical Registry manifest projection"):
        _resolve(fixture)


def test_ambiguous_publication_bindings_are_rejected(tmp_path: Path) -> None:
    def mutate(manifest: dict[str, object]) -> None:
        bindings = manifest["artifactPublicationBindings"]
        assert isinstance(bindings, list) and isinstance(bindings[0], dict)
        duplicate = dict(bindings[0])
        duplicate["bindingId"] = "second-binding"
        bindings.append(duplicate)

    fixture = write_authority_fixture(tmp_path, manifest_mutator=mutate)
    with pytest.raises(ValueError, match="ambiguous promoted route or public binding"):
        _resolve(fixture)


@pytest.mark.parametrize("field", ["head", "platform", "rid", "arch", "kind", "tupleId", "publicInstallRoute"])
def test_publication_binding_must_exactly_match_artifact_and_route(tmp_path: Path, field: str) -> None:
    def mutate(manifest: dict[str, object]) -> None:
        bindings = manifest["artifactPublicationBindings"]
        assert isinstance(bindings, list) and isinstance(bindings[0], dict)
        bindings[0][field] = "/downloads/install/different" if field == "publicInstallRoute" else "different"

    fixture = write_authority_fixture(tmp_path, manifest_mutator=mutate)
    with pytest.raises(ValueError, match="tuple does not match|kind does not match|publication binding"):
        _resolve(fixture)


def test_generation_id_and_file_name_bind_immutable_download_url(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        manifest_mutator=lambda manifest: manifest.__setitem__("generationId", "different-generation"),
    )
    with pytest.raises(ValueError, match="bind generationId and fileName"):
        _resolve(fixture)


def test_manifest_compatibility_alias_cannot_disagree_with_canonical_version(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        manifest_mutator=lambda manifest: manifest.__setitem__("releaseVersion", "run-different"),
    )
    with pytest.raises(ValueError, match="compatibility field releaseVersion disagrees"):
        _resolve(fixture)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("authoritySnapshotSha256", ""),
        ("candidateDecisionStatus", ""),
        ("candidateDecisionSha256", ""),
    ],
)
def test_preview_ready_requires_complete_candidate_closure(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        decision_mutator=lambda decision: decision.__setitem__(field, value),
    )
    with pytest.raises(ValueError, match="authoritySnapshotSha256|candidateDecisionStatus|candidateDecisionSha256"):
        _resolve(fixture)


def test_stable_contract_cannot_carry_review_required_posture(tmp_path: Path) -> None:
    def mutate(decision: dict[str, object]) -> None:
        manifest_sha = decision["manifestSha256"]
        registry_commit = decision["registryCommit"]
        release_version = decision["releaseVersion"]
        decision.clear()
        decision.update(
            {
                "contract_name": "chummer.final_gold_graph",
                "contract_version": 2,
                "releaseVersion": release_version,
                "releaseDecisionStatus": "review_required",
                "status": "review_required",
                "live_release": {},
                "release_authority": {
                    "contract": "chummer.release-authority-snapshot/v2",
                    "manifest_sha256": manifest_sha,
                    "registry_commit": registry_commit,
                    "release_decision_status": "review_required",
                },
            }
        )

    fixture = write_authority_fixture(
        tmp_path,
        decision_status="review_required",
        decision_mutator=mutate,
    )
    with pytest.raises(ValueError, match="stable_ready only"):
        _resolve(fixture)


def test_fallback_requires_explicit_decision_scope(tmp_path: Path) -> None:
    artifacts = default_artifacts()
    fallback = dict(artifacts[0])
    fallback.update(
        {
            "artifactId": "blazor-linux-x64-installer",
            "fileName": "chummer-blazor-linux-x64-installer.deb",
            "head": "blazor-desktop",
            "downloadUrl": "https://chummer.run/downloads/g/generation-1/files/chummer-blazor-linux-x64-installer.deb",
            "sha256": "c" * 64,
        }
    )
    fixture = write_authority_fixture(tmp_path, artifacts=artifacts + [fallback])
    with pytest.raises(ValueError, match="fallback-head scope"):
        _resolve(fixture)


def test_explicit_promoted_fallback_is_accepted(tmp_path: Path) -> None:
    artifacts = default_artifacts()
    fallback = dict(artifacts[0])
    fallback.update(
        {
            "artifactId": "blazor-linux-x64-installer",
            "fileName": "chummer-blazor-linux-x64-installer.deb",
            "head": "blazor-desktop",
            "downloadUrl": "https://chummer.run/downloads/g/generation-1/files/chummer-blazor-linux-x64-installer.deb",
            "sha256": "c" * 64,
        }
    )
    fixture = write_authority_fixture(
        tmp_path,
        artifacts=artifacts + [fallback],
        fallback_heads={"linux": ["blazor-desktop"]},
    )
    assert len(_resolve(fixture).authority["artifacts"]) == 3


def test_artifact_count_and_set_must_be_exact(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        snapshot_mutator=lambda snapshot: snapshot.__setitem__("artifactCount", 99),
    )
    with pytest.raises(ValueError, match="artifactCount"):
        _resolve(fixture)


def test_unknown_access_class_is_rejected(tmp_path: Path) -> None:
    def mutate(snapshot: dict[str, object]) -> None:
        artifacts = snapshot["artifacts"]
        assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
        artifacts[0]["installAccessClass"] = "mystery"

    fixture = write_authority_fixture(tmp_path, snapshot_mutator=mutate)
    with pytest.raises(ValueError, match="installAccessClass"):
        _resolve(fixture)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("compatibilityState", "incompatible", "compatibilityState"),
        ("promotionState", "candidate", "promotionState"),
        ("publicationScope", "private", "publicationScope"),
        ("revokeState", "revoked", "revokeState"),
        ("kind", "archive", "installer"),
        ("sizeBytes", 0, "positive integer"),
        ("downloadUrl", "/downloads/generated/file", "absolute HTTPS"),
        (
            "downloadUrl",
            "https://user:secret@chummer.run/downloads/g/generation-1/files/file.exe",
            "absolute HTTPS",
        ),
        (
            "downloadUrl",
            "https://chummer.run/downloads/g/generation-1/files/file.exe?mutable=1",
            "absolute HTTPS",
        ),
        (
            "downloadUrl",
            "https://chummer.run/generated/file.exe",
            "immutable /downloads/g",
        ),
    ],
)
def test_artifact_projection_value_rules_are_exact(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    def mutate(snapshot: dict[str, object]) -> None:
        artifacts = snapshot["artifacts"]
        assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
        artifacts[0][field] = value

    fixture = write_authority_fixture(tmp_path, snapshot_mutator=mutate)
    with pytest.raises(ValueError, match=message):
        _resolve(fixture)


@pytest.mark.parametrize(
    "route",
    [
        "https://chummer.run/downloads/file",
        "//chummer.run/downloads/file",
        "/downloads/../secret",
        "/downloads/%2e%2e/secret",
        "/downloads/file?token=secret",
        "/downloads/file#fragment",
        "/downloads\\..\\secret",
        "/downloads/files/legacy-installer.exe",
    ],
)
def test_public_install_route_must_be_safe_root_relative_path(tmp_path: Path, route: str) -> None:
    def mutate(snapshot: dict[str, object]) -> None:
        artifacts = snapshot["artifacts"]
        assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
        artifacts[0]["publicInstallRoute"] = route

    fixture = write_authority_fixture(tmp_path, snapshot_mutator=mutate)
    with pytest.raises(ValueError, match="root-relative"):
        _resolve(fixture)


def test_artifact_projection_requires_all_15_exact_fields(tmp_path: Path) -> None:
    def mutate(snapshot: dict[str, object]) -> None:
        artifacts = snapshot["artifacts"]
        assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
        artifacts[0].pop("rid")

    fixture = write_authority_fixture(tmp_path, snapshot_mutator=mutate)
    with pytest.raises(ValueError, match="property set"):
        _resolve(fixture)


def test_manifest_public_route_must_match_snapshot_projection_exactly(tmp_path: Path) -> None:
    def mutate(manifest: dict[str, object]) -> None:
        coverage = manifest["desktopTupleCoverage"]
        assert isinstance(coverage, dict)
        routes = coverage["desktopRouteTruth"]
        assert isinstance(routes, list) and isinstance(routes[0], dict)
        routes[0]["publicInstallRoute"] = "/downloads/install/different"

    fixture = write_authority_fixture(tmp_path, manifest_mutator=mutate)
    with pytest.raises(ValueError, match="publication binding"):
        _resolve(fixture)


def test_download_access_posture_is_exact_artifact_class_projection(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        snapshot_mutator=lambda snapshot: snapshot.__setitem__("downloadAccessPosture", "mixed"),
    )
    with pytest.raises(ValueError, match="downloadAccessPosture"):
        _resolve(fixture)


def test_sentinel_platform_and_head_ids_are_rejected(tmp_path: Path) -> None:
    def mutate(snapshot: dict[str, object]) -> None:
        snapshot["availablePlatforms"] = ["unknown", "windows"]
        snapshot["primaryHeadByPlatform"] = {"unknown": "missing", "windows": "avalonia"}
        artifacts = snapshot["artifacts"]
        assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
        artifacts[0]["platform"] = "unknown"
        artifacts[0]["head"] = "missing"

    fixture = write_authority_fixture(tmp_path, snapshot_mutator=mutate)
    with pytest.raises(ValueError, match="sentinel"):
        _resolve(fixture)


def test_snapshot_registry_repository_field_is_exact(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        snapshot_mutator=lambda snapshot: snapshot.__setitem__("registryRepository", "other/repo"),
    )
    with pytest.raises(ValueError, match="registryRepository"):
        _resolve(fixture)


def test_current_pointer_decision_digest_must_match_snapshot(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        current_mutator=lambda current: current.__setitem__("decisionSha256", "f" * 64),
    )
    with pytest.raises(ValueError, match="CURRENT.json releaseVersion, decisionSha256, and status"):
        _resolve(fixture)


def test_review_required_snapshot_requires_next_action(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        decision_status="review_required",
        artifacts=[],
        primary_heads={},
        snapshot_mutator=lambda snapshot: snapshot.__setitem__("nextActions", []),
    )
    with pytest.raises(ValueError, match="nextActions"):
        _resolve(fixture)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "preview_ready"),
        ("rollout_state", "public_preview"),
        ("supportability_state", "preview_supported"),
        ("artifact_count", 1),
        ("download_access_posture", "mixed"),
        ("known_issue_summary", "Different issue."),
        ("release_decision_status", "preview_ready"),
    ],
)
def test_stable_decision_live_projection_bindings_are_exact(tmp_path: Path, field: str, value: object) -> None:
    def mutate(decision: dict[str, object]) -> None:
        live = decision["live_release"]
        assert isinstance(live, dict)
        live[field] = value

    fixture = write_authority_fixture(
        tmp_path,
        decision_status="stable_ready",
        decision_mutator=mutate,
    )
    with pytest.raises(ValueError, match="live_release"):
        _resolve(fixture)


def test_empty_review_required_shelf_is_valid_and_projects_no_platforms(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        decision_status="review_required",
        artifacts=[],
        primary_heads={},
    )
    resolved = _resolve(fixture)
    assert resolved.authority["downloadAccessPosture"] == "unavailable"
    assert MODULE.authority_platform_ids(resolved.authority) == []
    packet = MODULE.build_packet(
        resolved.release_payload,
        _linux_gate(),
        _macos_contract(),
        resolved.authority,
        resolved.authority_source,
        resolved.served_mirror,
    )
    assert packet["release_posture"] == "review_required"
    assert packet["phase_label"] == "Release review required"
    assert packet["review_required_banner"].startswith("Release review required.")
    assert packet["primary_head_by_platform"] == {}


def test_served_mirror_must_be_a_portable_absolute_https_url(tmp_path: Path) -> None:
    fixture = write_authority_fixture(tmp_path)
    with pytest.raises(ValueError, match="safe absolute HTTPS"):
        MODULE.resolve_release_authority(
            fixture.current_path,
            registry_commit=fixture.registry_commit,
            expected_release_decision_status="preview_ready",
            served_mirror="/docker/machine-local/manifest.json",
        )


def test_empty_preview_ready_shelf_is_rejected(tmp_path: Path) -> None:
    fixture = write_authority_fixture(
        tmp_path,
        decision_status="preview_ready",
        artifacts=[],
        primary_heads={},
    )
    with pytest.raises(ValueError, match="availablePlatforms"):
        _resolve(fixture)
