from keras.preprocessing.image import load_img, img_to_array
from . import MPI
import threading
import queue
import os
import multiprocessing as mp

class Communicator(threading.Thread):
    def __init__(self, network_queue:queue.Queue, mpi:MPI.MPI):
        super().__init__()
        self.network_queue = network_queue
        self.mpi = mpi

    def run(self):
        # Receive the file list
        while True:
            size = self.mpi.int_recv(0)
            if size == -1:
                self.network_queue.put(None)
                break
            else:
                tasks = self.mpi.char_recv(0, size).split(b'\0')
                self.network_queue.put(tasks)

class Fetcher(threading.Thread):
    def __init__(self, network_queue:queue.Queue, job_queues:mp.SimpleQueue, num_workers:int):
        super().__init__()
        self.job_queues = job_queues
        self.network_queue = network_queue
        self.num_workers = num_workers

    def run(self):
        dest = 0
        while True:
            file_list = self.network_queue.get()
            if file_list is None:
                for jq in self.job_queues:
                    jq.put((None,None))
                break
            else:
                for file in file_list:
                    if not file: # empty string handling
                        continue
                    # Distribute files to the job queues (with load balancing)
                    file = file.decode('utf-8')
                    name = os.path.basename(file)
                    img = img_to_array(load_img(file))
                    img = img.reshape((1,) + img.shape)
                    self.job_queues[dest].put((name, img))
                    if self.num_workers > 1:
                        dest = (dest+1) % self.num_workers

class Loader():
    def __init__(self, job_queues:mp.SimpleQueue, mpi:MPI.MPI, num_workers:int):
        self.job_queues = job_queues
        self.network_queue = queue.Queue()
        self.mpi = mpi
        self.num_workers = num_workers
        self.communicator = Communicator(self.network_queue, self.mpi)
        self.fetcher = Fetcher(self.network_queue, self.job_queues, self.num_workers)

    def start(self):
        self.communicator.start()
        self.fetcher.start()

    def join(self):
        self.communicator.join()
        self.fetcher.join()
