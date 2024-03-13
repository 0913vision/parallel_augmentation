from ctypes import *

class Master:
    def __init__(self, mpi, directory, num_osts, num_loaders, stride) -> None:
        self.__so_module = CDLL('./library/lib.so')
        self.__mpi = mpi
        self.__directory_traversal = self.__so_module.directory_traversal_c
        self.__directory_traversal.argtypes = [c_void_p, c_char_p, c_int, c_int]
        self.__directory_traversal.restype = None
        self.__directory = directory
        self.__num_osts = num_osts
        self.__loaders = num_loaders
        self.__stride = stride

    def start(self):
        self.__directory_traversal(self.__mpi.get_communicator(), self.__directory.encode('utf-8'), c_int(int(self.__num_osts)), c_int(int(self.__num_loaders)), c_int(int(self.__stride)))