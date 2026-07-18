from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK = REPO_ROOT / "RELEASE.lock.json"
VERIFIER = REPO_ROOT / "scripts" / "verify_linux_source_lock.py"


class LinuxSourceLockTests(unittest.TestCase):
    def run_verifier(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        command_env = os.environ.copy()
        if env:
            command_env.update(env)
        return subprocess.run(
            ["python3", str(VERIFIER), *args],
            cwd=REPO_ROOT,
            env=command_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )

    def write_lock(self, root: Path, payload: dict) -> Path:
        path = root / "RELEASE.lock.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def inspect(self, path: Path) -> subprocess.CompletedProcess[str]:
        return self.run_verifier("inspect", "--lock", str(path), "--repo-root", str(REPO_ROOT))

    def test_checked_in_lock_is_valid_and_explicitly_review_only(self) -> None:
        completed = self.inspect(LOCK)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("SDK_VERSION\t10.0.103", completed.stdout)
        self.assertEqual(5, completed.stdout.count("REPOSITORY\t"))
        self.assertIn("RELEASE_MANIFEST_STATUS\tunbound_review_placeholder", completed.stdout)
        self.assertIn("RELEASE_EVIDENCE_ELIGIBLE\tfalse", completed.stdout)

    def test_duplicate_keys_and_repository_substitution_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"contract":"a","contract":"b"}\n', encoding="utf-8")
            duplicate_result = self.inspect(duplicate)
            self.assertNotEqual(duplicate_result.returncode, 0, duplicate_result.stdout)
            self.assertIn("duplicate JSON key: contract", duplicate_result.stdout)

            payload = json.loads(LOCK.read_text(encoding="utf-8"))
            payload["repositories"][0]["name"] = "attacker-controlled-repository"
            substituted = self.inspect(self.write_lock(root, payload))
            self.assertNotEqual(substituted.returncode, 0, substituted.stdout)
            self.assertIn("not a required Linux source-build repository", substituted.stdout)

    def test_noncanonical_commit_and_manifest_digest_drift_fail_closed(self) -> None:
        original = json.loads(LOCK.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bad_commit = deepcopy(original)
            bad_commit["repositories"][0]["commit"] = "main"
            commit_result = self.inspect(self.write_lock(root, bad_commit))
            self.assertNotEqual(commit_result.returncode, 0, commit_result.stdout)
            self.assertIn("not a canonical digest", commit_result.stdout)

            bad_manifest = deepcopy(original)
            bad_manifest["releaseManifest"]["sha256"] = "f" * 64
            manifest_result = self.inspect(self.write_lock(root, bad_manifest))
            self.assertNotEqual(manifest_result.returncode, 0, manifest_result.stdout)
            self.assertIn("does not match the checked file", manifest_result.stdout)

    def test_unbound_manifest_cannot_claim_release_evidence(self) -> None:
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        payload["releaseManifest"]["releaseEvidenceEligible"] = True
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.inspect(self.write_lock(Path(temp_dir), payload))
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("must remain ineligible for release evidence", completed.stdout)

    def test_download_verifier_rejects_changed_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dotnet-install.sh"
            path.write_text("#!/usr/bin/env bash\necho changed\n", encoding="utf-8")
            completed = self.run_verifier(
                "verify-file",
                "--path",
                str(path),
                "--sha256",
                "0" * 64,
                "--label",
                "dotnet-install.sh",
            )
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("dotnet-install.sh SHA256 mismatch", completed.stdout)

    def test_package_graph_drift_fails_even_when_the_outer_digest_is_updated(self) -> None:
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
            root = Path(temp_dir)
            package_lock_path = root / "packages.lock.json"
            package_lock = json.loads(
                (REPO_ROOT / payload["nuget"]["packageLocks"][0]["path"]).read_text(encoding="utf-8")
            )
            package_lock["dependencies"]["net10.0"]["Avalonia"]["resolved"] = "11.3.8"
            package_lock_path.write_text(json.dumps(package_lock, indent=2) + "\n", encoding="utf-8")
            entry = payload["nuget"]["packageLocks"][0]
            entry["path"] = package_lock_path.relative_to(REPO_ROOT).as_posix()
            entry["sha256"] = hashlib.sha256(package_lock_path.read_bytes()).hexdigest()
            completed = self.inspect(self.write_lock(root, payload))

        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("direct package graph drift", completed.stdout)

    def test_generated_nuget_config_ignores_ambient_sources_and_maps_only_locked_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packages = root / "packages"
            packages.mkdir()
            output = root / "NuGet.Config"
            ambient = root / "ambient.config"
            ambient.write_text(
                '<configuration><packageSources><add key="attacker" value="https://attacker.invalid/v3/index.json" /></packageSources></configuration>\n',
                encoding="utf-8",
            )
            completed = self.run_verifier(
                "write-nuget-config",
                "--lock",
                str(LOCK),
                "--repo-root",
                str(REPO_ROOT),
                "--rid",
                "linux-x64",
                "--packages-root",
                str(packages),
                "--output",
                str(output),
                env={
                    "NUGET_CONFIG_FILE": str(ambient),
                    "RestoreSources": "https://attacker.invalid/v3/index.json",
                    "CHUMMER_PUBLISHED_FEED_SOURCES": "https://attacker.invalid/v3/index.json",
                },
            )
            self.assertEqual(completed.returncode, 0, completed.stdout)
            config = output.read_text(encoding="utf-8")
            tree = ET.parse(output)

        sources = tree.findall("./packageSources/add")
        self.assertEqual(1, len(sources))
        self.assertEqual("nuget.org", sources[0].attrib["key"])
        self.assertEqual("https://api.nuget.org/v3/index.json", sources[0].attrib["value"])
        patterns = [node.attrib["pattern"] for node in tree.findall("./packageSourceMapping/packageSource/package")]
        self.assertIn("Avalonia", patterns)
        self.assertIn("microsoft.netcore.app.runtime.linux-x64", patterns)
        self.assertNotIn("*", patterns)
        self.assertNotIn("attacker.invalid", config)

    def test_cache_verifier_rejects_tampered_archive_and_unexpected_package(self) -> None:
        original = json.loads(LOCK.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            payload = deepcopy(original)
            cache = root / "packages"
            cache.mkdir()
            self._write_synthetic_cache(payload, "linux-x64", cache)
            source_lock = self.write_lock(root, payload)

            valid = self.run_verifier(
                "verify-nuget-cache",
                "--lock",
                str(source_lock),
                "--repo-root",
                str(REPO_ROOT),
                "--rid",
                "linux-x64",
                "--packages-root",
                str(cache),
            )
            self.assertEqual(valid.returncode, 0, valid.stdout)

            archive = cache / "avalonia" / "11.3.7" / "avalonia.11.3.7.nupkg"
            archive.write_bytes(archive.read_bytes() + b"tampered")
            tampered = self.run_verifier(
                "verify-nuget-cache",
                "--lock",
                str(source_lock),
                "--repo-root",
                str(REPO_ROOT),
                "--rid",
                "linux-x64",
                "--packages-root",
                str(cache),
            )
            self.assertNotEqual(tampered.returncode, 0, tampered.stdout)
            self.assertIn("archive SHA512 drift", tampered.stdout)

            shutil.rmtree(cache)
            cache.mkdir()
            self._write_synthetic_cache(payload, "linux-x64", cache)
            (cache / "unexpected.package" / "1.0.0").mkdir(parents=True)
            unexpected = self.run_verifier(
                "verify-nuget-cache",
                "--lock",
                str(source_lock),
                "--repo-root",
                str(REPO_ROOT),
                "--rid",
                "linux-x64",
                "--packages-root",
                str(cache),
            )
            self.assertNotEqual(unexpected.returncode, 0, unexpected.stdout)
            self.assertIn("package set drift", unexpected.stdout)

    def test_lock_rejects_build_script_drift(self) -> None:
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        payload["buildScript"]["sha256"] = "f" * 64
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.inspect(self.write_lock(Path(temp_dir), payload))
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("buildScript.sha256 does not match", completed.stdout)

    @staticmethod
    def _write_synthetic_cache(payload: dict, rid: str, cache: Path) -> None:
        entry = next(item for item in payload["nuget"]["packageLocks"] if item["runtimeIdentifier"] == rid)
        package_lock = json.loads((REPO_ROOT / entry["path"]).read_text(encoding="utf-8"))
        packages: dict[tuple[str, str], str] = {}
        for nodes in package_lock["dependencies"].values():
            for package_id, node in nodes.items():
                if "contentHash" in node:
                    packages[(package_id.casefold(), node["resolved"].casefold())] = node["contentHash"]
        for implicit in entry["implicitPackages"]:
            packages[(implicit["id"].casefold(), implicit["version"].casefold())] = implicit["contentHash"]

        implicit_by_identity = {
            (item["id"].casefold(), item["version"].casefold()): item for item in entry["implicitPackages"]
        }
        for (package_id, version), content_hash in packages.items():
            package_root = cache / package_id / version
            package_root.mkdir(parents=True)
            archive_bytes = f"synthetic:{package_id}:{version}".encode("utf-8")
            archive_sha = base64.b64encode(hashlib.sha512(archive_bytes).digest()).decode("ascii")
            (package_root / f"{package_id}.{version}.nupkg").write_bytes(archive_bytes)
            (package_root / f"{package_id}.{version}.nupkg.sha512").write_text(archive_sha, encoding="ascii")
            (package_root / ".nupkg.metadata").write_text(
                json.dumps(
                    {
                        "version": 2,
                        "contentHash": content_hash,
                        "source": "https://api.nuget.org/v3/index.json",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            if (package_id, version) in implicit_by_identity:
                implicit_by_identity[(package_id, version)]["archiveSha512"] = archive_sha


if __name__ == "__main__":
    unittest.main()
