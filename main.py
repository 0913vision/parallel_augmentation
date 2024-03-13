from library import Loader, Worker, Master, MPI
import argparse
import time

def main(processors:int, loaders:int, workers: int, osts:int, dups:int, image_path:str, save_path:str):
    mpi = MPI.MPI()

    if mpi.size != processors+loaders*(workers+1):
        raise Exception("MPI PARAMETER ERROR - WORLD SIZE")

    if mpi.rank == 0:
        master = Master.Master(mpi, image_path, osts, loaders, processors)
        mpi.barrier()

        start = time.perf_counter()
        master.start()

        mpi.barrier()
        end = time.perf_counter()
        print(f"[MAKESPAN] {end-start} sec.")

    elif mpi.rank < processors:
        mpi.barrier()
        mpi.barrier()
    
    elif mpi.rank < processors+loaders:
        # loader part
        first_worker_rank = processors+loaders+(mpi.rank-processors)*workers
        loader = Loader.Loader(mpi=mpi, first_worker_rank=first_worker_rank, num_workers=workers)
        mpi.barrier()
        loader.start()
        loader.join()
        mpi.barrier()

    else: # worker part
        loader_rank = int((mpi.rank-(processors+loaders))/workers + processors)
        worker = Worker.Worker(mpi=mpi, loader_rank=loader_rank, ost=loader_rank-processors, save_path=save_path, dups=dups)
        mpi.barrier()
        worker.start()
        worker.join()
        mpi.barrier()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='simple distributed image augmentation job')
    parser.add_argument('--processors', type=int, help='the number of processors of a node. (default(min): 1)', default=1)
    parser.add_argument('--loaders', type=int, help='the number of loaders. (default(min): 1)', default=1)
    parser.add_argument('--workers', type=int, help='the number of workers of a loader. (default(min): 1)', default=1)
    parser.add_argument('--osts', type=int, help='the number of osts (default: 24)', default=24)
    parser.add_argument('--dups', type=int, help='the number of augmented data (default(min): 1)', default=1)
    parser.add_argument('--image_path', help='where your images are located', type=str, default='./images')
    parser.add_argument('--save_path', type=str, help='where you want the augmented images to be saved', default='./')
    args = parser.parse_args()
    main(args.processors, args.loaders, args.workers, args.osts, args.dups, args.image_path, args.save_path)
