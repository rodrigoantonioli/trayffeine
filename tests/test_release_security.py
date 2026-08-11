from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILES = tuple((ROOT / ".github/workflows").glob("*.yml"))
RELEASE_WORKFLOW = ROOT / ".github/workflows/release.yml"
TAG_VALIDATOR = ROOT / "packaging/windows/validate-release-tag.ps1"


def read_repo_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_all_github_actions_are_pinned_to_commit_shas() -> None:
    offenders: list[str] = []
    action_pattern = re.compile(r"uses:\s*([^\s@]+)@([^\s#]+)")

    for workflow_path in WORKFLOW_FILES:
        workflow = workflow_path.read_text(encoding="utf-8")
        for action, revision in action_pattern.findall(workflow):
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                offenders.append(f"{workflow_path.relative_to(ROOT)}: {action}@{revision}")

    assert offenders == []


def test_release_tag_crosses_into_powershell_only_as_environment_data() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert workflow.count("${{ github.ref_name }}") == 1
    assert "RELEASE_TAG: ${{ github.ref_name }}" in workflow
    assert '$tag = "${{ github.ref_name }}"' not in workflow
    assert '-Version "${{ github.ref_name }}"' not in workflow
    assert "-Version $env:RELEASE_TAG" in workflow
    assert "$tag = $env:RELEASE_TAG" in workflow


def test_release_build_and_publication_have_separate_trust_boundaries() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    build_job, publish_job = workflow.split("  publish-release:\n", maxsplit=1)

    assert "permissions:\n  contents: read" in workflow
    assert "contents: write" not in build_job
    assert "WINGET_GITHUB_PAT" not in build_job
    assert "environment: release" in publish_job
    assert "contents: write" in publish_job
    assert "ref: main" in publish_job
    assert "persist-credentials: false" in publish_job
    assert "release-tooling\\packaging\\winget\\update.ps1" in publish_job


def _run_tag_validator(tag: str) -> subprocess.CompletedProcess[str]:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to validate the real release-tag boundary.")

    return subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(TAG_VALIDATOR),
            "-Tag",
            tag,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "tag",
    ("v1.2.0", "v1.2.0-beta", "v1.2.0-beta1", "v1.2.0-beta.1", "v1.2.0-beta-1"),
)
def test_release_tag_validator_accepts_supported_tags(tag: str) -> None:
    result = _run_tag_validator(tag)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "tag",
    (
        "v1.2",
        "v01.2.0",
        "v1.2.0-rc1",
        "v1.2.0;Get-ChildItem",
        "v1.2.0$(Write-Output injected)",
        "release-v1.2.0",
    ),
)
def test_release_tag_validator_rejects_unsupported_or_executable_text(tag: str) -> None:
    result = _run_tag_validator(tag)

    assert result.returncode != 0
    assert "Unsupported release tag" in f"{result.stdout}\n{result.stderr}"


def test_artifact_workflows_install_hash_locked_dependencies() -> None:
    expectations = {
        ".github/workflows/release.yml": "requirements-windows-build.lock",
        ".github/workflows/preview-build.yml": "requirements-windows-build.lock",
        ".github/workflows/msix-preview.yml": "requirements-msix-build.lock",
    }

    for workflow_path, lock_path in expectations.items():
        workflow = read_repo_text(workflow_path)
        assert f"pip install --require-hashes -r {lock_path}" in workflow
        assert "pip install --upgrade pip" not in workflow

        lock = read_repo_text(lock_path)
        assert " --hash=sha256:" in lock
        assert not re.search(r"(?m)^[a-z0-9_-]+(?:\[[^]]+\])?>=", lock)


def test_release_workflow_verifies_inno_setup_before_installer_build() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    script = read_repo_text("packaging/windows/install-inno-setup.ps1")

    assert "choco install innosetup" not in workflow.lower()
    assert "packaging\\windows\\install-inno-setup.ps1" in workflow
    assert "6.7.1" in script
    assert (
        "431A9F0A8D40D95F8A04C8D98617D2F6E88AC08B65A01BE1F272D6978C3F726AE118F9D7DC04C2B52A429DDEC3D491358A1C8BF2F77DEEE0ABDA8606A975EB61"
        in script
    )
    assert "4D11E8050B6185E0D49BD9E8CC661A7A59F44959A621D31D11033124C4E8A7B0" in script
    assert script.index("Get-FileHash") < script.index("Start-Process")
    assert script.index("Get-AuthenticodeSignature") < script.index("Start-Process")


def test_winget_helper_verifies_pinned_tool_before_token_handoff() -> None:
    script = read_repo_text("packaging/winget/update.ps1")

    assert "https://aka.ms/wingetcreate/latest" not in script
    assert "v1.12.8.0" in script
    assert "8BD738851B524885410112678E3771B341C5C716DE60FBBECB88AB0A363ED85D" in script
    assert script.index("Get-FileHash") < script.index("& $toolPath update")
    assert script.index("Get-AuthenticodeSignature") < script.index("& $toolPath update")
    assert script.index("& $toolPath update") < script.index("-t $GitHubToken")
