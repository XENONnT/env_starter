#!/bin/bash

IMAGE_NAME=$1
JUPYTER_TYPE=$2
NOTEBOOK_DIR=$3
PARTITION=$4
XENON_CONFIG=$5

IMAGE_DIRS=("/project/lgrandi/xenonnt/singularity-images" "/project2/lgrandi/xenonnt/singularity-images" "/dali/lgrandi/xenonnt/singularity-images")

CONTAINER=""
# If we passed the full path to an image and it exists, use that
if [ -e "${IMAGE_NAME}" ]; then
  CONTAINER="${IMAGE_NAME}"
else
  # Loop over the list of image directories
  for IMAGE_DIR in "${IMAGE_DIRS[@]}"; do
    # Check if the image exists in the current directory
    if [ -e "${IMAGE_DIR}/${IMAGE_NAME}" ]; then
      CONTAINER="${IMAGE_DIR}/${IMAGE_NAME}"
      break
    fi
  done
fi
# if no container found, throw an error
if [ -z "${CONTAINER}" ]; then
  echo "Error: Container image not found. Please provide a valid image name or path."
  exit 1
fi

if [ "x${JUPYTER_TYPE}" = "x" ]; then
  JUPYTER_TYPE='lab'
fi

# Determine whether to use singularity or apptainer based on hostname
if [[ $(hostname) == *"midway3"* ]]; then
  CONTAINER_CMD="apptainer"
  echo "Using apptainer image: ${CONTAINER}"
else
  CONTAINER_CMD="singularity"
  echo "Using singularity image: ${CONTAINER}"
fi

PORT=$((15000 + (RANDOM %= 5000)))

if [[ "$PARTITION" == "lgrandi" || "$PARTITION" == "build" || "$PARTITION" == "caslake" ]]; then
  CONTAINER_CACHEDIR=/scratch/midway3/$USER/singularity_cache
  SSH_HOST="midway3.rcc.uchicago.edu"
  BIND_OPTS=("--bind /project" "--bind /project2" "--bind /cvmfs" "--bind /scratch/midway3/$USER" "--bind /scratch/midway2/$USER" "--bind /home/$USER")
elif [[ "$PARTITION" == "dali" ]]; then
  CONTAINER_CACHEDIR=/dali/lgrandi/$USER/singularity_cache
  SSH_HOST="dali-login2.rcc.uchicago.edu"
  BIND_OPTS=("--bind /dali" "--bind /dali/lgrandi/xenonnt/xenon.config:/project2/lgrandi/xenonnt/xenon.config" "--bind /dali/lgrandi/grid_proxy/xenon_service_proxy:/project2/lgrandi/grid_proxy/xenon_service_proxy")
else
  CONTAINER_CACHEDIR=/scratch/midway2/$USER/singularity_cache
  SSH_HOST="midway2.rcc.uchicago.edu"
  BIND_OPTS=("--bind /project" "--bind /project2" "--bind /cvmfs" "--bind /scratch/midway3/$USER" "--bind /scratch/midway2/$USER" "--bind /project2/lgrandi/xenonnt/dali:/dali")
fi

# script to run inside container
DIR=$PWD
INNER=.singularity_inner
cat >$INNER <<EOF
#!/bin/bash
if [[ -n "\$SINGULARITYENV_XENON_CONFIG" && -f "\$SINGULARITYENV_XENON_CONFIG" ]]; then
    export XENON_CONFIG="\$SINGULARITYENV_XENON_CONFIG"
    echo "Forcibly set XENON_CONFIG inside container to: \$XENON_CONFIG"
fi

JUP_HOST=\$(hostname -i)
## print tunneling instructions
echo -e "
    Copy/Paste this in your local terminal to ssh tunnel with remote
    -----------------------------------------------------------------
    ssh -N -f -L localhost:$PORT:\$JUP_HOST:$PORT ${USER}@${SSH_HOST}
    -----------------------------------------------------------------

    Then open a browser on your local machine to the following address
    ------------------------------------------------------------------
    localhost:$PORT
    ------------------------------------------------------------------
    and use the token that appears below to login.

    OR replace "$ipnip" in the address below with "localhost" and copy
    to your local browser.
    " 2>&1

