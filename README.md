```
 __   __ ______  _   _   ____   _   _      _______ 
 \ \ / /|  ____|| \ | | / __ \ | \ | |    |__   __|
  \ V / | |__   |  \| || |  | ||  \| | _ __  | |   
   > <  |  __|  | . ` || |  | || . ` || '_ \ | |   
  / . \ | |____ | |\  || |__| || |\  || | | || |   
 /_/ \_\|______||_| \_| \____/ |_| \_||_| |_||_|   

                    The UChicago Analysis Center 
```

### Jupyter Notebook Starter Script

This package contains a standardized way to start up 
jupyter notebooks jobs on the Midway Cluster at UChicago.
This is meant to be a working template; that is, you 
might want/need to modify the script slightly for your 
particular use, but it should work out of the box for 
most things. 

We strongly recommend you understand what the script is 
doing so that if something breaks you can try to find a 
workaround without relying on someone else to fix it, 
which can take time. 

#### Installation
Login to midway/dali. For directions on getting accounts 
setup etc, see [here](https://xe1t-wiki.lngs.infn.it/doku.php?id=xenon:xenon1t:cmp:computing:midway_cluster:instructions). 

```
ssh {username}@dali-login1.rcc.uchicago.edu
```

Decide where you would like to put the env_starter 
repository. It should probably be somewhere in your home 
directory.

```
cd path/to/wherever/you/want/env_start
```

Clone the repository:

```
git clone git@github.com:XENONnT/env_starter.git
```
 

#### Testing your installation
*Note: using **`./start_jupyter.py`** is already **deprecated**. So please follow the updated instructions below:*


We recommend using `start_jupyter.sh` instead of `start_jupyter.py,` as the former checks the available Python interpreters automatically. To test that the env_starter script is working, do the 
following:
- If you are on midway2 or dali login nodes, where you can submit notebooks to either dali or midway2 compute nodes:
```
cd env_starter
./start_jupyter.sh
```
- If you are on midway3 login nodes, where you can submit notebooks to midway3 compute nodes:
```
cd env_starter
./start_jupyter.sh --partition lgrandi
```

You should see a nice splash screen similar to above, 
and then a lot of output, eventually with something like 
this: 

```
Jupyter started succesfully
	Dumping URL {some url} to cache file /home/ershockley/.
	last_jupyter_url
	Parsing URL {some url}

All done! If you have linux, execute this command on your laptop:

{some ssh command && sensible-brower command}

If you have a mac, instead do:

{some ssh command && some open command}

Happy strax analysis, ershockley!
```

These commands are what you should run *on your personal 
laptop, not on Midway itself*. Before running those, 
however, it is useful to understand what is happening 
here. What this script did was submit a job to the 
Midway cluster that started up a jupyter notebook. Let's 
first confirm that we can see a job running. Below, 
everywhere you see `ershockley` you should see your own 
username.

``` 
[ershockley@dali-login1 env_starter]$ squeue -u $USER
             JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)
          12196471   xenon1t straxlab ershockl  R       0:17      1 midway2-0416
```

Above you can see a single job running, called 
`straxlab`. This job is running a jupyter lab/notebook 
session. In order to connect to that jupyter session on 
your own personal laptop/web browser, you need to run 
the `ssh` command listed above. 

``` 
ssh -fN -L {something} && {sensible-broswer/open something}
```

What this does is setup an ssh tunnel between the machine you run those commands on (again, not Midway!) and the worker node on Midway that is actually running the jupyter notebook. Everything after the `&&` is opening a web browser and pointing it to the url where you can see the jupyter notebook.


### Standard Usage
This script submits jobs to the midway cluster and so must be executed on midway itself. However, it is convenient to execute it over ssh *from your personal machine*:

```
ssh {username}@dali.rcc.uchicago.edu /path/to/your/env_starter/env_starter/start_jupyter.sh
```

You should then see the output as above and then be able to access the notebook. 

#### Arguments
There are several arguments you can pass to 
`start_jupyter.sh` to customize your job. 

```
usage: start_jupyter.sh [-h] [--partition PARTITION] [--bypass_reservation] [--node NODE]
                        [--timeout TIMEOUT] [--cpu CPU] [--ram RAM] [--gpu] [--env {singularity,cvmfs}]
                        [--tag TAG] [--force_new] [--jupyter {lab,notebook}] [--notebook_dir NOTEBOOK_DIR]
                        [--copy_tutorials] [--local_cutax] [--debug_interpreter]

Start a strax jupyter notebook server on the dali batch queue

optional arguments:
  -h, --help            show this help message and exit
  --partition PARTITION
                        RCC/DALI partition to use. Try dali, broadwl, or xenon1t.
  --bypass_reservation  Do not use the notebook reservation (useful if it is full)
  --node NODE           Specify a node, if desired. By default no specification made
  --timeout TIMEOUT     Seconds to wait for the jupyter server to start
  --cpu CPU             Number of CPUs to request.
  --ram RAM             MB of RAM to request
  --gpu                 Request to run on a GPU partition. Limits runtime to 2 hours.
  --env {singularity,cvmfs}
                        Environment to activate; defaults to "singularity" to load XENONnT singularity
                        container. Passing "cvmfs" will use the conda environment installed in cvmfs, using
                        the --tag argument to determine which env exactly
  --tag TAG             Tagged environment to loadSee 
  wiki page https://xe1t-wiki.lngs.infn.it/doku.php?id=xenon:xenonnt:dsg:computing:environment_tracking Default: "development", or --
                        equivalently -- "latest"
  --force_new           Start a new job even if you already have an old one running
  --jupyter {lab,notebook}
                        Use jupyter-lab or jupyter-notebook
  --notebook_dir NOTEBOOK_DIR
                        The working directory passed to jupyter
  --copy_tutorials      Copy tutorials to ~/strax_tutorials (if it does not exist)
  --local_cutax         enable the usage of local installation of cutax
  --debug_interpreter   Display detailed information about Python interpreter selection

```


We highlight just a few here. First, the `--env`
argument is used to specify either `singularity` (which 
is the default) or `cvmfs`. The default one will run in 
a singularity container, which is isolated from the host 
system software. This means you will not be able to run, 
for example `sbatch` or other SLURM commands from inside 
the container. The `cvmfs` env, however, does not have 
this problem, but it is more likely to have environment 
conflicts from the host system, which can often affect 
rucio-related commands. 

The `--tag` argument is used to specify which tag of 
base_environmnent to use. This applies to both the 
singularity and cvmfs environments. It defaults to 
`development`, the most up-to-date env. 

A partition equipped with GPU, for example, `gpu2`, doesn't guarantee access to GPU. Without `--gpu`, you will get a CPU-only notebook. So remember to include it if you need to use GPU.

If you are developing `cutax` and want to use your local installation, you can add `--local_cutax`.  

### Convenient shortcuts
A general guidance about using ssh key could be found here: [ssh-key authentication](https://www.digitalocean.com/community/tutorials/how-to-configure-ssh-key-based-authentication-on-a-linux-server)

*SSH profile and key authentication*. It is useful to add 
midway to your ssh 
profile so you can use shorter names when sshing. See 
[here](https://linuxize.com/post/using-the-ssh-config-file/). 
My `~/.ssh/config` looks like the following:
``` 
Host dali
User ershockley
Hostname dali-login1.rcc.uchicago.edu
```

pairing this with ssh-key authentication, it is very easy to login to midway:
``` 
Evans-MacBook-Air:~ shocks$ ssh dali
Last login: Mon Jul 19 10:59:02 2021 from wireless-169-228-79-134.ucsd.edu
===============================================================================
                               Welcome to Midway
                           Research Computing Center
                             University of Chicago
                            http://rcc.uchicago.edu
```

With the ssh config being set, you may be asked for a 2-factor authentication required by UChicago. To bypass the 2-factor authentication, see [Bypass 2-factor authentication](https://xe1t-wiki.lngs.infn.it/doku.php?id=xenon:xenonnt:analysis:analysis_tools_team:midway_tutorial#the_midway_login_nodes)


*Aliases*. You can use aliases to make running this 
script more convenient. Perhaps easiest is just make an 
alias on your personal machine. On Linux you can add 
aliases to `~/.bashrc` and for MacOS it is `~/.
bash_profile`. For your respective machine, add an alias 
like the following (note this assumes you have setup the 
ssh config as above): 

``` 
alias notebook="ssh dali /path/to/your/env_starter/start_jupyter.sh"
``` 

Then on your personal machine you can then start up a 
notebook just with the command `notebook`. You can also 
pass any arguments as you normally would. For example:
``` 
Evans-MacBook-Air:~ shocks$ notebook --container xenonnt-2021.07.1.simg

 __   __ ______  _   _   ____   _   _      _______
 \ \ / /|  ____|| \ | | / __ \ | \ | |    |__   __|
  \ V / | |__   |  \| || |  | ||  \| | _ __  | |
   > <  |  __|  | . ` || |  | || . ` || '_ \ | |
  / . \ | |____ | |\  || |__| || |\  || | | || |
 /_/ \_\|______||_| \_| \____/ |_| \_||_| |_||_|

                    The UChicago Analysis Center
                    
Submitting a new jupyter job
	Submitting sbatch /home/ershockley/straxlab/notebook.sbatch
	sbatch returned: b'Submitted batch job 12229201\n'
	You have job id 12229201
Waiting for your job to start
	Looking for logfile /home/ershockley/straxlab/notebook.log
	still waiting...
Job started. Logfile is displayed below; we're looking for the jupyter URL.
	Starting jupyter job
	Using singularity image: /project2/lgrandi/xenonnt/singularity-images/xenonnt-2021.07.1.simg
```

Another option would be to make an alias on midway. This 
involves one extra step. First, make the alias in your 
`~/.bashrc`, which for me looked like this: 

``` 
alias start_notebook="/home/ershockley/nt/computing/env_starter/start_jupyter.sh"
```
But in order for this to run via ssh you also need to 
add this to *the very top of* your `.bashrc`:
``` 
if [ -z "$PS1" ]; then
  shopt -s expand_aliases
fi
```
as discussed in this [stackexchange thread](https://unix.stackexchange.com/questions/425319/how-do-i-execute-a-remote-alias-over-an-ssh).
After this, you should then be able to run something like: 

``` 
Evans-MacBook-Air:~ shocks$ ssh dali start_notebook --container xenonnt-2021.07.1.simg
```


### Further Customization
This script is used to create an `.sbatch` script that 
then gets submitted to the cluster. If the 
arguments/customization listed above do not include any 
changes you need, you can of course modify the sbatch 
script directly. By default, this script 
gets written to 
``` 
~/straxlab/notebook.sbatch
```
which should serve as a good template to make further 
changes. If you do this, we recommend copying your 
customized sbatch script to a new filename, as otherwise 
it will be overwritten next time you run `start_jupyter.sh`. 

