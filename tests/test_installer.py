"""Exercise the public Go installer without network access or global installs."""

import hashlib
import os
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "install" / "9l.run.sh"


def executable(path, content):
    path.write_text(content)
    path.chmod(0o755)


@pytest.fixture
def installer(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    commands = tmp_path / "commands"
    commands.mkdir()
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    destination = tmp_path / "Go tools's bin"
    requests = tmp_path / "requests"
    executable(
        commands / "uname",
        '#!/bin/sh\ncase "$1" in -s) echo "$INSTALLER_TEST_OS";; -m) echo "$INSTALLER_TEST_ARCH";; esac\n',
    )
    executable(
        commands / "curl",
        f"#!{sys.executable}\n"
        "import os, pathlib, shutil, sys\n"
        "args = sys.argv[1:]\n"
        "url = args[args.index('-o') - 1]\n"
        "assert url.startswith('https://github.com/Quality-Max/9lives-runner/releases/download/v0.1.1/')\n"
        "with open(os.environ['INSTALLER_TEST_REQUESTS'], 'a') as log: log.write(url + '\\n')\n"
        "shutil.copyfile(pathlib.Path(os.environ['INSTALLER_TEST_ASSETS']) / url.rsplit('/', 1)[1], "
        "args[args.index('-o') + 1])\n",
    )
    environment = {
        **os.environ,
        "PATH": f"{commands}{os.pathsep}{os.environ['PATH']}",
        "TMPDIR": str(temporary),
        "NINELIVES_VERSION": "v0.1.1",
        "NINELIVES_INSTALL_DIR": str(destination),
        "INSTALLER_TEST_OS": "Darwin",
        "INSTALLER_TEST_ARCH": "arm64",
        "INSTALLER_TEST_ASSETS": str(assets),
        "INSTALLER_TEST_REQUESTS": str(requests),
    }

    def package(bundle="9l-darwin-arm64", missing=None, version="0.1.1"):
        source = tmp_path / bundle
        source.mkdir()
        executable(source / "9l", f"#!/bin/sh\nprintf '9l {version} (Go runner)\\n'\n")
        (source / "LICENSE").write_text("Apache-2.0 fixture\n")
        (source / "NOTICE").write_text("Release notice fixture\n")
        archive = assets / f"{bundle}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            for artifact in source.iterdir():
                if artifact.name != missing:
                    tar.add(artifact, arcname=f"{bundle}/{artifact.name}")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (assets / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
        return source

    def run():
        return subprocess.run(["sh", str(SCRIPT)], env=environment, capture_output=True, text=True, timeout=30, check=False)

    return package, run, environment, destination, assets, requests, temporary


@pytest.mark.parametrize(
    ("system", "architecture", "bundle"),
    [
        ("Darwin", "arm64", "9l-darwin-arm64"),
        ("Darwin", "x86_64", "9l-darwin-amd64"),
        ("Linux", "aarch64", "9l-linux-arm64"),
        ("Linux", "x86_64", "9l-linux-amd64"),
    ],
)
def test_installs_verified_platform_and_prints_usable_path(installer, system, architecture, bundle):
    package, run, environment, destination, _, requests, temporary = installer
    environment.update(INSTALLER_TEST_OS=system, INSTALLER_TEST_ARCH=architecture)
    source = package(bundle)
    result = run()
    assert result.returncode == 0, result.stderr
    assert requests.read_text().splitlines() == [
        f"https://github.com/Quality-Max/9lives-runner/releases/download/v0.1.1/{bundle}.tar.gz",
        "https://github.com/Quality-Max/9lives-runner/releases/download/v0.1.1/SHA256SUMS",
    ]
    for artifact in ("9l", "LICENSE", "NOTICE"):
        assert (destination / artifact).read_bytes() == (source / artifact).read_bytes()
    assert os.access(destination / "9l", os.X_OK)
    path_line = next(line.strip() for line in result.stdout.splitlines() if line.strip().startswith("export PATH="))
    selected = subprocess.run(
        ["sh", "-c", path_line + "; command -v 9l; 9l --version"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert selected.returncode == 0, selected.stderr
    assert selected.stdout.splitlines() == [str(destination / "9l"), "9l 0.1.1 (Go runner)"]
    assert list(temporary.iterdir()) == []
    assert not list(destination.glob(".9l-install.*"))


@pytest.mark.parametrize("checksum", ["mismatch", "missing", "duplicate"])
def test_bad_checksums_never_install_or_replace_a_binary(installer, checksum):
    package, run, _, destination, assets, _, temporary = installer
    package()
    destination.mkdir()
    original = "#!/bin/sh\necho '9l 0.0.0 (Go runner)'\n"
    executable(destination / "9l", original)
    manifest = assets / "SHA256SUMS"
    if checksum == "mismatch":
        manifest.write_text("0" * 64 + "  9l-darwin-arm64.tar.gz\n")
    elif checksum == "missing":
        manifest.write_text("0" * 64 + "  unrelated.tar.gz\n")
    else:
        manifest.write_text(manifest.read_text() * 2)
    result = run()
    assert result.returncode != 0
    assert "checksum" in result.stderr
    assert (destination / "9l").read_text() == original
    assert list(destination.iterdir()) == [destination / "9l"]
    assert list(temporary.iterdir()) == []


def test_missing_release_artifact_never_installs(installer):
    package, run, _, destination, _, _, temporary = installer
    package(missing="NOTICE")
    result = run()
    assert result.returncode != 0
    assert "missing a regular NOTICE" in result.stderr
    assert not destination.exists()
    assert list(temporary.iterdir()) == []


def test_wrong_release_identity_preserves_existing_go_binary(installer):
    package, run, _, destination, _, _, temporary = installer
    package(version="0.1.0")
    destination.mkdir()
    original = "#!/bin/sh\necho '9l 0.0.0 (Go runner)'\n"
    executable(destination / "9l", original)
    result = run()
    assert result.returncode != 0
    assert "version does not match" in result.stderr
    assert (destination / "9l").read_text() == original
    assert list(temporary.iterdir()) == []


@pytest.mark.parametrize("symlink", [False, True])
def test_preserves_python_executable_and_symlinks(installer, symlink):
    _, run, _, destination, assets, requests, _ = installer
    destination.mkdir()
    python_cli = assets / "python-cli"
    original = "#!/bin/sh\necho '9lives 0.2.1'\n"
    executable(python_cli, original)
    if symlink:
        (destination / "9l").symlink_to(python_cli)
    else:
        executable(destination / "9l", original)
    result = run()
    assert result.returncode != 0
    assert "choose a separate NINELIVES_INSTALL_DIR" in result.stderr
    assert python_cli.read_text() == original
    assert (destination / "9l").read_text() == original
    assert (destination / "9l").is_symlink() == symlink
    assert not requests.exists()


def test_can_update_its_existing_go_binary(installer):
    package, run, _, destination, _, _, _ = installer
    source = package()
    destination.mkdir()
    executable(destination / "9l", "#!/bin/sh\necho '9l 0.0.0 (Go runner)'\n")
    assert run().returncode == 0
    assert (destination / "9l").read_bytes() == (source / "9l").read_bytes()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("INSTALLER_TEST_OS", "Windows_NT"),
        ("INSTALLER_TEST_ARCH", "riscv64"),
        ("NINELIVES_VERSION", "v0x1x1"),
        ("NINELIVES_VERSION", "v0.1.1\nextra-line"),
        ("NINELIVES_VERSION", "../../main"),
        ("NINELIVES_INSTALL_DIR", "relative/bin"),
    ],
)
def test_rejects_unsupported_targets_before_download(installer, key, value):
    _, run, environment, _, _, requests, _ = installer
    environment[key] = value
    assert run().returncode != 0
    assert not requests.exists()


def test_python_integration_commands_ignore_foreign_9l(tmp_path):
    """A Go executable earlier on PATH must not change Python integration identity."""
    executable(tmp_path / "9l", "#!/bin/sh\necho 'wrong engine' >&2\nexit 97\n")
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "PYTHONPATH": str(ROOT / "src"),
    }
    hook_entries = [
        line.removeprefix("  entry: ")
        for line in (ROOT / ".pre-commit-hooks.yaml").read_text().splitlines()
        if line.startswith("  entry: ")
    ]
    action_entries = [
        line.strip().split(' "${specs[@]}"')[0]
        for line in (ROOT / "action" / "action.yml").read_text().splitlines()
        if "ninelives.cli" in line
    ]
    assert len(hook_entries) == len(action_entries) == 2
    for entry in hook_entries + action_entries:
        command = shlex.split(entry)
        assert command[1:3] == ["-m", "ninelives.cli"]
        result = subprocess.run(
            [sys.executable, *command[1:3], "--version"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "9lives 0.2.1"
