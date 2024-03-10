#!/bin/sh
#PBS -V
#PBS -N mpi_2
#PBS -q normal
#PBS -A etc
#PBS -l select=2:ncpus=4:mpiprocs=2
#PBS -l walltime=00:30:00

cd $PBS_O_WORKDIR

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0

mpirun -n 2 python3 ./main.py --vcpu 2 --osts 24 --image_path ./images/ --save_path ./output

