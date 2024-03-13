import threading
import queue
from PIL import Image
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import os
from . import MPI
import struct

class Augmenter(threading.Thread):
    def __init__(self, mpi:MPI.MPI, loader_rank:int, complete_queue:queue.Queue): #mpi, loader_rank, self.complete_queue
        super().__init__()
        self.mpi = mpi
        self.loader_rank = loader_rank
        self.complete_queue = complete_queue

    def run(self):
        while True:
            # Fetch a job from the job queue
            # name, img = self.job_queue.get()
            size_or_terminate = self.mpi.int_recv(self.loader_rank)
            if size_or_terminate == -1:
                self.complete_queue.put((None, None))
                break
            
            received_data = self.mpi.char_recv(self.mpi_rank, size_or_terminate)

            header = received_data[:4]
            name_length = struct.unpack('i', header)[0]
            name = received_data[4:4+name_length].decode('utf-8')
            img_bytes = received_data[4+name_length:]
            img = np.frombuffer(img_bytes, dtype=np.float32)

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
            for i in range(50):
                for batch in datagen.flow(img, batch_size=1):
                    augmented_images.append(batch[0])
                    break  # Generate only one batch per image

            self.complete_queue.put((name, augmented_images))

            # Signal task completion
            # self.job_queue.task_done()

class Flusher(threading.Thread):
    def __init__(self, complete_queue:queue.Queue, size:int, rank:int, num_osts:int, save_path:str):
        super().__init__()
        self.complete_queue = complete_queue
        self.rank = rank
        self.num_osts = num_osts
        self.save_path = save_path

        for i in range(size):
            dir_path = os.path.join(save_path, str(i))
            try:
                os.makedirs(dir_path)
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
                dir_path = os.path.join(self.save_path, str((self.rank-1)%self.num_osts))
                file_name = f"{name}_augmented_image_{i}.png"
                full_path = os.path.join(dir_path, file_name)
                img.save(full_path)

class Worker():
    def __init__(self, mpi:MPI.MPI, loader_rank:int, ost:int, save_path:str):
        self.complete_queue = queue.Queue()
        self.augmenter = Augmenter(mpi, loader_rank, self.complete_queue)
        self.flusher = Flusher(self.complete_queue, ost, save_path)

    def start(self):
        self.augmenter.start()
        self.flusher.start()

    def join(self):
        self.augmenter.join()
        self.flusher.join()
