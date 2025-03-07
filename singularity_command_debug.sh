#!/bin/bash
singularity exec -e --bind /project2 --bind /cvmfs --bind /project --bind /scratch/midway3/yuem --bind /scratch/midway2/yuem --bind /project2/lgrandi/xenonnt/dali:/dali /project/lgrandi/xenonnt/singularity-images/xenonnt-development.simg /bin/bash -c ' /home/yuem/env_starter/.singularity_inner'
