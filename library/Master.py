from ctypes import *

class Master:
    def __init__(self, mpi, path, num_osts, num_loaders, stride) -> None:
        self.__so_module = CDLL('./library/lib.so')

        create_traverser_c = self.__so_module.create_traverser_c
        create_traverser_c.argtypes = [c_void_p, c_char_p, c_int, c_int, c_int]
        create_traverser_c.restype = c_void_p

        self.__traverser_start = self.__so_module.traverser_start
        self.__traverser_start.argtypes = [c_void_p]
        self.__traverser_start.restype = None

        self.__trav = create_traverser_c(mpi, path, num_osts, num_loaders, stride)

    def start(self):
        self.__traverser_start()