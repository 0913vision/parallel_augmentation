#include <iostream>
#include <filesystem>
#include <chrono>
#include <vector>
#include <cstdlib>
#include <cstring>
#include <mpi.h>
#include <queue>

#if MODE==1
#include <random>
#endif

#if MODE<2
#include "lustre/lustreapi.h"
#endif

#if MODE==2
#include <cstdio>
#endif

using namespace std;
using namespace std::filesystem;

#define TASK_QUEUE_FULL 4
#define MAX_FILE_PATH_LEN 320

struct FileTask {
    char file_path[MAX_FILE_PATH_LEN];
};

class OSTWorkerMapper {
private:
    int num_osts, num_workers;
    std::vector<std::queue<int>> workers_for_ost;

public:
    OSTWorkerMapper(int n, int m) : num_osts(n), num_workers(m) {
        for (int i = 0; i < n; ++i) {
            std::queue<int> worker_queue;
            for (int j = 0; j < m; ++j) {
                if (j % n == i) {
                    worker_queue.push(j);
                }
            }
            workers_for_ost.push_back(worker_queue);
        }
    }

    int getWorkerForOST(int ost_id) {
        if (num_osts >= num_workers) {
            return ost_id % num_workers;
        } else {
            std::queue<int>& worker_queue = workers_for_ost[ost_id];
            int assigned_worker = worker_queue.front();
            worker_queue.pop();
            worker_queue.push(assigned_worker);
            return assigned_worker;
        }
    }
};

class MPICommunication {
    public:
        MPICommunication() {
            MPI_Init_thread(NULL, NULL, MPI_THREAD_MULTIPLE, &provided);
            if (provided < MPI_THREAD_MULTIPLE) {
                MPI_Abort(MPI_COMM_WORLD, EXIT_FAILURE);
            }
            MPI_Comm_rank(MPI_COMM_WORLD, &rank);
            MPI_Comm_size(MPI_COMM_WORLD, &size);
            MPI_Get_processor_name(processor_name, &processor_name_size);
        }

        ~MPICommunication() {
            MPI_Finalize();
        }

        void send(int dest, int tag, void* data, int count, MPI_Datatype datatype) {
            MPI_Send(data, count, datatype, dest, tag, MPI_COMM_WORLD);
        }

        void recv(int source, int tag, void* data, int count, MPI_Datatype datatype, MPI_Status* status) {
            MPI_Recv(data, count, datatype, source, tag, MPI_COMM_WORLD, status);
        }

        int getRank() {
            return rank;
        }

        int getSize() {
            return size;
        }

        char* getProcessorName(int* size) {
            *size = processor_name_size;
            return processor_name;
        }

    private:
        int rank, size, processor_name_size, provided;
        char processor_name[MPI_MAX_PROCESSOR_NAME];
};

void serialize_and_send(MPICommunication& mpi, const std::vector<FileTask>& tasks, int dest_rank) {
    int total_size = 0;
    for (const auto& task : tasks) {
        total_size += strlen(task.file_path) + 1;
    }

    char* buffer = new char[total_size];
    char* buffer_ptr = buffer;
    for (const auto& task : tasks) {
        strcpy(buffer_ptr, task.file_path);
        buffer_ptr += strlen(task.file_path) + 1;
    }
    
    mpi.send(dest_rank+1, 0, &total_size, 1, MPI_INT);
    mpi.send(dest_rank+1, 0, buffer, total_size, MPI_CHAR);

    delete[] buffer;
}

#if MODE<2
int get_file_ost(const string& file_path) {
    struct llapi_layout *layout = llapi_layout_get_by_path(file_path.c_str(), 0);
    int ost_index;

    if (layout == NULL) {
        cerr << "Error getting layout for file: " << file_path << endl;
        return -1;
    }

    llapi_layout_comp_use(layout, 1);
    llapi_layout_ost_index_get(layout, 0, &ost_index);
    return ost_index;
}
#endif

void directory_traversal(MPICommunication* mpi, const char* directory_path, int num_osts) {
    int localSize = mpi->getSize()-1;
    vector<vector<FileTask>> task_queues(localSize);
    string path_string(directory_path);
    OSTWorkerMapper mapper(num_osts, localSize);

    #if MODE==1
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<int> dis(0, num_osts-1);
    #endif

    #if MODE==2
    int dum = 0;
    #endif

    for (const auto& dir_entry : directory_iterator(directory_path)) {
        if (is_symlink(dir_entry) || !dir_entry.is_regular_file()) {
            continue;
        }

        #if MODE==0
        int ost = get_file_ost(dir_entry.path().string());
        #endif

        #if MODE==1
        int ost = dis(gen);
        #endif
        
        #if MODE==2
        int ost = dum++ % num_osts;
        #endif
        
        int dest_rank = mapper.getWorkerForOST(ost);

        FileTask task;
        strncpy(task.file_path, dir_entry.path().string().c_str(), MAX_FILE_PATH_LEN);
        task.file_path[MAX_FILE_PATH_LEN - 1] = '\0';

        task_queues[dest_rank].push_back(task);
        #if LOG==1
        cout << dest_rank << " " << task.file_path << endl;
        #endif

        if (task_queues[dest_rank].size() >= TASK_QUEUE_FULL) {
            serialize_and_send(*mpi, task_queues[dest_rank], dest_rank);
            task_queues[dest_rank].clear();
        }
    }

    for (int i = 0; i < localSize; ++i) {
        if (!task_queues[i].empty()) {
            #if LOG==1
            cout << i <<"th work start\n";
            #endif
            serialize_and_send(*mpi, task_queues[i], i);
            task_queues[i].clear();
            #if LOG==1
            cout << i <<"th work end\n";
            #endif
        }
    }

    int termination_signal = -1;
    for (int i = 1; i <= localSize; ++i) {
        mpi->send(i, 0, &termination_signal, 1, MPI_INT);
    }
}

extern "C" {
    void directory_traversal_c(MPICommunication* mpi, const char* directory_path, int localSize) {
        directory_traversal(mpi, directory_path, localSize);
    }

    MPICommunication* create_mpi_communication() {
        return new MPICommunication();
    }
    void delete_mpi_communication(MPICommunication* mpi_comm) {
        delete mpi_comm;
    }
    void mpi_int_send(MPICommunication* mpi_comm, int dest, int data) {
        int d = data;
        mpi_comm->send(dest, 0, &d, 1, MPI_INT);
    }
    int mpi_int_recv(MPICommunication* mpi_comm, int source) {
        int ret;
        mpi_comm->recv(source, 0, &ret, 1, MPI_INT, NULL);
        return ret;
    }
    void mpi_char_recv(MPICommunication* mpi_comm, int source, void** data, int count) {
        *data = malloc(count);
        mpi_comm->recv(source, 0, *data, count, MPI_CHAR, NULL);
    }
    int mpi_get_rank(MPICommunication* mpi_comm) {
        return mpi_comm->getRank();
    }
    int mpi_get_size(MPICommunication* mpi_comm) {
        return mpi_comm->getSize();
    }
    void mpi_get_processor_name(MPICommunication* mpi_comm, void** buf, int* size) {
        *buf = mpi_comm->getProcessorName(size);
    }
    void free_buffer(void* data) {
        free(data);
    }
}