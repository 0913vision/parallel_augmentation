#!/bin/sh
#PBS -V
#PBS -N mpi_2
#PBS -q normal
#PBS -A etc
#PBS -l select=3:ncpus=4:mpiprocs=9
#PBS -l walltime=00:02:00

cd $PBS_O_WORKDIR

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0 python/3.9.5

pip3 install urllib3==1.26.15
pip3 install keras tensorflow scipy pillow

echo "[shell] pip completed."

mpirun -n 3 python3 ./main.py --vcpu 4 --osts 24 --image_path ./images/ --save_path ./output

