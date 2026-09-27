import os
import subprocess
import sys


def test_cli_dry_run_prints_report():
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [sys.executable, "-m", "ibm_espp_monitor", "--dry-run"],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    assert "IBM SELL MONITOR" in result.stdout
    assert "Not a price prediction." in result.stdout
