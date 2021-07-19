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
work around without relying on someone else fixing it, 
which can take time. 

#### Installation
Login to midway/dali. For directions on getting accounts 
setup etc, see [here](https://xe1t-wiki.lngs.infn.it/doku.php?id=xenon:xenon1t:cmp:computing:midway_cluster:instructions). 

```
ssh {username}@dali.rcc.uchicago.edu
```

Decide where you would like to put the env_starter 
repository. It should probably be somewhere in your home 
directory.

```
cd path/to/wherever/you/want/env_start
```

Finally, clone the repository.

```
git clone git@github.com:XENONnT/env_starter.git
```
 

#### Testing your installation
To test that the env_starter script is working, do the 
following (still on Midway):

```
cd env_starter
./start_jupyter.py
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

These comands are what you should run *on your personal 
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
ssh {username}@dali.rcc.uchicago.edu /path/to/your/env_starter/env_starter/start_jupyter.py
```

You should then see the output as above and then be able to access the notebook. 

#### Arguments
There are several arguments you can pass to 
`start_jupyter.py` to customize your job. 

TODO


### Convenient shortcuts

*Symbolic link*. For convenience, it might be useful to 
make a symbolic 
link of 
the `start_jupyer.py` command to your home directory. 
For me this looked like this:
```
[ershockley@dali-login1 ~]$ ln -s /home/ershockley/nt/computing/env_starter/start_jupyter.py ~/start_jupyter.py 
```
but yours would look different depending on where you 
cloned the `env_starter` repository. After doing this, 
you can then shorten the job starter script significantly:
``` 
ssh {user}@dali.rcc.uchicago.edu start_jupyter.py
```
and you can pass the same flags as above. 


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
it will be overwritten next time you run `start_jupyter.py`. 

