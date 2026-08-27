import argparse
import json
import os
import os.path as osp
import shutil
import subprocess
import stat
import sys
import time
from random import choices
from string import ascii_lowercase
import getpass
import socket
from typing import List
from urllib.parse import urlsplit, urlunsplit

def _get_lc_nodes(partition: str) -> List[str]:
    """
    Get the list of 'lc' (loosely coupled) nodes in the specified partition.
    
    Args:
        partition (str): The partition to check for 'lc' nodes.
    
    Returns:
        List[str]: The list of 'lc' node names.
    """
    cmd = f"nodestatus {partition}"
    try:
        output = subprocess.check_output(cmd, universal_newlines=True, shell=True)
        lines = output.split("\n")
        lc_nodes = []
        for line in lines:
            columns = line.split()
            if len(columns) >= 4 and "," in columns[3]:
                features = columns[3].split(",")
                if "lc" in features:
                    lc_nodes.append(columns[0])
        return lc_nodes
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while executing nodestatus: {e}")
        return []

# check which machine I am on
hostname = socket.gethostname()
full_hostname = hostname.replace(".rcc.local", ".rcc.uchicago.edu")
# automatically set default partition based on hostname
if 'midway3' in hostname:
    default_partition = 'lgrandi'
    on_midway3 = True
else:
    default_partition = 'xenon1t'
    on_midway3 = False

# the path to this file
ENVSTARTER_PATH = osp.dirname(osp.abspath(__file__))
# where you want to store sbatch and log files
OUTPUT_DIR_DALI = osp.expanduser('/dali/lgrandi/%s/straxlab'%(getpass.getuser()))
OUTPUT_DIR_MIDWAY = osp.expanduser('~/straxlab')
OUTPUT_DIR = {
    'lgrandi': OUTPUT_DIR_MIDWAY,
    'build': OUTPUT_DIR_MIDWAY,
    'caslake': OUTPUT_DIR_MIDWAY,
    'dali': OUTPUT_DIR_DALI,
    'xenon1t': OUTPUT_DIR_MIDWAY,
    'broadwl': OUTPUT_DIR_MIDWAY,
    'kicp': OUTPUT_DIR_MIDWAY,
    'bigmem2': OUTPUT_DIR_MIDWAY,
    'gpu2': OUTPUT_DIR_MIDWAY,
}
ACTIVE_JOB_STATES = {
    'PENDING', 'RUNNING', 'CONFIGURING', 'COMPLETING', 'SUSPENDED',
    'RESIZING', 'REQUEUED', 'REQUEUE_FED', 'REQUEUE_HOLD', 'SIGNALING',
    'STAGE_OUT',
}

# default home directories
HOME_MIDWAY = os.environ['HOME']
HOME_DALI = osp.expanduser('/dali/lgrandi/%s'%(getpass.getuser()))
HOME = {
    'lgrandi': HOME_MIDWAY,
    'build': HOME_MIDWAY,
    'caslake': HOME_MIDWAY,
    'dali': HOME_DALI,
    'xenon1t': HOME_MIDWAY,
    'broadwl': HOME_MIDWAY,
    'kicp': HOME_MIDWAY,
    'bigmem2': HOME_MIDWAY,
    'gpu2': HOME_MIDWAY,
}
SHELL_SCRIPT = 'start_notebook.sh'

def printflush(x):
    """Does print(x, flush=True), also in python 2.x"""
    print(x)
    sys.stdout.flush()


def _job_info_path(partition, job_id):
    """Legacy per-job metadata path kept for backward-compatible reads."""
    return osp.join(OUTPUT_DIR[partition], 'jobs', f'{job_id}.json')


