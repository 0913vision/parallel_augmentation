#!/bin/sh
#PBS -V
#PBS -N aug
#PBS -q rokaf_knl
#PBS -A etc
#PBS -l select=49:ncpus=64:mpiprocs=4
#PBS -l walltime=24:00:00
#PBS -m abe
#PBS -M 0913vision@gmail.com
#PBS -W sandbox=PRIVATE

cd $PBS_O_WORKDIR

PDD="/home01/sample_data/nurion_stripe"
DIR="$PDD/imagenet64"
DATASET="$PDD/extracted_imagenet64"
CATALOG="$PDD/imagenet64_catalog/catalog.txt"

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0 python/3.9.5

pip3 install urllib3==1.26.15
pip3 install keras tensorflow-cpu scipy pillow

# echo "[shell] pip completed." >> stdout

function delete {
    # delete files
    rsync -a --delete /scratch/s5104a22/empty_dir/ $DIR
}

function setup {
    # ost setup
    for i in {0..23}
    do
        mkdir $DIR/$i                # Create directory with the name as the current number
        lfs setstripe -i $i $DIR/$i  # Bind the directory to the OST with the same index
    done
}

loader_array=(24 24 48 48 72 72 96 96)
np_array=(52 52 100 100 148 148 196 196)
exp_type=(1 1 1 1)
length=7

#exp start
for j in {0..$length}
do

echo "===== $j =====" >> stdout

# fc-no catalog
if [ "${exp_type[0]}" -eq 1 ]; then
    ./compile.sh 1 0 0 0
    echo "[FC-MDS]" >> stdout

    mpirun -n ${np_array[j]} python3 ./main_random.py --processors 4 --loaders ${loader_array[j]} --workers 1 --osts 24 --dups 1 --image_path $DATASET --save_path $DIR 1>>stdout 2>stderr

    delete
    setup
    sleep 10m
fi

# oc-no catalog
if [ "${exp_type[1]}" -eq 1 ]; then
    ./compile.sh 0 0 0 0
    echo "[OC-MDS]" >> stdout

    mpirun -n ${np_array[j]} python3 ./main.py --processors 4 --loaders ${loader_array[j]} --workers 1 --osts 24 --dups 1 --image_path $DATASET --save_path $DIR 1>>stdout 2>stderr

    delete
    setup
    sleep 10m
fi

# fc-catalog
if [ "${exp_type[2]}" -eq 1 ]; then
    ./compile.sh 1 1 0 0
    echo "[FC-CAT]" >> stdout

    mpirun -n ${np_array[j]} python3 ./main_random.py --processors 4 --loaders ${loader_array[j]} --workers 1 --osts 24 --dups 1 --image_path $CATALOG --save_path $DIR 1>>stdout 2>stderr

    delete
    setup
    sleep 10m
fi

# oc-catalog
if [ "${exp_type[3]}" -eq 1 ]; then
    ./compile.sh 0 1 0 0
    echo "[OC-CAT]" >> stdout

    mpirun -n ${np_array[j]} python3 ./main.py --processors 4 --loaders ${loader_array[j]} --workers 1 --osts 24 --dups 1 --image_path $CATALOG --save_path $DIR 1>>stdout 2>stderr

    # file delete
    delete
    setup
    if [ $j -lt $length ]; then
    sleep 10m
    fi
fi

done