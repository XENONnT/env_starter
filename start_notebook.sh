#!/bin/bash
# Enter the XENONnT (singularity + conda) environment on dali/midway
IMAGE_NAME=$1

IMAGE_DIR='/project2/lgrandi/xenonnt/singularity-images'

# if we passed the full path to an image, use that
if [ -e ${IMAGE_NAME} ]; then
  CONTAINER=${IMAGE_NAME}
# otherwise check if the name exists in the standard image directory
elif [ -e ${IMAGE_DIR}/${IMAGE_NAME} ]; then
  CONTAINER=${IMAGE_DIR}/${IMAGE_NAME}
# if not any of those, throw an error
else
  echo "We could not find the container at its full path ${IMAGE_NAME} or in ${IMAGE_DIR}. Exiting."
  exit 1
fi

echo "Using singularity image: ${CONTAINER}"

PORT=$(( 15000 + (RANDOM %= 5000) ))
SINGULARITY_CACHEDIR=/scratch/midway2/$USER/singularity_cache

# script to run inside container
DIR=$PWD
INNER=.singularity_inner
cat > $INNER << EOF
#!/bin/bash
JUP_HOST=\$(hostname -i)
## print tunneling instructions
echo -e "
    Copy/Paste this in your local terminal to ssh tunnel with remote
    -----------------------------------------------------------------
    ssh -N -f -L localhost:$PORT:\$JUP_HOST:$PORT ${USER}@midway2.rcc.uchicago.edu
    -----------------------------------------------------------------

    Then open a browser on your local machine to the following address
    ------------------------------------------------------------------
    localhost:$PORT
    ------------------------------------------------------------------
    and use the token that appears below to login.

    OR replace "$ipnip" in the address below with "localhost" and copy
    to your local browser.
    " 2>&1


jupyter lab --no-browser --port=$PORT --ip=\$JUP_HOST --notebook-dir $HOME 2>&1
EOF
chmod +x $INNER

module load singularity
singularity exec --bind /project2 --bind /scratch/midway2/$USER --bind /dali $CONTAINER $DIR/$INNER
