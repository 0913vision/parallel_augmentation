import threading
import queue
import time
from PIL import Image
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import os
from . import MPI
import struct
import random

class Augmenter(threading.Thread):
    def __init__(self, mpi:MPI.MPI, loader_rank:int, complete_queue:queue.Queue, dups:int): #mpi, loader_rank, self.complete_queue
        super().__init__()
        self.mpi = mpi
        self.loader_rank = loader_rank
        self.complete_queue = complete_queue
        self.dups = dups

    def run(self):
        while True:
            # Fetch a job from the job queue
            # name, img = self.job_queue.get()
            size_or_terminate = self.mpi.int_recv(self.loader_rank)
            if size_or_terminate == -1:
                self.complete_queue.put((None, None))
                break
            
            received_data = self.mpi.char_recv(self.loader_rank, size_or_terminate)

            shape_header = received_data[:12]
            img_shape = struct.unpack('iii', shape_header)
            header = received_data[12:16]
            name_length = struct.unpack('i', header)[0]
            name = received_data[16:16+name_length].decode('utf-8')
            img_bytes = received_data[16+name_length:]
            img = np.frombuffer(img_bytes, dtype=np.float32).reshape((1,) + img_shape)

            datagen = ImageDataGenerator(
                rotation_range=40,
                width_shift_range=0.2,
                height_shift_range=0.2,
                rescale=1./255,
                shear_range=0.2,
                zoom_range=0.2,
                horizontal_flip=True,
                fill_mode='nearest')

            # Perform image augmentation
            augmented_images = []
            for i in range(self.dups):
                for batch in datagen.flow(img, batch_size=1):
                    augmented_images.append(batch[0])
                    break  # Generate only one batch per image

            self.complete_queue.put((name, augmented_images))

            # Signal task completion
            # self.job_queue.task_done()

class Flusher(threading.Thread):
    def __init__(self, mpi:MPI.MPI, complete_queue:queue.Queue, ost:int, save_path:str, processors:int, loaders:int):
        super().__init__()
        self.mpi = mpi
        self.complete_queue = complete_queue
        self.ost = ost
        self.save_path = save_path
        self.processors = processors
        self.loaders = loaders
        self.write_time = 0.0

        self.dir_path = os.path.join(save_path, str(ost))

        try:
            os.makedirs(self.dir_path)
        except FileExistsError:
            pass

    def run(self):
        while True:
            # Fetch an augmented image from the complete queue
            name, augmented_images = self.complete_queue.get()
            if augmented_images is None:  # A way to signal termination
                break

            # Save the augmented image to disk
            for i, img_array in enumerate(augmented_images):
                img = Image.fromarray((img_array * 255).astype(np.uint8))
                file_name = f"{name}_augmented_image_{i}.png"
                random_ost = str(random.randrange(0,24))
                full_path = os.path.join(*[self.save_path, random_ost, file_name])
                #full_path = os.path.join(self.dir_path, file_name)
                start_time = time.perf_counter()
                img.save(full_path)
                write_time = time.perf_counter() - start_time
                self.write_time += write_time

        start_time = time.perf_counter()
        if self.mpi.rank == self.processors+self.loaders:
            all_write_times = [self.write_time]
            for i in range(self.processors + self.loaders + 1, self.mpi.size):
                write_time = self.mpi.char_recv(i, struct.calcsize('d'))
                all_write_times.append(struct.unpack('d', write_time)[0])
            
            if all_write_times:
                total_write_time = sum(all_write_times)
                average_time = total_write_time / len(all_write_times)
                max_time = max(all_write_times)
                min_time = min(all_write_times)
                print(f"Average write time: {average_time:.6f} seconds")
                print(f"Max write time: {max_time:.6f} seconds")
                print(f"Min write time: {min_time:.6f} seconds")
            
            end_time = time.perf_counter()
            print(f"Write time calculation time: {end_time - start_time:.6f} seconds")
        else:
            self.mpi.char_send(self.processors+self.loaders, struct.pack('d', self.write_time))

class Worker_random():
    def __init__(self, mpi:MPI.MPI, loader_rank:int, ost:int, save_path:str, dups:int, processors:int, loaders:int):
        self.complete_queue = queue.Queue()
        self.augmenter = Augmenter(mpi, loader_rank, self.complete_queue, dups)
        self.flusher = Flusher(mpi, self.complete_queue, ost, save_path, processors, loaders)

    def start(self):
        self.augmenter.start()
        self.flusher.start()

    def join(self):
        self.augmenter.join()
        self.flusher.join()
