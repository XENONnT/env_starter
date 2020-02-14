#!/usr/bin/env python
import argparse
import os
import os.path as osp
import shutil
import subprocess
import sys
import tempfile
import time


JOB_HEADER = """#!/bin/bash
#SBATCH --job-name=straxlab
#SBATCH --output={log_fn}
#SBATCH --error={log_fn}
#SBATCH --account=pi-lgrandi
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={n_cpu}
#SBATCH --mem-per-cpu={mem_per_cpu}
#SBATCH --time={max_hours}:00:00
{extra_header}

echo Starting jupyter job

"""

GPU_HEADER = """\
#SBATCH --partition=gpu2
#SBATCH --gres=gpu:1

module load cuda/9.1
"""

CPU_HEADER = """\
#SBATCH --qos {partition}
#SBATCH --partition {partition}
#SBATCH --reservation=xenon_notebook
"""

# This is only if the user is NOT starting the singularity container
# (for singularity, starting jupyter is done in _xentenv_inner)
START_JUPYTER = """
# Arcane conda setup instructions
if [ -f "{conda_dir}/etc/profile.d/conda.sh" ]; then
    echo "Using slightly less magic conda setup"
    . "{conda_dir}/etc/profile.d/conda.sh"
else
    echo "Using totally unmagical conda setup"
    export PATH="{conda_dir}/bin:$PATH"
fi
{conda_dir}/bin/conda activate {env_name}
source {conda_dir}/bin/activate {env_name}

JUP_PORT=$(( 15000 + (RANDOM %= 5000) ))
JUP_HOST=$(hostname -i)
{conda_dir}/envs/{env_name}/bin/jupyter notebook --no-browser --port=$JUP_PORT --ip=$JUP_HOST 2>&1
"""

SUCCESS_MESSAGE = """
Success! If you have linux, execute the following command on your laptop:

ssh -fN -L {port}:{ip}:{port} {username}@dali-login2.rcc.uchicago.edu && sensible-browser http://localhost:{port}/{token}

If you have a mac, instead do:

ssh -fN -L {port}:{ip}:{port} {username}@dali-login2.rcc.uchicago.edu && open http://localhost:{port}/{token}

Happy strax analysis, {username}!
"""


