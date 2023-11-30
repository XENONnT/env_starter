#!/bin/bash

potential_interpreters=()

# Add the output of 'which python' if it exists and is not empty
python_path=$(which python 2>/dev/null)
if [ -n "$python_path" ] && [[ ! "$python_path" =~ "no python" ]]; then
    potential_interpreters+=("$python_path")
fi

# Add the output of 'which python3' if it exists and is not empty
python3_path=$(which python3 2>/dev/null)
if [ -n "$python3_path" ] && [[ ! "$python3_path" =~ "no python" ]]; then
    potential_interpreters+=("$python3_path")
fi

# Add other paths
potential_interpreters+=(
    "/usr/bin/python3"
    "/dali/lgrandi/strax/miniconda3/envs/strax/bin/python"
    "/cvmfs/xenon.opensciencegrid.org/releases/nT/development/anaconda/envs/XENONnT_development/bin/python"
)

# Use uniq to remove duplicate lines
unique_interpreters=($(echo "${potential_interpreters[@]}" | tr ' ' '\n' | uniq))

# Create a new array to store unique interpreters
declare -a interpreter_array

# Iterate over unique interpreters and add them to the new array
for interpreter in "${unique_interpreters[@]}"; do
    interpreter_array+=("$interpreter")
done

# Print the interpreters
echo "Potential interpreters:"
for interpreter in "${interpreter_array[@]}"; do
    echo "$interpreter"
done

selected_interpreter=None


for interpreter in "${potential_interpreters[@]}"; do
    if command -v "$interpreter" &> /dev/null; then
        selected_interpreter="$interpreter"
        echo "Using the interpreter: $interpreter"
        break
    else
        echo "Interpreter not found: $interpreter"
    fi
done

# If none of the potential interpreters are found, exit
if [ -z "$selected_interpreter" ]; then
    echo "No suitable Python interpreter found. Exiting."
    exit 1
fi

# Run Python code using the selected interpreter with all environment variables
export PYTHONPATH=$PYTHONPATH
source "$(dirname "$(readlink -f "$0")")/first_bash_script_env.sh"
# Extract arguments passed to the shell script
args="$@"

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

$selected_interpreter "$SCRIPT_DIR/start_jupyter.py" $args
