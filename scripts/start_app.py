"""Run the app on the host's port, without enabling anonymous usage telemetry."""
import os
from pathlib import Path
import sys


def launch_args(port):
    if not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError('PORT doit être un entier entre 1 et 65535.')
    app = Path(__file__).resolve().parents[1] / 'app.py'
    return [sys.executable, '-m', 'streamlit', 'run', str(app),
            '--server.address=0.0.0.0', f'--server.port={int(port)}',
            '--server.headless=true', '--browser.gatherUsageStats=false']


if __name__ == '__main__':
    try:
        args = launch_args(os.environ.get('PORT', '8501'))
    except ValueError as exc:
        sys.exit(str(exc))
    os.execv(sys.executable, args)
