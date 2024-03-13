#!/bin/sh
#PBS -V
#PBS -N aug
#PBS -q exclusive
#PBS -A etc
#PBS -l select=4:ncpus=16:mpiprocs=4
#PBS -l walltime=00:10:00
#PBS -m abe
#PBS -M 0913vision@gmail.com
#PBS -W sandbox=PRIVATE

cd $PBS_O_WORKDIR

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0 python/3.9.5

pip3 install urllib3==1.26.15
pip3 install keras tensorflow scipy pillow

echo "[shell] pip completed."

mpirun -n 16 python3 ./main.py --processors 4 --loaders 4 --workers 2 --osts 24 --im    age_path /home01/sample_data/nurion_stripe/tiny-imagenet-200/ --save_path /home01/sample_data/nurion_stripe/tiny-imagenet-augmented/ 1>stdout 2>stderr