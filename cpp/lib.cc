#include <iostream>
#include <filesystem>
#include <chrono>
#include <random>
#include <vector>
#include <cstdlib>
#include <cstring>
#include <mpi.h>
#include <queue>
#include <cstdio>
#include <fstream>
#include <string>
#include <ctime>
#include "lustre/lustreapi.h"

using namespace std;
using namespace std::filesystem;

#define TASK_QUEUE_FULL 4
#define MAX_FILE_PATH_LEN 320

struct FileTask {
    char file_path[MAX_FILE_PATH_LEN];
};

struct CatalogData {
    string filename;
    int ostNumber;
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

        void send(int dest, int tag, const void* data, int count, MPI_Datatype datatype) {
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
        void barrier() {
            MPI_Barrier(MPI_COMM_WORLD);
        }

        double wtime() {
            return MPI_Wtime();
        }

    private:
        int rank, size, processor_name_size, provided;
        char processor_name[MPI_MAX_PROCESSOR_NAME];
};

class Traverser {
private:
    vector<CatalogData> dataList;
    MPICommunication* mpi;
    const char* path;
    int num_osts;
    int localSize;
    int stride;
    OSTWorkerMapper mapper;
    vector<vector<FileTask>> task_queues;
    random_device rd;
    mt19937 gen;
    uniform_int_distribution<int> dis;

    void serialize_and_send(const std::vector<FileTask>& tasks, int dest_rank) {
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
        
        mpi->send(dest_rank+stride, 0, &total_size, 1, MPI_INT);
        mpi->send(dest_rank+stride, 0, buffer, total_size, MPI_CHAR);

        delete[] buffer;
    }
    
    int get_file_ost(const string& file_path) {
        struct llapi_layout *layout = llapi_layout_get_by_path(file_path.c_str(), 0);
        uint64_t ost_index;

        if (layout == NULL) {
            cerr << "Error getting layout for file: " << file_path << endl;
            return -1;
        }

        llapi_layout_comp_use(layout, 1);
        llapi_layout_ost_index_get(layout, 0, &ost_index);
        return ost_index;
    }

public:
    Traverser(MPICommunication* mpi, const char* path, int num_osts, int num_loaders, int stride) 
    : mpi(mpi), path(path), num_osts(num_osts), localSize(num_loaders), stride(stride), 
      mapper(num_osts, num_loaders), task_queues(num_loaders), gen(rd()), dis(0,num_loaders) {
#if CATALOG==1
        ifstream file(path);

        ios::sync_with_stdio(false);

        string line;
        while (getline(file, line)) {
            CatalogData data;
            istringstream iss(line);
            if (!(iss >> data.filename >> data.ostNumber)) {
                break;
            }
            dataList.push_back(data);
        }

        for(auto& data : dataList) {
#if MODE==0
            int dest_rank = mapper.getWorkerForOST(data.ostNumber);
#endif
#if MODE==1
            int dest_rank = dis(gen);
#endif
            FileTask task;
            strncpy(task.file_path, data.filename.c_str(), MAX_FILE_PATH_LEN);
            task.file_path[MAX_FILE_PATH_LEN - 1] = '\0';
            task_queues[dest_rank].push_back(task);
        }
#endif
    }
    ~Traverser() {}

    void catalog_traversal() {
        for (int i = 0; i < localSize; ++i) {
            if (!task_queues[i].empty()) {
                serialize_and_send(task_queues[i], i);
                task_queues[i].clear();
            }
        }

        int termination_signal = -1;
        for (int i = 0; i < localSize; ++i) {
            mpi->send(i+stride, 0, &termination_signal, 1, MPI_INT);
        }
    }

    void directory_traversal() {
#if TIME==1
        double start;
        double sum=0;
        start = mpi->wtime();
#endif

        for (const auto& dir_entry : recursive_directory_iterator(path)) {
            if (is_symlink(dir_entry) || !dir_entry.is_regular_file()) continue;

#if TIME==1
            sum += mpi->wtime() - start;
#endif

#if MODE==0
            int ost = get_file_ost(dir_entry.path().string());
#endif
            
#if MODE==0
            int dest_rank = mapper.getWorkerForOST(ost);
#endif

#if MODE==1
            int dest_rank = dis(gen);
#endif
            FileTask task;
            strncpy(task.file_path, dir_entry.path().string().c_str(), MAX_FILE_PATH_LEN);
            task.file_path[MAX_FILE_PATH_LEN - 1] = '\0';

            task_queues[dest_rank].push_back(task);
#if LOG==1
            cout << dest_rank << " " << task.file_path << endl;
#endif

            if (task_queues[dest_rank].size() >= TASK_QUEUE_FULL) {
                serialize_and_send(task_queues[dest_rank], dest_rank);
                task_queues[dest_rank].clear();
            }

#if TIME==1
            start = mpi->wtime();
#endif
        }

        for (int i = 0; i < localSize; ++i) {
            if (!task_queues[i].empty()) {
#if LOG==1
                cout << i <<"th work start\n";
#endif
                serialize_and_send(task_queues[i], i);
                task_queues[i].clear();
#if LOG==1
                cout << i <<"th work end\n";
#endif
            }
        }

        int termination_signal = -1;
        for (int i = 0; i < localSize; ++i) {
            mpi->send(i+stride, 0, &termination_signal, 1, MPI_INT);
        }
#if TIME==1
        cout << "metadata(dir) io : " << sum << endl;
#endif
    }
};


extern "C" {
    Traverser* create_traverser_c(MPICommunication* mpi, const char* path, int num_osts, int num_loaders, int stride) {
        return new Traverser(mpi, path, num_osts, num_loaders, stride);
    }
    void traverser_start(Traverser* trav) {
#if CATALOG==0
        trav->directory_traversal();
#endif
#if CATALOG==1
        trav->catalog_traversal();
#endif
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
    void mpi_char_send(MPICommunication* mpi_comm, int dest, const char* data, int count) {
        mpi_comm->send(dest, 0, data, count, MPI_CHAR);
    }
    void mpi_char_recv(MPICommunication* mpi_comm, int source, void** data, int count) {
        *data = malloc(count);
        mpi_comm->recv(source, 0, *data, count, MPI_CHAR, NULL);
    }
    void mpi_barrier(MPICommunication* mpi_comm) {
        mpi_comm->barrier();
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
