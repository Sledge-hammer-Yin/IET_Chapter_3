"""Run or inspect the three Section 3.5 experiment groups."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
CODE = REPO / 'algorithms/LearningAid'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['validate', 'plot', 'gnss', 'uwb', 'io', 'all', 'diagnostics'])
    parser.add_argument('--output', type=Path, help='New directory for figures or a new experiment.')
    parser.add_argument('--models', type=Path, help='Model directory for a new experiment.')
    args = parser.parse_args()
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2', CUDA_VISIBLE_DEVICES='')
    library = Path(sys.prefix) / 'Library/bin'
    if os.name == 'nt' and library.is_dir():
        # Conda DLLs must precede unrelated libraries when VS Code has not activated the environment.
        env['PATH'] = str(library) + os.pathsep + env.get('PATH', '')
    if args.output is not None:
        env['CH3_RESULTS'] = str(args.output.resolve())
    if args.models is not None:
        env['CH3_MODELS'] = str(args.models.resolve())
    # Read only paths here; validation and plotting do not require PyTorch.
    sys.path.insert(0, str(CODE))
    import common
    frozen = REPO / 'results/LearningAid' / common.PROTOCOL['run_id']
    if args.action == 'plot':
        destination = args.output.resolve() if args.output else frozen.with_name('replot_' + common.PROTOCOL['run_id'])
        if destination.exists():
            raise SystemExit('Choose a new plot directory; existing files are kept.')
        if destination == frozen or frozen in destination.parents or destination in frozen.parents:
            raise SystemExit('Plot output must be separate from the frozen results.')
        shutil.copytree(frozen, destination)
        env['CH3_RESULTS'] = str(destination)
        steps = ['generate_results.py']
    elif args.action == 'validate':
        steps = ['validate_results.py']
    else:
        destination = Path(env.get('CH3_RESULTS', str(common.OUT))).resolve()
        if destination == frozen.resolve():
            raise SystemExit('Use --output with a new directory; frozen results are kept.')
        if args.action != 'diagnostics' and not (args.models or env.get('CH3_MODELS')):
            raise SystemExit('Use --models for training or explicitly select the saved model directory.')
        steps = {
            'gnss': ['prepare_gnss.py', 'run_gnss.py'],
            'uwb': ['run_uwb.py'],
            'io': ['prepare_io.py', 'run_io.py'],
            'all': ['prepare_gnss.py', 'run_gnss.py', 'run_uwb.py', 'prepare_io.py', 'run_io.py', 'benchmark_and_diagnostics.py', 'generate_results.py'],
            'diagnostics': ['benchmark_and_diagnostics.py'],
        }[args.action]
    for step in steps:
        subprocess.run([sys.executable, '-u', str(CODE / step)], env=env, check=True)


if __name__ == '__main__':
    main()
