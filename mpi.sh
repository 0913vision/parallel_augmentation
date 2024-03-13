#!/bin/sh
#PBS -V
#PBS -N aug
#PBS -q exclusive
#PBS -A etc
#PBS -l select=9:ncpus=64:mpiprocs=12
#PBS -l walltime=12:00:00
#PBS -m abe
#PBS -M 0913vision@gmail.com
#PBS -W sandbox=PRIVATE

cd $PBS_O_WORKDIR

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0 python/3.9.5

pip3 install urllib3==1.26.15
pip3 install keras tensorflow scipy pillow

echo "[shell] pip completed."

mpirun -n 108 python3 ./main.py --processors 12 --loaders 24 --workers 3 --osts 24 --dups 10 --image_path /home01/sample_data/nurion_stripe/tiny-imagenet-200/ --save_path /home01/sample_data/nurion_stripe/tiny-imagenet-augmented/ 1>stdout 2>stderr