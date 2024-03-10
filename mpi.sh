#!/bin/sh
#PBS -V
#PBS -N mpi_2
#PBS -q normal
#PBS -A etc
#PBS -l select=2:ncpus=4:mpiprocs=2
#PBS -l walltime=00:30:00

cd $PBS_O_WORKDIR

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0 python/3.9.5

pip3 install keras tensorflow
pip3 uninstall urllib3
pip3 install urllib3==1.26.15
pip3 install scipy pillow

mpirun -n 3 python3 ./main.py --vcpu 4 --osts 24 --image_path ./images/ --save_path ./output

