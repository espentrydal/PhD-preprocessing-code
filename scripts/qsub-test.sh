#!/bin/sh

# SGE job configuration
#$ -N test_cuda
#$ -q r.q
#$ -l h_vmem=64G
#$ -l h_rt=24:00:00
#$ -wd /home/espen/forskningsdata/edlb
#$ -o /home/espen/forskningsdata/edlb/logs/sge/$JOB_NAME.o$JOB_ID
#$ -e /home/espen/forskningsdata/edlb/logs/sge/$JOB_NAME.e$JOB_ID

# Environment setup
# FSL Setup
FSLDIR=/home/espen/fsl
PATH=${FSLDIR}/share/fsl/bin:${PATH}
export FSLDIR PATH
. ${FSLDIR}/etc/fslconf/fsl.sh

. /home/espen/miniforge3/etc/profile.d/conda.sh
conda activate clinica || {
  echo "Failed to activate conda environment"
  exit 1
}
. /home/espen/forskningsdata/edlb/clinica/bin/activate || {
  echo "Failed to activate clinica"
  exit 1
}

eddy_cuda10.2
