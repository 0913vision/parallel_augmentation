import threading
import queue
from PIL import Image
import numpy as np
from keras.preprocessing.image import ImageDataGenerator
import multiprocessing as mp

class Augmenter(threading.Thread):
    def __init__(self, job_queue:mp.SimpleQueue, complete_queue:queue.Queue):
        super().__init__()
        self.job_queue = job_queue
        self.complete_queue = complete_queue

    def run(self):
        while True:
            # Fetch a job from the job queue
            name, img = self.job_queue.get()
            if img is None:  # A way to signal termination
                self.complete_queue.put((None,None))
                break
            
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
    def __init__(self, complete_queue:queue.Queue, rank:int, num_osts:int, save_path:str):
        super().__init__()
        self.complete_queue = complete_queue
        self.rank = rank
        self.num_osts = num_osts
        self.save_path = save_path

    def run(self):
        while True:
            # Fetch an augmented image from the complete queue
            name, augmented_images = self.complete_queue.get()
            if augmented_images is None:  # A way to signal termination
                break

            # Save the augmented image to disk
            for i, img_array in enumerate(augmented_images):
                img = Image.fromarray((img_array * 255).astype(np.uint8))
                filename = f'{self.save_path}/./{(self.rank-1) % self.num_osts}/{name}_augmented_image_{i}.png'
                img.save(filename)

class Worker():
    def __init__(self, job_queue:mp.SimpleQueue, rank:int, osts:int, save_path:str):
        self.job_queue = job_queue
        self.complete_queue = queue.Queue()
        self.augmenter = Augmenter(self.job_queue, self.complete_queue)
        self.flusher = Flusher(self.complete_queue, rank, osts, save_path)

    def start(self):
        self.augmenter.start()
        self.flusher.start()

    def join(self):
        self.augmenter.join()
        self.flusher.join()
