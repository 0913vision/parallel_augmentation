#!/bin/sh
#PBS -V
#PBS -N aug
#PBS -q normal
#PBS -A etc
#PBS -l select=385:ncpus=64:mpiprocs=4
#PBS -l walltime=48:00:00
#PBS -m abe
#PBS -M 0913vision@gmail.com
#PBS -W sandbox=PRIVATE

cd $PBS_O_WORKDIR

PDD="/home01/sample_data/nurion_stripe"
DIR="$PDD/yc_target"
DATASET="$PDD/yc_source"
CATALOG="$PDD/all_file_paths_yc_source.txt"
PREPARE="/scratch/s5104a22/imagenet_tiny_prepare"

module purge
module load craype-x86-skylake gcc/8.3.0 openmpi/3.1.0 python/3.9.5

pip3 install urllib3==1.26.15
pip3 install keras tensorflow-cpu scipy pillow

# echo "[shell] pip completed." >> stdout

function delete {
    # delete files
    # rsync -a --delete /scratch/s5104a22/empty_dir/ $DIR
    # mpirun -np 1540 $PREPARE/delete_dataset $PDD/all_file_paths_yc_source.txt
    # mpirun -np 1540 $PREPARE/delete_dataset $PDD/all_file_paths_yc_target.txt
    rm -rf $DIR
    rm -rf $DATASET
    # rmdir $DIR
    # rmdir $DATASET
}

function setup {
    mkdir -p $DIR
    mpirun -np 1540 $PREPARE/make_dataset $PDD yc_source $PREPARE/train_merge 0
    # ost setup
    for i in {0..23}
    do
        mkdir $DIR/$i                # Create directory with the name as the current number
        lfs setstripe -i $i $DIR/$i  # Bind the directory to the OST with the same index
    done
}

# loader_array=(1 2 4 8 24 48 96 192 384 768)
# np_array=(6 8 12 20 52 100 196 388 772 1540)
loader_array=(768 384 192 96 48 24 8 4 2 1)
np_array=(1540 772 388 196 100 52 20 12 8 6)
exp_type=(1 1 0 1)
length=10

delete
setup

#exp start
for j in $(seq 0 $length)
do

echo "===== $j =====" >> stdout

# fc-no catalog
if [ "${exp_type[0]}" -eq 1 ]; then
    ./compile.sh 1 0 0 0
    echo "[FC-MDS]" >> stdout

    mpirun -n ${np_array[j]} python3 ./main_random.py --processors 4 --loaders ${loader_array[j]} --workers 1 --osts 24 --dups 1 --image_path $DATASET --save_path $DIR 1>>stdout 2>stderr

    delete
    setup
    sleep 5m
fi

# oc-no catalog
if [ "${exp_type[1]}" -eq 1 ]; then
    ./compile.sh 0 0 0 0
    echo "[OC-MDS]" >> stdout

    mpirun -n ${np_array[j]} python3 ./main.py --processors 4 --loaders ${loader_array[j]} --workers 1 --osts 24 --dups 1 --image_path $DATASET --save_path $DIR 1>>stdout 2>stderr

    delete
    setup
    sleep 5m
fi

# fc-catalog
if [ "${exp_type[2]}" -eq 1 ]; then
    ./compile.sh 1 1 0 0
    echo "[FC-CAT]" >> stdout

    mpirun -n ${np_array[j]} python3 ./main_random.py --processors 4 --loaders ${loader_array[j]} --workers 1 --osts 24 --dups 1 --image_path $CATALOG --save_path $DIR 1>>stdout 2>stderr

    delete
    setup
    sleep 5m
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
        sleep 5m
    fi
fi
done
