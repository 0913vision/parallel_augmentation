# Parallel Augmentation Program

## 🏛️ Architecture
This Parallel Augmentation Program is designed with a master-slave architecture consisting of 1 master and N-1 nodes. 

- **Master**: Implemented in C, the master navigates through directories, locates stored OSTs (Object Storage Targets), and assigns tasks to nodes considering these OSTs.
- **Nodes**: Each node is comprised of two types of modules: Loader and Worker.
  - **Loader**: There is one loader per node. It contains two components:
    - **Communicator**: Responsible for receiving a list of files from the master via MPI communication.
    - **Fetcher**: Reads files from the received list, reshapes them, and passes them to the workers. Both components in the loader operate using multithreading.
  - **Worker**: Each node has M-1 workers. A worker includes:
    - **Augmenter**: Generates augmented data from files provided by the loader.
    - **Flusher**: Stores the data created by the augmenter. Both components in the worker also function using multithreading.

## 🚀 Usage
The program is executed as follows:

```bash
mpirun -n [N] python3 ./main.py --vcpu [M] --osts 24 --image_path ./images/ --save_path ./
```
Here, `[N]` represents the total number of processes (1 master + number of nodes), and `[M]` is the sum of 1 loader and the number of workers per node.

## ⚙️ Configuration

- **CPP Directory**: This directory houses the C library source code. It includes essential functionalities such as MPI (Message Passing Interface) integration, LLAPI (Low-Level API) support, and directory traversal operations. 
  - **Compilation**: Use the `compile.sh` script to compile the C source code. The script supports `MODE` and `LOG` flags for version control and logging preferences. After successful compilation, a dynamic library file `lib.so` is generated inside the `library` directory.

- **Library Directory**: Contains Python files, each corresponding to different modules of the program. These files are responsible for handling various operations like communication, data fetching, data augmentation, and data storage in a multi-threaded environment.

- **main.py**: This is the primary Python script that is executed using `mpirun`. It orchestrates the overall process, initiating the MPI environment, and managing the distribution of tasks across the nodes.

## 🏁 Building and Running
- **Building the C Library**: Navigate to the CPP directory and run the `compile.sh` script. Ensure you have the necessary dependencies installed.
- **Running the Program**: Use the command provided in the Usage section to start the program. Adjust the parameters `[N]` and `[M]` as per your setup requirements.

Remember to set the correct paths for `--image_path` (where your images are located) and `--save_path` (where you want the augmented images to be saved).
<!-- For detailed instructions on setup, configuration, and execution, refer to the documentation inside each directory. -->

## 👋 Support and Contributions
For any support requests, bug reports, or contributions, please contact the author or submit an issue/pull request on the project's GitHub repository.
