#!/bin/sh
#PBS -V
#PBS -N aug
#PBS -q exclusive
#PBS -A etc
#PBS -l select=2:ncpus=8:mpiprocs=4
#PBS -l walltime=00:02:00
#PBS -m ae
#PBS -M 0913vision@gmail.com

cd $PBS_O_WORKDIR

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0 python/3.9.5

pip3 install urllib3==1.26.15
pip3 install keras tensorflow scipy pillow

echo "[shell] pip completed."

mpirun -n 9 python3 ./main.py --processors 4 --loaders 4 --workers 2 --osts 24 --image_path ./images/ --save_path ./output