def get_job_state(job_id):
    commands = [
        ['squeue', '-h', '-j', str(job_id), '-o', '%T'],
        ['sacct', '-n', '-X', '-j', str(job_id), '-o', 'State'],
    ]
    for command in commands:
        try:
            output = subprocess.check_output(command, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            continue
        states = output.decode().strip().splitlines()
        if states:
            return states[0].strip().split()[0].rstrip('+')
    return 'UNKNOWN'


def check_job_state(job_id, log_fn):
    state = get_job_state(job_id)
    if state != 'UNKNOWN' and state not in ACTIVE_JOB_STATES:
        raise RuntimeError(
            f'Jupyter job {job_id} entered state {state} before a URL was found. '
            f'Expected log: {log_fn}'
        )
    return state


def get_straxlab_jobs(username):
    command = ['squeue', '-h', '-u', username, '-n', 'straxlab',
               '-o', '%i|%T|%N|%R']
    output = subprocess.check_output(command).decode().splitlines()
    jobs = []
    for line in output:
        job_id, state, node, reason = line.split('|', 3)
        jobs.append({
            'job_id': int(job_id),
            'state': state,
            'node': node or reason,
        })
    return jobs


def get_slurm_log_path(job_id):
    try:
        output = subprocess.check_output(
            ['scontrol', 'show', 'job', '-o', str(job_id)],
            stderr=subprocess.DEVNULL,
        ).decode()
    except (OSError, subprocess.CalledProcessError):
        return None
    for item in output.split():
        if item.startswith('StdOut='):
            return item.split('=', 1)[1]
    return None


def read_jupyter_url(log_fn):
    if not log_fn:
        return None
    try:
        with open(log_fn, mode='r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return None

    url = None
    for line in lines:
        if 'http' in line and not any(excluded in line for excluded in ['sylabs', 'github.com']):
            url = line.split()[-1].replace('\x1b[0m', '')
    return url


def _jupyter_jobs_cache_path(partition):
    return osp.join(HOME[partition], '.last_jupyter_jobs')


def _normalise_job_info(value):
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        return {'url': value}
    return {}


def _load_jobs_cache_file(partition):
    path = _jupyter_jobs_cache_path(partition)
    if not osp.exists(path):
        return {}
    try:
        with open(path, mode='r', encoding='utf-8') as f:
            saved = json.load(f)
    except (OSError, ValueError, TypeError):
        print_flush(f'Warning: could not read Jupyter job cache {path}')
        return {}
    return saved if isinstance(saved, dict) else {}


def load_job_info(partition, job_id):
    info = load_cached_jobs(partition).get(int(job_id), {})

    # Merge metadata written by older versions if it still exists.
    path = _job_info_path(partition, job_id)
    if osp.exists(path):
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                legacy_info = _normalise_job_info(json.load(f))
        except (OSError, ValueError, TypeError):
            legacy_info = {}
        legacy_info.update(info)
        info = legacy_info
    return info


def _write_jobs_cache(partition, cached_jobs):
    path = _jupyter_jobs_cache_path(partition)
    os.makedirs(osp.dirname(path), mode=stat.S_IRWXU, exist_ok=True)
    saved = {}
    for job_id, info in cached_jobs.items():
        try:
            saved[str(int(job_id))] = _normalise_job_info(info)
        except (TypeError, ValueError):
            continue

    temporary = f'{path}.{os.getpid()}.tmp'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                 stat.S_IRUSR | stat.S_IWUSR)
    try:
        with os.fdopen(fd, mode='w', encoding='utf-8') as f:
            json.dump({job_id: saved[job_id] for job_id in sorted(saved)},
                      f, indent=2, sort_keys=True)
            f.write('\n')
        os.replace(temporary, path)
    finally:
        if osp.exists(temporary):
            os.remove(temporary)


def save_job_info(partition, job_id, info):
    cached_jobs = load_cached_jobs(partition)
    saved = load_job_info(partition, job_id)
    saved.update(info)
    cached_jobs[int(job_id)] = saved
    save_cached_jobs(partition, cached_jobs)


def load_cached_jobs(partition):
    cached_jobs = {}
    saved = _load_jobs_cache_file(partition)
    for job_id, info in saved.items():
        try:
            cached_jobs[int(job_id)] = _normalise_job_info(info)
        except (TypeError, ValueError):
            continue

    legacy_path = osp.join(HOME[partition], '.last_jupyter_url')
    if osp.exists(legacy_path):
        try:
            with open(legacy_path, mode='r', encoding='utf-8') as f:
                job_id, url = f.read().split()
            cached_jobs.setdefault(int(job_id), {'url': url})
        except (OSError, ValueError):
            print_flush(f'Warning: could not read legacy Jupyter URL cache {legacy_path}')
    return cached_jobs


def save_cached_jobs(partition, cached_jobs):
    _write_jobs_cache(partition, cached_jobs)

    legacy_path = osp.join(HOME[partition], '.last_jupyter_url')
    if osp.exists(legacy_path):
        os.remove(legacy_path)


def refresh_cached_jobs(partition):
    cached_jobs = load_cached_jobs(partition)
    try:
        active_job_ids = {
            job['job_id'] for job in get_straxlab_jobs(os.environ['USER'])
        }
    except (OSError, subprocess.CalledProcessError):
        print_flush('Warning: could not query Slurm; keeping the Jupyter job cache unchanged')
        return cached_jobs

    cached_jobs = {
        job_id: info for job_id, info in cached_jobs.items()
        if job_id in active_job_ids
    }
    for job_id in active_job_ids:
        if job_id not in cached_jobs:
            info = load_job_info(partition, job_id)
            if info:
                cached_jobs[job_id] = info
    save_cached_jobs(partition, cached_jobs)
    return cached_jobs


def get_cached_url(partition, job_id):
    return load_cached_jobs(partition).get(int(job_id), {}).get('url')

def tunnel_command(url, username, alias=None):
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError:
        return None
    if parsed.hostname is None or port is None:
        return None

    local_url = urlunsplit((
        parsed.scheme or 'http', f'localhost:{port}',
        parsed.path or '/', parsed.query, parsed.fragment,
    ))
    if alias:
        return (
        f'\n\tFor linux: ssh -fN -L {port}:{parsed.hostname}:{port} {alias} && sensible-browser "{local_url}\n\n'
        f'\tFor macOS: ssh -fN -L {port}:{parsed.hostname}:{port} {alias} && open "{local_url}"\n\n'
        f'\tFor Windows: ssh -fN -L {port}:{parsed.hostname}:{port} {alias}; Start-Process "{local_url}"\n'
        )
    else:
        return (
            f'\n\tFor linux: ssh -fN -L {port}:{parsed.hostname}:{port} {username}@{full_hostname} && sensible-browser "{local_url}\n\n'
            f'\tFor macOS: ssh -fN -L {port}:{parsed.hostname}:{port} {username}@{full_hostname} && open "{local_url}"\n\n'
            f'\tFor Windows: ssh -fN -L {port}:{parsed.hostname}:{port} {username}@{full_hostname}; Start-Process "{local_url}"\n'
        )


def list_straxlab_jobs(partition, alias):
    username = os.environ['USER']
    jobs = get_straxlab_jobs(username)
    if not jobs:
        print_flush('No active straxlab jobs found.')
        return

    print_flush(f'Found {len(jobs)} active straxlab job(s).')
    for job in jobs:
        job_id = job['job_id']
        info = load_job_info(partition, job_id)
        log_fn = info.get('log_path') or get_slurm_log_path(job_id)
        url = info.get('url') or read_jupyter_url(log_fn)
        if url is None:
            url = get_cached_url(partition, job_id)

        print_flush(f'\nJob {job_id} ({job["state"]})')
        print_flush(f'\tNode: {job["node"]}')
        print_flush(f'\tContainer: {info.get("container", "unknown")}')
        print_flush(f'\tLog: {log_fn or "unknown"}')
        if url is None:
            print_flush('\tURL not available yet.')
            continue

        print_flush(f'\tURL: {url}')
        command = tunnel_command(url, username, alias)
        if command is not None:
            print_flush('\tOpen from your laptop with:')

            print_flush(f'\t{command}')


SPLASH_SCREEN = r"""
 __   __ ______  _   _   ____   _   _      _______ 
 \ \ / /|  ____|| \ | | / __ \ | \ | |    |__   __|
  \ V / | |__   |  \| || |  | ||  \| | _ __  | |   
   > <  |  __|  | . ` || |  | || . ` || '_ \ | |   
  / . \ | |____ | |\  || |__| || |\  || | | || |   
 /_/ \_\|______||_| \_| \____/ |_| \_||_| |_||_|   

                    The UChicago Analysis Center

"""

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

export NUMEXPR_MAX_THREADS={n_cpu}
echo Starting jupyter job

"""

GPU_HEADER = """\
#SBATCH --partition=gpu2
#SBATCH --gres=gpu:1

module load cuda/10.1
"""

CPU_HEADER = """\
#SBATCH --qos {qos}
#SBATCH --partition {partition}
{reservation}
"""


# This is only if the user is NOT starting the singularity container
# (for singularity, starting jupyter is done in _xentenv_inner)
START_JUPYTER = """
JUP_PORT=$(( 15000 + (RANDOM %= 5000) ))
JUP_HOST=$(hostname -i)
echo $PYTHONPATH
jupyter {jupyter} --no-browser --port=$JUP_PORT --ip=$JUP_HOST --notebook-dir {notebook_dir} 2>&1
"""

SUCCESS_MESSAGE = """
All done! If you have linux, execute this command on your laptop:

ssh -fN -L {port}:{ip}:{port} {user_host_name} && sensible-browser http://localhost:{port}/{token}

If you have a windows powershell, instead do (open browser manually if it doesn't prompt):

ssh -N -L {port}:{ip}:{port} {user_host_name}; Start-Process "http://localhost:{port}/{token}"

If you have a mac, instead do:

ssh -fN -L {port}:{ip}:{port} {user_host_name} && open "http://localhost:{port}/{token}"

To connect to any web-based service (including VSCode Server), use the following URL format in your browser:

https://{ip}:{port}

Happy strax analysis, {username}!
"""

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Start a strax jupyter notebook server on the dali batch queue')
    parser.add_argument('--partition',
                        default=default_partition, type=str,
                        help="RCC/DALI partition to use. Try dali, broadwl, xenon1t, lgrandi, caslake or kicp. If you want to use midway3, then use 'lgrandi'.")
    parser.add_argument('--bypass_reservation', '--bypass-reservation', '--skip_reservation', '--skip-reservation', '--no_reservation', '--no-reservation',
                        dest='bypass_reservation',
                        action='store_true',
                        help="Do not use the notebook reservation (useful if it is full)")
    parser.add_argument('--node', help="Specify a node, if desired. By default no specification made")
    parser.add_argument('--exclude_nodes',
                        default=None,
                        help="Specify nodes, which should be excluded, e.g., dali001,dali002 or dali0[28-30]")
    parser.add_argument('--timeout',
                        default=120, type=int,
                        help='Seconds to wait for the jupyter server to start')
    parser.add_argument('--cpu',
                        default=2, type=int,
                        help='Number of CPUs to request.')
    parser.add_argument('--ram',
                        default=8000, type=int,
                        help='MB of RAM to request')
    parser.add_argument('--gpu',
                        action='store_true', default=False,
                        help='Request to run on a GPU partition. Limits runtime to 2 hours.')
    parser.add_argument('--env',
                        default='singularity',
                        choices=['singularity', 'cvmfs', 'backup'],
                        help='Environment to activate; defaults to "singularity" '
                             'to load XENONnT singularity container. '
                             'Passing "cvmfs" will use the conda environment installed in cvmfs, '
                             'using the --tag argument to determine which env exactly ')
    parser.add_argument('--tag',
                        default='development',
                        help='Tagged environment to load'
                             'See wiki page https://xe1t-wiki.lngs.infn.it/doku.php?id=xenon:xenonnt:analysis:environments'   # noqa
                             'Default: "development", or -- equivalently -- "latest"')
    parser.add_argument('--max_hours',
                        default=None, type=float,
                        help='Max number of hours before the job expires. Defaults to 8 h for normal jobs and 2 for GPUs.')  # noqa
    parser.add_argument('--force_new', '--force-new',
                        dest='force_new',
                        action='store_true', default=False,
                        help='Start a new job even if you already have an old one running')
    parser.add_argument('--list',
                        dest='list_jobs',
                        action='store_true', default=False,
                        help='List active straxlab jobs and their Jupyter URLs')
    parser.add_argument('--jupyter',
                        choices=['lab', 'notebook'],
                        default='lab',
                        help='Use jupyter-lab or jupyter-notebook')
    parser.add_argument('--notebook_dir',  '--notebook-dir',
                        dest='notebook_dir',
                        default=os.environ['HOME'],
                        help='The working directory passed to jupyter')
    parser.add_argument('--copy_tutorials', '--copy-tutorials',
                        dest='copy_tutorials',
                        action='store_true',
                        help='Copy tutorials to ~/strax_tutorials (if it does not exist)')
    parser.add_argument('--xenon_config', '--xenon-config',
                        default=None,
                        help='Enter the path of your xenon_config file if you want to replace the public one.')
    parser.add_argument('--rcc_alias',
                        default=None,
                        help='Set the alias for your RCC account to by pass two-factor authentication when opening the jupyter notebooks')

    return parser.parse_args()


def main():
    args = parse_arguments()
    print_flush(SPLASH_SCREEN)

    cached_jobs = refresh_cached_jobs(args.partition)
    if args.list_jobs:
        list_straxlab_jobs(args.partition, args.rcc_alias)
        return

    # Dir for the sbatch and log files
    os.makedirs(OUTPUT_DIR[args.partition], exist_ok=True)

    if args.copy_tutorials:
        dest = os.path.join(OUTPUT_DIR[args.partition], 'strax_tutorials')
        if osp.exists(dest):
            print_flush("NOT copying tutorials, folder already exists")
        else:
            shutil.copytree(
                '/dali/lgrandi/strax/straxen/notebooks/tutorials',
                dest)
    
    # If using default value for notebook_dir, switch to the dali 
    if args.notebook_dir == os.environ['HOME']:
        print('Your HOME directory:', HOME[args.partition])
        args.notebook_dir = HOME[args.partition]

    if args.env == 'singularity':
        s_container = 'xenonnt-%s.simg' % args.tag
        container = s_container
        batch_job = JOB_HEADER + \
                    "{env_starter}/{script} " \
                    "{s_container} {jupyter} {nbook_dir} {partition} {xenon_config}".format(env_starter=ENVSTARTER_PATH,
                                                                 script=SHELL_SCRIPT,
                                                                 s_container=s_container,
                                                                 jupyter=args.jupyter,
                                                                 nbook_dir=args.notebook_dir,
                                                                 partition=args.partition,
                                                                 xenon_config=args.xenon_config
                                                                 )
    elif args.env == 'cvmfs':
        container = 'cvmfs:%s' % args.tag
        if args.partition == 'lgrandi':
            raise Exception("Only singularity is supported on Midway3")
        batch_job = (JOB_HEADER
                     + "source /cvmfs/xenon.opensciencegrid.org/releases/nT/%s/setup.sh" % (args.tag)
                     + START_JUPYTER.format(jupyter=args.jupyter,
                                            notebook_dir=args.notebook_dir)
                     )
        print_flush("Using conda from cvmfs (%s) instead of singularity container." % (args.tag))

    elif args.env == 'backup':
        container = 'backup'
        if args.partition == 'lgrandi':
            raise Exception("Only singularity is supported on Midway3")
        if args.tag != 'development':
            raise ValueError('I\'m going to give you the latest container, you cannot choose a version!')
        batch_job = (JOB_HEADER
                     + "source /dali/lgrandi/strax/miniconda3/bin/activate strax"
                     + START_JUPYTER.format(jupyter=args.jupyter,
                                            notebook_dir=args.notebook_dir)
                     )
        print_flush("Using conda from cvmfs (%s) instead of singularity container." % (args.tag))

    if args.partition == 'kicp':
        qos = 'xenon1t-kicp'
    else:
        qos = args.partition

    url = None
    url_cache_fn = _jupyter_jobs_cache_path(args.partition)
    username = os.environ['USER']

    # Check if a job is already running
    q = subprocess.check_output(['squeue', '-u', username])
    jobs = [line for line in q.decode().splitlines() if 'straxlab' in line]
    job_ids = [int(job.split()[0]) for job in jobs]
    unique_id = '' if len(job_ids) == 0 else '_' + get_unique_id()

    if job_ids:
        print_flush("You still have running straxlab jobs with ids [%s]!" % ",".join([str(id) for id in job_ids]))

    for job_id in job_ids:
        if not args.force_new:
            print_flush("\tTrying to retrieve the URL for job %d from " % job_id + url_cache_fn)
            print_flush("\tIf it doesn't work, login and cancel your job "
                        "so we can start a new one.")
            cached_info = cached_jobs.get(job_id, {})
            cached_url = cached_info.get('url') if isinstance(cached_info, dict) else cached_info
            if cached_url is None:
                print_flush(f"\tNo cached URL found for job {job_id}")
            else:
                url = cached_url
            if url is not None:
                break

    else:
        print_flush("Submitting a new jupyter job")

        _want_to_make_reservation = (args.partition == 'xenon1t'
                                     and (not args.bypass_reservation))
        if args.ram > 16000 and _want_to_make_reservation:
            print_flush('You asked for more than 16 GB total memory you cannot use the notebook '
                        'reservation queue for this job! We will bypass the reservation.')

        if args.cpu >= 8 and _want_to_make_reservation:
            print_flush('You asked for more than 7 CPUs you cannot use the notebook reservation '
                        'queue for this job! We will bypass the reservation.')
        use_reservation = (
                (not args.force_new)
                and _want_to_make_reservation
                and args.cpu < 8
                and args.ram <= 16000
                and (not on_midway3)
        )

        job_fn = os.path.join(OUTPUT_DIR[args.partition], f'notebook{unique_id}.sbatch')
        if not args.force_new:
            log_fn = os.path.join(OUTPUT_DIR[args.partition], 'notebook.log')
        else:
            log_fn = os.path.join(OUTPUT_DIR[args.partition], f'notebook_forced{unique_id}.log')
        if os.path.exists(log_fn):
            os.remove(log_fn)
        with open(job_fn, mode='w', encoding='utf-8') as f:
            extra_header = (GPU_HEADER if args.gpu
                            else CPU_HEADER.format(partition=args.partition,
                                                   qos=qos,
                                                   reservation=('#SBATCH --reservation=xenon_notebook'
                                                                if use_reservation else '')))
            if args.node:
                extra_header += '\n#SBATCH --nodelist={node}'.format(node=args.node)
            if args.exclude_nodes:
                if args.exclude_nodes == 'lc':
                    # Get the list of 'lc' nodes
                    lc_nodes = _get_lc_nodes(args.partition)
                    # Convert the list of 'lc' nodes to a comma-separated string
                    exclude_nodes_str = ','.join(lc_nodes)
                    # Append the --exclude option to the extra_header
                    extra_header += '\n#SBATCH --exclude={exclude_nodes}'.format(exclude_nodes=exclude_nodes_str)
                    print(f"Excluding lc nodes: {exclude_nodes_str}")
                else:
                    extra_header += '\n#SBATCH --exclude={exclude_nodes}'.format(exclude_nodes=args.exclude_nodes)
            if args.max_hours is None:
                max_hours = 2 if args.gpu else 8
            else:
                max_hours = int(args.max_hours)
            f.write(batch_job.format(
                log_fn=log_fn,
                max_hours=max_hours,
                extra_header=extra_header,
                n_cpu=args.cpu,
                mem_per_cpu=int(args.ram / args.cpu)))
        make_executable(job_fn)
        print_flush("\tSubmitting sbatch %s" % job_fn)
        result = subprocess.check_output(['sbatch', job_fn])
        print_flush("\tsbatch returned: %s" % result)
        job_id = int(result.decode().split()[-1])
        print_flush("\tYou have job id %d" % job_id)
        save_job_info(
            args.partition,
            job_id,
            {
                'container': container,
                'environment': args.env,
                'job_id': job_id,
                'job_script': job_fn,
                'log_path': log_fn,
                'partition': args.partition,
                'submitted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'tag': args.tag,
            },
        )

        print_flush("Waiting for your job to start")
        print_flush("\tLooking for logfile %s" % log_fn)
        while not osp.exists(log_fn):
            check_job_state(job_id, log_fn)
            print_flush("\tstill waiting...")
            time.sleep(2)

        print_flush("Job started. Logfile is displayed below; "
                    "we're looking for the jupyter URL.")
        lines_shown = 0
        slept = 0
        url = None
        while url is None and slept < args.timeout:
            try:
                with open(log_fn, mode='r', encoding='utf-8') as f:
                    content = f.readlines()
            except FileNotFoundError:
                check_job_state(job_id, log_fn)
                print_flush("\tLogfile disappeared, retrying...")
                time.sleep(2)
                slept += 2
                continue

            for line_i, line in enumerate(content):
                if line_i >= lines_shown:
                    print_flush('\t' + line.rstrip())
                    lines_shown += 1
                if 'http' in line and not any([excluded in line for excluded in ['sylabs', 'github.com']]):
                    url = line.split()[-1].replace('\x1b[0m', '')
                    break
            else:
                check_job_state(job_id, log_fn)
                time.sleep(2)
                slept += 2
        if url is None:
            raise RuntimeError("Jupyter did not start inside your job!")

        print_flush("\nJupyter started succesfully")

        print_flush("\tSaving URL %s to cache file %s" % (url, url_cache_fn))
        cached_jobs = refresh_cached_jobs(args.partition)
        cached_info = cached_jobs.get(job_id, {})
        if not isinstance(cached_info, dict):
            cached_info = {'url': cached_info}
        else:
            cached_info = dict(cached_info)
        cached_info['url'] = url
        cached_jobs[job_id] = cached_info
        save_cached_jobs(args.partition, cached_jobs)
        save_job_info(args.partition, job_id, {'url': url})

    print_flush("\tParsing URL %s" % url)
    ip, port = url.split('/')[2].split(':')
    if 'token' in url:
        token = url.split('?')[1].split('=')[1]
        token = '?token=' + token
    else:
        token = ''

    # Check if many jobs are running
    q = subprocess.check_output(['squeue', '-u', username])
    jobs = [line for line in q.decode().splitlines() if 'straxlab' in line]
    job_ids = [int(job.split()[0]) for job in jobs]

    if len(job_ids) > 1:
        print_flush("\nPlease consider stopping remaining straxlab jobs:")
        for job in jobs:
            print_flush("\t" + job)

    if args.rcc_alias:
        user_host_name = args.rcc_alias
    else:
        user_host_name = f"{username}@{full_hostname}"    

    print_flush(SUCCESS_MESSAGE.format(ip=ip, port=port, token=token, user_host_name=user_host_name, username=username))


def print_flush(x):
    """Does print(x, flush=True), also in python 2.x"""
    print(x)
    sys.stdout.flush()


def get_unique_id():
    return ''.join(choices(ascii_lowercase, k=6))


def make_executable(path):
    """Make the file at path executable, see """
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2    # copy R bits to X
    os.chmod(path, mode)


if __name__ == '__main__':
    main()
