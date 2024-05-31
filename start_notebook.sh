#!/bin/bash

IMAGE_NAME=$1
JUPYTER_TYPE=$2
NOTEBOOK_DIR=$3
PARTITION=$4

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
  echo "Error: Singularity image not found. Please provide a valid image name or path."
  exit 1
fi

if [ "x${JUPYTER_TYPE}" = "x" ]; then
  JUPYTER_TYPE='lab'
fi

echo "Using singularity image: ${CONTAINER}"

PORT=$((15000 + (RANDOM %= 5000)))

if [[ "$PARTITION" == "lgrandi" || "$PARTITION" == "build" || "$PARTITION" == "caslake" ]]; then
  SINGULARITY_CACHEDIR=/scratch/midway3/$USER/singularity_cache
  SSH_HOST="midway3.rcc.uchicago.edu"
  BIND_OPTS=("--bind /project2" "--bind /scratch/midway3/$USER" "--bind /project/lgrandi" "--bind /project/lgrandi/xenonnt/dali:/dali")
elif [[ "$PARTITION" == "dali" ]]; then
  SINGULARITY_CACHEDIR=/dali/lgrandi/$USER/singularity_cache
  SSH_HOST="dali-login2.rcc.uchicago.edu"
  BIND_OPTS=("--bind /dali" "--bind /dali/lgrandi/xenonnt/xenon.config:/project2/lgrandi/xenonnt/xenon.config" "--bind /dali/lgrandi/grid_proxy/xenon_service_proxy:/project2/lgrandi/grid_proxy/xenon_service_proxy")
else
  SINGULARITY_CACHEDIR=/scratch/midway2/$USER/singularity_cache
  SSH_HOST="midway2.rcc.uchicago.edu"
  BIND_OPTS=("--bind /project2" "--bind /cvmfs" "--bind /project" "--bind /scratch/midway3/$USER" "--bind /scratch/midway2/$USER" "--bind /project2/lgrandi/xenonnt/dali:/dali")
fi

# script to run inside container
DIR=$PWD
INNER=.singularity_inner
cat >$INNER <<EOF
#!/bin/bash
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

if [[ "$PARTITION" == "dali" ]]; then
  export XENON_CONFIG=/dali/lgrandi/xenonnt/xenon.config
fi

module load singularity

# Initialize an empty string to store the singularity exec command
SINGULARITY_COMMAND="singularity exec"

# Check each bind path and add valid ones to the command string
for bind_opt in "${BIND_OPTS[@]}"; do
  bind_path=$(echo "$bind_opt" | cut -d':' -f1 | sed 's/--bind //')
  if [ -e "$bind_path" ]; then
    SINGULARITY_COMMAND+=" $bind_opt"
  else
    echo "Warning: Bind path '$bind_path' does not exist. Skipping."
  fi
done

# Append the container and script paths to the command string
SINGULARITY_COMMAND+=" $CONTAINER $DIR/$INNER"

# Execute the singularity command using the string
eval "$SINGULARITY_COMMAND"