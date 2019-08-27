#!/bin/bash
DEV_PYDIR=/project2/lgrandi/xenonnt/development

echo "Clearing environment variables"
unset PYTHONPATH
for VAR in X509_CERT_DIR X509_VOMS_DIR; do
    VALUE=${!VAR}
    if [ "X$VALUE" != "X" ]; then
        echo "WARNING: $VAR is set set and could lead to problems when using this environment"
    fi
done

echo "Activating conda environment"
source /opt/XENONnT/anaconda/bin/activate XENONnT_development
which conda
conda --version
which python
python --version

echo "Setting environment variables"

# prepend to LD_LIBRARY_PATH - non-Python tools might be using it
# Why is this necessary? shouldn't conda do it?
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib64${LD_LIBRARY_PATH:+:}${LD_LIBRARY_PATH}

# Development python packages
export PYTHONPATH=$DEV_PYDIR/lib/python3.6/site-packages:$PYTHONPATH
export PATH=$DEV_PYDIR/bin:$PATH

# gfal2
export GFAL_CONFIG_DIR=$CONDA_PREFIX/etc/gfal2.d
export GFAL_PLUGIN_DIR=$CONDA_PREFIX/lib64/gfal2-plugins/

# rucio
#export RUCIO_HOME=$CONDA_PREFIX  #developer Rucio catalogue
export RUCIO_HOME=/cvmfs/xenon.opensciencegrid.org/software/rucio-py27/1.8.3/rucio #production catalogue
export RUCIO_ACCOUNT=xenon-analysis
export X509_USER_PROXY=/project2/lgrandi/grid_proxy/xenon_service_proxy
if [ "x$X509_CERT_DIR" = "x" ]; then
    export X509_CERT_DIR=/etc/grid-security/certificates
fi

# stuff
#alias py_dev_install='python setup.py develop --prefix=$DEV_PYDIR'
alias llt='ls -ltrh'
alias la='ls -a'
alias ll='ls -la'

echo "Testing strax/straxen import"
python -c 'import strax; import straxen; [print(f"{x.__name__} {x.__version__}") for x in [strax, straxen]]'

# Start the shell or jupyter server
if [[ $1 = "-j" ]]; then
    shift
    if [[ -z "$1" ]]; then
        JUP_PORT=$(( 15000 + (RANDOM %= 5000) ))
        JUP_HOST=$(hostname -i)
    else
        JUP_PORT=$1
        JUP_HOST=localhost
    fi    
    echo "Starting jupyter server on host $JUP_HOST, port $JUP_PORT"
    jupyter notebook --config /project2/lgrandi/xenonnt/development/jupyter_notebook_config.py --no-browser --port=$JUP_PORT --ip=$JUP_HOST 2>&1
else
    export PS1="[nT \u@\h \W]\$ "
    bash
fi
