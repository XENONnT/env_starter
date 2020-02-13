#!/bin/bash

echo "Activating conda environment"
source /opt/XENONnT/setup.sh

which conda
conda --version
which python
python --version

echo "Setting environment variables"

export X509_USER_PROXY=/project2/lgrandi/grid_proxy/xenon_service_proxy

/project2/lgrandi/xenonnt/development/print_versions

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
    jupyter lab --config /project2/lgrandi/xenonnt/development/jupyter_notebook_config.py --no-browser --port=$JUP_PORT --ip=$JUP_HOST 2>&1
else
    export PS1="[nT \u@\h \W]\$ "
    bash
fi
