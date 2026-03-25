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


def build_wheel():
    """Build a wheel for pip distribution."""
    click.echo("[*] Building wheel...")
    result = subprocess.run(
        [sys.executable, '-m', 'build', '--wheel'],
        check=False,
    )
    if result.returncode != 0:
        click.echo("[!] Wheel build failed. Install build: pip install build", err=True)
        sys.exit(1)

    wheels = list(Path('dist').glob('*.whl'))
    if wheels:
        click.echo(f"[+] Built: {wheels[0]} ({wheels[0].stat().st_size / 1024:.0f} KB)")
    return wheels[0] if wheels else None


@click.command()
@click.option('--clean', is_flag=True, help='Clean build artifacts only')
@click.option('--mode', type=click.Choice(['zipapp', 'pip']), default='zipapp',
              help='Build mode (default: zipapp)')
def main(clean, mode):
    """
    Casts Down build tool.

    \b
    Build single-file executable (fast, ~seconds):
      python build_exe.py

    \b
    Build wheel for pip:
      python build_exe.py --mode pip

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
        output = build_wheel()
        if output:
            click.echo(f"\nInstall:\n  pip install {output}")


if __name__ == '__main__':
    main()
