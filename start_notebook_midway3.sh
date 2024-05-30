#!/bin/bash

IMAGE_NAME=$1
JUPYTER_TYPE=$2
NOTEBOOK_DIR=$3

IMAGE_DIRS=("/project/lgrandi/xenonnt/singularity-images" "/project2/lgrandi/xenonnt/singularity-images")

# If we passed the full path to an image and it exists, use that
if [ -e "${IMAGE_NAME}" ]; then
  CONTAINER="${IMAGE_NAME}"
else
  # Loop over the list of image directoriesß
  for IMAGE_DIR in "${IMAGE_DIRS[@]}"; do
    # Check if the image exists in the current directory
    if [ -e "${IMAGE_DIR}/${IMAGE_NAME}" ]; then
      CONTAINER="${IMAGE_DIR}/${IMAGE_NAME}"
      break
    fi
  done
fi

if [ "x${JUPYTER_TYPE}" = "x" ]; then
  JUPYTER_TYPE='lab'
fi

echo "Using singularity image: ${CONTAINER}"

PORT=$((15000 + (RANDOM %= 5000)))
SINGULARITY_CACHEDIR=/scratch/midway3/$USER/singularity_cache

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
    ssh -N -f -L localhost:$PORT:\$JUP_HOST:$PORT ${USER}@midway3.rcc.uchicago.edu
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

module load singularity
singularity exec --bind /project2 --bind /scratch/midway3/$USER --bind /project/lgrandi $CONTAINER $DIR/$INNER
