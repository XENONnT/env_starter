#!/bin/bash

echo "Setting environment variables"
export X509_USER_PROXY=/project2/lgrandi/grid_proxy/xenon_service_proxy
echo "Environment variables set"

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
    echo "Starting shell in the XENONnT environment"
    echo "In order to get everything right, we seem to have to source the env another time"
    echo "This can give warnings since the env has sometimes sourced itself already"
    bash --rcfile <(echo '. ~/.bashrc; source /opt/XENONnT/setup.sh')
fi
