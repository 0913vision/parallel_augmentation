from library import Loader, Worker, Master, MPI
import multiprocessing
from multiprocessing import Process
import argparse
import time

def main(vcpu: int, osts:int, image_path:str, save_path:str):
    mpi = MPI.MPI()
    num_workers = vcpu-1

    if mpi.rank == 0:
        start = time.perf_counter()
        master = Master.Master(mpi, image_path, osts)
        master.start()

        for i in range(1, mpi.size):
            _ = mpi.int_recv(i)
        end = time.perf_counter()
        print(f"[MAKESPAN] {end-start} sec.")
    
    else:
        processes = []
        job_queues = [multiprocessing.SimpleQueue() for _ in range(num_workers)]
        
        def run_loader(job_queues, mpi, num_workers):
            loader = Loader.Loader(job_queues, mpi, num_workers)
            loader.start()

        loader_process = Process(target=run_loader, args=(job_queues, mpi, num_workers))
        processes.append(loader_process)
        loader_process.start()

        def run_worker(job_queue, rank, ost, save_path):
            worker = Worker.Worker(job_queues[i], rank, ost, save_path)
            worker.start()

        for i in range(num_workers):
            p = Process(target=run_worker, args=(job_queues[i], mpi.rank, osts, save_path))
            processes.append(p)
            p.start()
        
        for p in processes:
            p.join()

        mpi.int_send(0, 0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='simple distributed image augmentation job')
    parser.add_argument('--vcpu', type=int, help='the number of processor in one node except master. (default(min): 2)', default=2)
    parser.add_argument('--osts', type=int, help='the number of osts (default: 24)', default=24)
    parser.add_argument('--image_path', type=str, default='./images')
    parser.add_argument('--save_path', type=str, default='./')
    args = parser.parse_args()
    main(args.vcpu, args.osts, args.image_path, args.save_path)