# Dir for temporary files
# Must be shared between batch queue and login node
# (i.e. not /tmp)
TMP_DIR = '/project2/lgrandi/xenonnt/development/.tmp_for_jupyter_job_launcher'


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Start a strax jupyter notebook server on the dali batch queue')
    parser.add_argument('--copy_tutorials',
        action='store_true',
        help='Copy tutorials to ~/strax_tutorials (if it does not exist)')
    parser.add_argument('--partition',
        default='xenon1t', type=str,
        help="RCC/DALI partition to use. Try dali, broadwl, or xenon1t.")
    parser.add_argument('--timeout',
        default=120, type=int,
        help='Seconds to wait for the jupyter server to start')
    parser.add_argument('--cpu',
        default=1, type=int,
        help='Number of CPUs to request.')
    parser.add_argument('--ram',
        default=4480, type=int,
        help='MB of RAM to request')
    parser.add_argument('--conda_path',
        default='<INFER>',
        help="For non-singularity environments, path to conda binary to use."
             "Default is to infer this from running 'which conda'.")
    parser.add_argument('--env_starter_path',
        default='/project2/lgrandi/xenonnt/development',
        help="Directory containing the xnt_env script for starting the environment")
    parser.add_argument('--gpu',
        action='store_true', default=False,
        help='Request to run on a GPU partition. Limits runtime to 2 hours.')
    parser.add_argument('--env',
        default='nt_singularity',
        help='Environment to activate; defaults to "nt_singularity" '
             'to load XENONnT singularity container. '
             'Other arguments are passed to "conda activate" '
             "(and don't load a container).")
    parser.add_argument('--container',
        default='/project2/lgrandi/xenonnt/singularity-images/xenonnt-development.simg',
        help='Singularity container to load'
             'See wiki page https://xe1t-wiki.lngs.infn.it/doku.php?id=xenon:xenonnt:dsg:computing:environment_tracking'
             'Default container: "latest"')
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.copy_tutorials:
        dest = osp.expanduser('~/strax_tutorials')
        if osp.exists(dest):
            print_flush("NOT copying tutorials, folder already exists")
        else:
            shutil.copytree(
                '/dali/lgrandi/strax/straxen/notebooks/tutorials',
                dest)

    if args.env == 'nt_singularity':
        start_env = os.path.join(args.env_starter_path, 'xnt_env') \
                    + ' -j ' + args.container
        batch_job = JOB_HEADER + start_env
    else:
        if args.conda_path == '<INFER>':
            print_flush("Autoinferring conda path")
            conda_path = subprocess.check_output(['which', 'conda']).strip()
            conda_path = conda_path.decode()
        else:
            conda_path = args.conda_path

        conda_dir = os.path.dirname(conda_path)
        conda_dir = os.path.abspath(os.path.join(conda_dir, os.pardir))
        print_flush("Using conda from %s instead of singularity container."
                    % conda_dir)

        batch_job = (
            JOB_HEADER
            + START_JUPYTER.format(conda_dir=conda_dir,
                                   env_name=args.env))

    url_cache_fn = osp.join(
        os.environ['HOME'],
        '.last_jupyter_url')
    username = os.environ['USER']

    # Check if a job is already running
    q = subprocess.check_output(['squeue', '-u', username])
    for line in q.decode().splitlines():
        if 'straxlab' in line:
            job_id = int(line.split()[0])
            print_flush("You still have a running job with id %d, "
                        "trying to retrieve the URL." % job_id)
            with open(url_cache_fn) as f:
                url = f.read()
            break

    else:
        print_flush("Submitting a new jupyter job")

        job_fn = tempfile.NamedTemporaryFile(
            delete=False, dir=TMP_DIR).name
        log_fn = tempfile.NamedTemporaryFile(
            delete=False, dir=TMP_DIR).name
        with open(job_fn, mode='w') as f:
            f.write(batch_job.format(
                log_fn=log_fn,
                max_hours=2 if args.gpu else 24,
                extra_header=(
                    GPU_HEADER if args.gpu
                    else CPU_HEADER.format(partition=args.partition)),
                n_cpu=args.cpu,
                mem_per_cpu=int(args.ram / args.cpu)))
        make_executable(job_fn)
        print_flush("\tSubmitting sbatch %s" % job_fn)
        result = subprocess.check_output(['sbatch', job_fn])
        print_flush("\tsbatch returned: %s" % result)
        job_id = int(result.decode().split()[-1])
        print_flush("\tYou have job id %d" % job_id)

        print_flush("Waiting for your job to start")
        print_flush("\tStarting to look for logfile %s" % log_fn)
        while not osp.exists(log_fn):
            print_flush("\tstill waiting...")
            time.sleep(2)

        print_flush("Job started. Parsing logfile for jupyter url")
        lines_shown = 0
        slept = 0
        url = None
        while url is None and slept < args.timeout:
            with open(log_fn, mode='r') as f:
                content = f.readlines()
                for line_i, line in enumerate(content):
                    if line_i >= lines_shown:
                        print_flush('\t' + line.rstrip())
                        lines_shown += 1
                    if 'http' in line and 'sylabs' not in line:
                        url = line.split()[-1]
                        break
                else:
                    time.sleep(2)
                    slept += 2
        if url is None:
            raise RuntimeError("Jupyter did not start inside your job!")

        with open(url_cache_fn, mode='w') as f:
            f.write(url)
        print_flush("Jupyter started. Dumped URL %s to cache file" % url)

    print_flush("Parsing URL %s" % url)
    ip, port = url.split('/')[2].split(':')
    if 'token' in url:
        token = url.split('?')[1].split('=')[1]
        token = '?token=' + token
    else:
        token = ''

    print_flush(SUCCESS_MESSAGE.format(ip=ip, port=port, token=token, username=username))


def print_flush(x):
    """Does print(x, flush=True), also in python 2.x"""
    print(x)
    sys.stdout.flush()


def make_executable(path):
    """Make the file at path executable, see """
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2    # copy R bits to X
    os.chmod(path, mode)


if __name__ == '__main__':
    main()
