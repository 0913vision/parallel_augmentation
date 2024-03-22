#!/bin/sh
#PBS -V
#PBS -N aug
#PBS -q rokaf_knl
#PBS -A etc
#PBS -l select=49:ncpus=64:mpiprocs=4
#PBS -l walltime=06:00:00
#PBS -m abe
#PBS -M 0913vision@gmail.com
#PBS -W sandbox=PRIVATE

cd $PBS_O_WORKDIR

DIR="/home01/sample_data/nurion_stripe/imagenet64"
DATASET="/home01/sample_data/nurion_stripe/extracted_imagenet64"

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0 python/3.9.5

pip3 install urllib3==1.26.15
pip3 install keras tensorflow-cpu scipy pillow

echo "[shell] pip completed."

# delete files
rsync -a --delete /scratch/s5104a22/empty_dir/ $DIR

# ost setup
for i in {0..23}
do
    mkdir $DIR/$i                # Create directory with the name as the current number
    lfs setstripe -i $i $DIR/$i  # Bind the directory to the OST with the same index
done

loader_array=(24 24 48 72 96)
np_array=(52 52 100 148 196)

#exp start
for j in {0..4}
do

# not random (normal)
#./compile.sh 0 0
#echo "normal"

#mpirun -n 52 python3 ./main.py --processors 4 --loaders 24 --workers 1 --osts 24 --dups 1 --image_path $DATASET --save_path $DIR 1>>stdout 2>stderr

#file delete
#rsync -a --delete /scratch/s5104a22/empty_dir/ $DIR

#ost setup
#for i in {0..23}
#do
#    mkdir $DIR/$i                # Create directory with the name as the current number
#    lfs setstripe -i $i $DIR/$i  # Bind the directory to the OST with the same index
#done

# random

./compile.sh 1 0 0 0
echo "random $j"
echo "${np_array[j]} mpi processors, and ${loader_array[j]} loaders."

mpirun -n ${np_array[j]} python3 ./main_random.py --processors 4 --loaders ${loader_array[j]} --workers 1 --osts 24 --dups 1 --image_path $DATASET --save_path $DIR 1>>stdout 2>stderr

# file deelete
rsync -a --delete /scratch/s5104a22/empty_dir/ $DIR

# setup
for i in {0..23}
do
    mkdir $DIR/$i                # Create directory with the name as the current number
    lfs setstripe -i $i $DIR/$i  # Bind the directory to the OST with the same index
done

if [ $j -lt 4 ]; then
sleep 10m
fi

done
