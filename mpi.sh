#!/bin/sh
#PBS -V
#PBS -N aug
#PBS -q cirnbio
#PBS -A etc
#PBS -l select=31:ncpus=64:mpiprocs=4
#PBS -l walltime=06:00:00
#PBS -m abe
#PBS -M 0913vision@gmail.com
#PBS -W sandbox=PRIVATE

cd $PBS_O_WORKDIR

DIR="/home01/sample_data/nurion_stripe/tiny-imagenet-augmented"

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0 python/3.9.5

pip3 install urllib3==1.26.15
pip3 install keras tensorflow scipy pillow

echo "[shell] pip completed."

rsync -a --delete /scratch/s5104a22/empty_dir/ /home01/sample_data/nurion_stripe/tiny-imagenet-augmented/

for i in {0..23}
do
    mkdir $DIR/$i                # Create directory with the name as the current number
    lfs setstripe -i $i $DIR/$i  # Bind the directory to the OST with the same index
done

for j in {1..1}
do

mpirun -n 124 python3 ./main.py --processors 4 --loaders 24 --workers 4 --osts 24 --dups 4 --image_path /home01/sample_data/nurion_stripe/tiny-imagenet-200/ --save_path /home01/sample_data/nurion_stripe/tiny-imagenet-augmented/ 1>>stdout 2>stderr

rsync -a --delete /scratch/s5104a22/empty_dir/ /home01/sample_data/nurion_stripe/tiny-imagenet-augmented/

for i in {0..23}
do
    mkdir $DIR/$i                # Create directory with the name as the current number
    lfs setstripe -i $i $DIR/$i  # Bind the directory to the OST with the same index
done
done
