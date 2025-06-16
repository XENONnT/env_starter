#!/bin/bash

# Parse arguments
debug_interpreter=false
args=()

# Check if we're in a sourced environment with CVMFS Python
current_python=$(which python 2>/dev/null)
if [[ "$current_python" == *"/cvmfs/"* ]]; then
    echo "ERROR: Don't launch jupyter notebooks within a cvmfs environment - it may mess up the package paths :("
    echo "Your current Python ($current_python) is from a /cvmfs path."
    echo "Please open a new terminal and try again."
    exit 1
fi

# Process command line arguments
for arg in "$@"; do
    if [[ "$arg" == "--debug_interpreter" || "$arg" == "--debug_interpreter=true" || "$arg" == "--debug_interpreter=True" ]]; then
        debug_interpreter=true
    else
        args+=("$arg")
    fi
done

potential_interpreters=()
if [ "$debug_interpreter" = true ]; then
    echo "Looking for Python 3.6+ interpreters..."
fi

# Helper function to check Python version
check_version() {
    local interpreter=$1
    if [ -x "$interpreter" ]; then
        # Check if the interpreter path contains /cvmfs
        if [[ "$interpreter" == *"/cvmfs/"* ]]; then
            if [ "$debug_interpreter" = true ]; then
                echo "Error: $interpreter - CONTAINS /cvmfs PATH - NOT ALLOWED"
            fi
            return 1
        fi
        
        # Try to get the version directly, with a simpler format
        local version_output=$($interpreter -c "import sys; print('{} {}'.format(sys.version_info.major, sys.version_info.minor))" 2>/dev/null)
        if [ $? -eq 0 ]; then
            # Parse major and minor version
            read -r major minor <<< "$version_output"
            
            # Check if it's Python 3.6 or higher
            if [ "$major" -eq 3 ] && [ "$minor" -ge 6 ] || [ "$major" -gt 3 ]; then
                if [ "$debug_interpreter" = true ]; then
                    echo "✓ $interpreter (Python $major.$minor) - COMPATIBLE"
                fi
                return 0
            else
                if [ "$debug_interpreter" = true ]; then
                    echo "✗ $interpreter (Python $major.$minor) - TOO OLD (need 3.6+)"
                fi
            fi
        else
            if [ "$debug_interpreter" = true ]; then
                echo "✗ $interpreter - VERSION CHECK FAILED"
            fi
        fi
    else
        if [ "$debug_interpreter" = true ]; then
            echo "✗ $interpreter - NOT EXECUTABLE OR NOT FOUND"
        fi
    fi
    return 1
}

# Add system Python paths if they're 3.6+
python_path=$(which python 2>/dev/null)
if [ -n "$python_path" ] && check_version "$python_path"; then
    potential_interpreters+=("$python_path")
fi

python3_path=$(which python3 2>/dev/null)
if [ -n "$python3_path" ] && check_version "$python3_path"; then
    potential_interpreters+=("$python3_path")
fi

# Check specific paths that might have newer Python versions
specific_paths=(
    "/usr/bin/python3"
    # "/dali/lgrandi/strax/miniconda3/envs/strax/bin/python"
)

for path in "${specific_paths[@]}"; do
    if [ -f "$path" ] && check_version "$path"; then
        # Check if this path is already in our list (avoid duplicates)
        is_duplicate=false
        for existing in "${potential_interpreters[@]}"; do
            if [ "$existing" = "$path" ]; then
                is_duplicate=true
                break
            fi
        done
        
        if [ "$is_duplicate" = false ]; then
            potential_interpreters+=("$path")
        fi
    fi
done

if [ "$debug_interpreter" = true ]; then
    echo ""
    echo "Available Python 3.6+ interpreters:"
    for interpreter in "${potential_interpreters[@]}"; do
        echo "- $interpreter"
    done
fi

# If we want to prioritize specific versions, we can reorder here
# Just use the first compatible interpreter we found
if [ ${#potential_interpreters[@]} -gt 0 ]; then
    selected_interpreter="${potential_interpreters[0]}"
    echo "Using interpreter: $selected_interpreter"
fi

# If no conda Python was found, use the first one
if [ -z "$selected_interpreter" ] && [ ${#potential_interpreters[@]} -gt 0 ]; then
    selected_interpreter="${potential_interpreters[0]}"
    echo "Using interpreter: $selected_interpreter"
fi

# Exit if no suitable interpreter was found
if [ -z "$selected_interpreter" ]; then
    echo "ERROR: No suitable Python 3.6+ interpreter found. Exiting."
    exit 1
fi

# Final check for /cvmfs in path (in case it somehow slipped through)
if [[ "$selected_interpreter" == *"/cvmfs/"* ]]; then
    echo "ERROR: Don't source any environment in the terminal when you want to start a jupyter notebook."
    echo "The selected interpreter ($selected_interpreter) contains a /cvmfs path."
    exit 1
fi

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Execute the Python script with the remaining arguments
$selected_interpreter "$SCRIPT_DIR/start_jupyter.py" "${args[@]}"
