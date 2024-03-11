from ctypes import *

class MPI:
    __mpi_module = CDLL('./library/lib.so')
    __create_mpi_communication = __mpi_module.create_mpi_communication
    __create_mpi_communication.restype = c_void_p
    __delete_mpi_communication = __mpi_module.delete_mpi_communication
    __delete_mpi_communication.argtypes = [c_void_p]

    def __init__(self):
        self.__mpi_communication = self.__create_mpi_communication()

        self.__get_rank = self.__mpi_module.mpi_get_rank
        self.__get_rank.argtypes = [c_void_p]
        self.__get_rank.restype = c_int
        self.rank = self.__get_rank (self.__mpi_communication)

        self.__get_size = self.__mpi_module.mpi_get_size
        self.__get_size.argtypes = [c_void_p]
        self.__get_size.restype = c_int
        self.size = self.__get_size (self.__mpi_communication)

        self.__get_processor_name = self.__mpi_module.mpi_get_processor_name
        self.__get_processor_name.argtypes = [c_void_p, POINTER(c_char_p), POINTER(c_int)]
        self.__get_processor_name.restype = None
        self.__processor_name = None

        self.__int_send = self.__mpi_module.mpi_int_send
        self.__int_send.argtypes = [c_void_p, c_int, c_int]
        self.__int_send.restype = None

        self.__int_recv = self.__mpi_module.mpi_int_recv
        self.__int_recv.argtypes = [c_void_p, c_int]
        self.__int_recv.restype = c_int

        self.__char_recv = self.__mpi_module.mpi_char_recv
        self.__char_recv.argtypes = [c_void_p, c_int, POINTER(c_char_p), c_int]
        self.__char_recv.restype = None

        self.__barrier = self.__mpi_module.mpi_barrier
        self.__barrier.argtypes = None
        self.__barrier.restype = None

        self.__free_buffer = self.__mpi_module.free_buffer
        self.__free_buffer.argtypes = [c_void_p]
        self.__free_buffer.restype = None

    def __del__(self):
        self.__delete_mpi_communication(self.__mpi_communication)

    def get_communicator(self):
        return self.__mpi_communication

    def Get_processor_name(self):
        if self.__processor_name is None:
            data_buffer = c_char_p()
            data_buffer_size = c_int()
            self.__get_processor_name(self.__mpi_communication, byref(data_buffer), byref(data_buffer_size))
            self.__processor_name = data_buffer.value.decode() 
            self.__free_buffer(data_buffer)

        return self.__processor_name
    
    def int_recv(self, source):
        return self.__int_recv(self.__mpi_communication, c_int(int(source)))#.value
    
    def char_recv(self, source, size):
        data_buffer = c_char_p()
        self.__char_recv(self.__mpi_communication, c_int(int(source)), byref(data_buffer), c_int(int(size)))
        recvdata = string_at(data_buffer, size)
        self.__free_buffer(data_buffer)
        return recvdata
    
    def int_send(self, dest, data):
        self.__int_send(self.__mpi_communication, c_int(int(dest)), c_int(int(data)))

    def barrier(self):
        self.__barrier()