jupyter ${JUPYTER_TYPE} --no-browser --port=$PORT --ip=\$JUP_HOST --notebook-dir ${NOTEBOOK_DIR} 2>&1
EOF
chmod +x $INNER

# Set default XENON_CONFIG path based on PARTITION
case "$PARTITION" in
"dali")
  DEFAULT_CONFIG="/dali/lgrandi/xenonnt/xenon.config"
  ;;
"lgrandi" | "caslake" | "build")
  DEFAULT_CONFIG="/project/lgrandi/xenonnt/xenon.config"
  ;;
"xenon1t" | "broadwl" | "kicp" | "bigmem2" | "gpu2")
  DEFAULT_CONFIG="/project2/lgrandi/xenonnt/xenon.config"
  ;;
*)
  DEFAULT_CONFIG=""
  ;;
esac

# Check if user-provided XENON_CONFIG exists
if [[ -n "$XENON_CONFIG" && "$XENON_CONFIG" != "None" ]]; then
  if [[ -f "$XENON_CONFIG" ]]; then
    echo "Using provided xenon_config: $XENON_CONFIG"
  else
    echo "Warning: Provided xenon_config file not found at $XENON_CONFIG"
    XENON_CONFIG=""
  fi
else
  echo "No xenon_config provided by user."
  XENON_CONFIG=""
fi

XENON_CONFIG_OVERRIDE=""
if [[ -n "$XENON_CONFIG" && -f "$XENON_CONFIG" ]]; then
    XENON_CONFIG=$(realpath "$XENON_CONFIG")
    XENON_CONFIG_OVERRIDE="export XENON_CONFIG='$XENON_CONFIG' &&"
    echo "Will override XENON_CONFIG in container with: $XENON_CONFIG"
fi

# If user-provided XENON_CONFIG is not valid, try to use DEFAULT_CONFIG
if [[ -z "$XENON_CONFIG" ]]; then
  if [[ -n "$DEFAULT_CONFIG" ]]; then
    if [[ -f "$DEFAULT_CONFIG" ]]; then
      echo "Using default xenon_config: $DEFAULT_CONFIG"
    else
      echo "Error: Default xenon_config file not found at $DEFAULT_CONFIG"
    fi
  else
    echo "Error: No default xenon_config path available for the partition: $PARTITION"
  fi
fi

# Load the appropriate container module based on the system
if [[ "$CONTAINER_CMD" == "apptainer" ]]; then
  module load apptainer
else
  module load singularity
fi

# Configure container environment variables
if [[ -n "$XENON_CONFIG" && -f "$XENON_CONFIG" ]]; then
    if [[ "$CONTAINER_CMD" == "apptainer" ]]; then
        export APPTAINERENV_XENON_CONFIG="$XENON_CONFIG"
    else
        export SINGULARITYENV_XENON_CONFIG="$XENON_CONFIG"
    fi
    XENON_CONFIG_BIND="--bind $XENON_CONFIG:$XENON_CONFIG"
else
    XENON_CONFIG_BIND=""
fi

CONTAINER_COMMAND="$CONTAINER_CMD exec"

# Add the XENON_CONFIG bind option if it exists
if [[ -n "$XENON_CONFIG_BIND" ]]; then
    CONTAINER_COMMAND+=" $XENON_CONFIG_BIND"
fi

# Check each bind path and add valid ones to the command string
for bind_opt in "${BIND_OPTS[@]}"; do
  bind_path=$(echo "$bind_opt" | cut -d':' -f1 | sed 's/--bind //')
  if [ -e "$bind_path" ]; then
    CONTAINER_COMMAND+=" $bind_opt"
  else
    echo "Warning: Bind path '$bind_path' does not exist. Skipping."
  fi
done

# Append the container and script paths to the command string
CONTAINER_COMMAND+=" $CONTAINER /bin/bash -c '$XENON_CONFIG_OVERRIDE$DIR/$INNER'"
echo "Comand: $CONTAINER_COMMAND"

# Execute the container command
eval "$CONTAINER_COMMAND"
