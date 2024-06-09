from keras.preprocessing.image import load_img, img_to_array
from . import MPI
import threading
import queue
import os
import struct
import time
import ctypes

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
    def __init__(self, mpi:MPI.MPI, first_worker_rank:int, network_queue:queue.Queue, num_workers:int, processors:int, loaders:int, get_ost:bool):
        super().__init__()
        self.mpi = mpi
        self.first_worker_rank = first_worker_rank
        self.network_queue = network_queue
        self.num_workers = num_workers
        self.read_time = 0.0  # 총 파일 읽기 시간을 저장하는 변수
        self.processors = processors
        self.loaders = loaders
        if get_ost:
            self.getost = ctypes.CDLL('./library/getost.so')
            self.getost.get_file_ost.argtypes = [ctypes.c_char_p]
            self.getost.get_file_ost.restype = ctypes.c_int
            self.get_ost_time = 0.0

    def get_file_ost(self, file):
        print("get_file_ost")
        if isinstance(file, str):
            file = file.encode('utf-8')
        return self.getost.get_file_ost(file)

    def run(self):
        dest = 0
        supported_extensions = {b'.jpg', b'.jpeg', b'.png', b'.bmp', b'.gif'}
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

                    if self.getost:
                        if self.mpi.rank == self.processors:
                            print(file)
                        start_time = time.time()
                        a = self.get_file_ost(file)
                        if self.mpi.rank == self.processors:
                            print(a)
                        get_ost_time = time.time() - start_time
                        self.get_ost_time += get_ost_time

                    start_time = time.time()
                    # Distribute files (with load balancing)
                    file = file.decode('utf-8')
                    name = os.path.basename(file)
                    img = img_to_array(load_img(file))

                    read_time = time.time() - start_time
                    self.read_time += read_time

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

        start_time = time.time()
        if self.mpi.rank == self.processors:
            all_read_times = [self.read_time]
            for i in range(self.processors + 1, self.processors + self.loaders):
                read_time = self.mpi.char_recv(i, struct.calcsize('d'))
                all_read_times.append(struct.unpack('d', read_time)[0])
            
            if all_read_times:
                total_read_time = sum(all_read_times)
                average_time = total_read_time / len(all_read_times)
                max_time = max(all_read_times)
                min_time = min(all_read_times)
                print(f"Average read time: {average_time:.6f} seconds")
                print(f"Max read time: {max_time:.6f} seconds")
                print(f"Min read time: {min_time:.6f} seconds")
            
            end_time = time.time()
            print(f"Read time calculation time: {end_time - start_time:.6f} seconds")
        else:
            self.mpi.char_send(self.processors, struct.pack('d', self.read_time))

        if self.getost:
            if self.mpi.rank == self.processors:
                all_get_ost_times = [self.get_ost_time]
                for i in range(self.processors + 1, self.processors + self.loaders):
                    get_ost_time = self.mpi.char_recv(i, struct.calcsize('d'))
                    all_get_ost_times.append(struct.unpack('d', get_ost_time)[0])
                
                if all_get_ost_times:
                    total_get_ost_time = sum(all_get_ost_times)
                    average_time = total_get_ost_time / len(all_get_ost_times)
                    max_time = max(all_get_ost_times)
                    min_time = min(all_get_ost_times)
                    print(f"Average get_ost time: {average_time:.6f} seconds")
                    print(f"Max get_ost time: {max_time:.6f} seconds")
                    print(f"Min get_ost time: {min_time:.6f} seconds")
                
                end_time = time.time()
                print(f"Get_ost time calculation time: {end_time - start_time:.6f} seconds")
            else:
                self.mpi.char_send(self.processors, struct.pack('d', self.get_ost_time))

class Loader():
    def __init__(self, mpi:MPI.MPI, first_worker_rank:int, num_workers:int, processors:int, loaders:int, get_ost:bool):
        self.network_queue = queue.Queue()
        self.num_workers = num_workers
        self.communicator = Communicator(mpi, self.network_queue)
        self.fetcher = Fetcher(mpi, first_worker_rank, self.network_queue, self.num_workers, processors, loaders, get_ost)

    def start(self):
        self.communicator.start()
        self.fetcher.start()

    def join(self):
        self.communicator.join()
        self.fetcher.join()
