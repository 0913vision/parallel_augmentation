from keras.preprocessing.image import load_img, img_to_array
from . import MPI
import threading
import queue
import os
import struct

class Communicator(threading.Thread):
    def __init__(self, mpi:MPI.MPI, network_queue:queue.Queue):
        super().__init__()
        self.mpi = mpi
        self.network_queue = network_queue

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
    def __init__(self, mpi:MPI.MPI, first_worker_rank:int, network_queue:queue.Queue, num_workers:int):
        super().__init__()
        self.mpi = mpi
        self.first_worker_rank = first_worker_rank
        self.network_queue = network_queue
        self.num_workers = num_workers

    def run(self):
        dest = 0
        supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        while True:
            file_list = self.network_queue.get()
            if file_list is None:
                for i in range(self.first_worker_rank, self.num_workers+self.first_worker_rank):
                    self.mpi.int_send(i, -1)
                break
            else:
                for file in file_list:
                    if not file: # empty string handling
                        continue
                    _, ext = os.path.splitext(file)
                    if ext.lower() not in supported_extensions:
                        continue

                    # Distribute files (with load balancing)
                    file = file.decode('utf-8')
                    name = os.path.basename(file)
                    img = img_to_array(load_img(file))
                    # img = img.reshape((1,) + img.shape)
                    img_shape = img.shape
                    img_bytes = img.tobytes()

                    shape_header = struct.pack('iii', *img_shape)
                    header = struct.pack('i', len(name))  # 4 bytes for name length
                    message = shape_header + header + name.encode('utf-8') + img_bytes
                    total_size = struct.calcsize('iii') + struct.calcsize('i') + len(name) + len(img_bytes)
                    
                    self.mpi.int_send(dest+self.first_worker_rank, total_size)
                    self.mpi.char_send(dest+self.first_worker_rank, message)
                    # self.job_queues[dest].put((name, img))

                    if self.num_workers > 1:
                        dest = (dest+1) % self.num_workers

class Loader():
    def __init__(self, mpi:MPI.MPI, first_worker_rank:int, num_workers:int):
        self.network_queue = queue.Queue()
        self.num_workers = num_workers
        self.communicator = Communicator(mpi, self.network_queue)
        self.fetcher = Fetcher(mpi, first_worker_rank, self.network_queue, self.num_workers)

    def start(self):
        self.communicator.start()
        self.fetcher.start()

    def join(self):
        self.communicator.join()
        self.fetcher.join()
