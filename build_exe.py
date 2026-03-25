#!/usr/bin/env python3
"""
Cross-platform build script for casts_down.

Two build modes:
  --mode zipapp  (default) Fast build using Python zipapp. Requires Python on target.
  --mode pip     Package as wheel for pip distribution.
"""

import platform
import shutil
import subprocess
import sys
import tempfile
import zipapp
from pathlib import Path

import click


def get_platform_info():
    system = platform.system().lower()
    machine = platform.machine().lower()
    platform_map = {'darwin': 'macos', 'linux': 'linux', 'windows': 'windows'}
    arch_map = {'x86_64': 'x64', 'amd64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}
    return platform_map.get(system, system), arch_map.get(machine, machine)


def clean_build():
    """Clean build artifacts."""
    for d in ['build', 'dist', 'release']:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p)
            click.echo(f"  Removed {d}/")


def build_zipapp():
    """
    Build a .pyz executable using zipapp (stdlib, no extra deps).
    Bundles only casts_down/ package. Dependencies must be installed on target.
    """
    os_name, arch = get_platform_info()
    output_name = f"casts-down-{os_name}-{arch}.pyz"

    release_dir = Path('release')
    release_dir.mkdir(exist_ok=True)
    output_path = release_dir / output_name

    click.echo(f"[*] Building {output_name}...")

    # Create a temp staging directory
    with tempfile.TemporaryDirectory() as tmpdir:
        staging = Path(tmpdir)

        # Copy the package
        shutil.copytree('casts_down', staging / 'casts_down')

        # Create __main__.py entry point
        main_py = staging / '__main__.py'
        main_py.write_text(
            "from casts_down.cli import main\n"
            "main()\n"
        )

        # Build the zipapp
        # Use the exact Python that's running this build script
        python_path = sys.executable
        zipapp.create_archive(
            staging,
            target=output_path,
            interpreter=python_path,
            compressed=True,
        )

    output_path.chmod(0o755)
    size_kb = output_path.stat().st_size / 1024
    click.echo(f"[+] Built: {output_path} ({size_kb:.0f} KB)")
    return output_path


def build_dist():
    """Build wheel + sdist for PyPI distribution."""
    click.echo("[*] Building wheel + sdist...")
    result = subprocess.run(
        [sys.executable, '-m', 'build'],
        check=False,
    )
    if result.returncode != 0:
        click.echo("[!] Build failed. Install build: pip install build", err=True)
        sys.exit(1)

    artifacts = list(Path('dist').glob('*'))
    for a in artifacts:
        click.echo(f"[+] {a.name} ({a.stat().st_size / 1024:.0f} KB)")
    return artifacts


def publish_pypi(test: bool = False):
    """Upload dist/* to PyPI using twine.

    Authentication via environment variables:
      TWINE_USERNAME  - PyPI username (use __token__ for API tokens)
      TWINE_PASSWORD  - PyPI API token
    Or for TestPyPI:
      TEST_PYPI_TOKEN - TestPyPI API token
    """
    # Check for API token
    import os
    if test:
        token = os.environ.get('TEST_PYPI_TOKEN') or os.environ.get('TWINE_PASSWORD')
        env_name = 'TEST_PYPI_TOKEN'
    else:
        token = os.environ.get('PYPI_TOKEN') or os.environ.get('TWINE_PASSWORD')
        env_name = 'PYPI_TOKEN'

    if not token:
        target = 'TestPyPI' if test else 'PyPI'
        click.echo(f"[!] No {target} credentials found.", err=True)
        click.echo(f"    Set environment variable before publishing:", err=True)
        click.echo(f"    export {env_name}=pypi-xxxxxxxx", err=True)
        click.echo(f"    Or: export TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-xxxxxxxx", err=True)
        sys.exit(1)

    # Set twine env vars from our token
    env = os.environ.copy()
    env['TWINE_USERNAME'] = '__token__'
    env['TWINE_PASSWORD'] = token

    dist_files = list(Path('dist').glob('*'))
    if not dist_files:
        click.echo("[!] No dist/ files found. Run build first: python build_exe.py --mode pip", err=True)
        sys.exit(1)

    # Check packages first
    click.echo("[*] Checking packages...")
    check = subprocess.run(
        [sys.executable, '-m', 'twine', 'check'] + [str(f) for f in dist_files],
        check=False,
    )
    if check.returncode != 0:
        click.echo("[!] Package check failed", err=True)
        sys.exit(1)

    # Upload
    repo_arg = ['--repository', 'testpypi'] if test else []
    target = 'TestPyPI' if test else 'PyPI'
    click.echo(f"[*] Uploading to {target}...")
    upload = subprocess.run(
        [sys.executable, '-m', 'twine', 'upload'] + repo_arg + [str(f) for f in dist_files],
        check=False,
        env=env,
    )
    if upload.returncode != 0:
        click.echo(f"[!] Upload to {target} failed", err=True)
        sys.exit(1)

    click.echo(f"[+] Published to {target}!")


@click.command()
@click.option('--clean', is_flag=True, help='Clean build artifacts only')
@click.option('--mode', type=click.Choice(['zipapp', 'pip']), default='zipapp',
              help='Build mode (default: zipapp)')
@click.option('--publish', is_flag=True, help='Upload dist/* to PyPI after building')
@click.option('--test-pypi', is_flag=True, help='Upload to TestPyPI instead of PyPI')
def main(clean, mode, publish, test_pypi):
    """
    Casts Down build tool.

    \b
    Build single-file executable (fast, <1s):
      python build_exe.py

    \b
    Build wheel + sdist for PyPI:
      python build_exe.py --mode pip

    \b
    Build and publish to PyPI:
      python build_exe.py --mode pip --publish

    \b
    Build and publish to TestPyPI:
      python build_exe.py --mode pip --publish --test-pypi

    \b
    Clean:
      python build_exe.py --clean
    """
    os_name, arch = get_platform_info()
    click.echo(f"Casts Down Build ({os_name}-{arch}, Python {sys.version.split()[0]})\n")

    if clean:
        clean_build()
        click.echo("[+] Clean complete")
        return

    clean_build()

    if mode == 'zipapp':
        output = build_zipapp()
        click.echo(f"\nUsage:\n  ./{output} <URL>\n  ./{output} --help")
        click.echo("\nNote: Requires Python 3.10+ and dependencies installed on target.")
    else:
        build_dist()
        if publish:
            publish_pypi(test=test_pypi)
        else:
            click.echo("\nTo publish:\n  python build_exe.py --mode pip --publish")
            click.echo("  python build_exe.py --mode pip --publish --test-pypi")


if __name__ == '__main__':
    main()
