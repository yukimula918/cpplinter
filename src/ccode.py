"""This file implements the code models used to analyze C++ code.

author: Lin Huan
Date:   2023/03/23
"""
import collections
import os
import chardet
import random
import logging


__CPP_FILE_SUFFIX__ = ['.c', '.cpp', '.h', '.hpp']


def find_c_files_in(root_path: str):
    """This method returns the set of paths of source files in root directory

    :param root_path: the path of root directory as the project's work-space
    :return:          the set of source files fetched from project directory
    """
    queue = collections.deque()
    queue.append(root_path)
    c_file_paths = list()
    while len(queue) > 0:
        file_path = queue.popleft()
        file_path: str
        if not os.path.exists(file_path):
            continue
        elif os.path.isdir(file_path):
            for child_name in os.listdir(file_path):
                child_path = os.path.join(file_path, child_name)
                queue.append(child_path)
        else:
            is_source_file = False
            for suffix in __CPP_FILE_SUFFIX__:
                if file_path.endswith(suffix):
                    is_source_file = True
                    break
            if is_source_file:
                c_file_paths.append(file_path)
    return c_file_paths


def __percent__(x: int, y: int):
    """
    :param x:
    :param y:
    :return: the percent of `x/(x+y)`
    """
    if x == 0:
        return 0.0
    ratio = (x + 0.0) / (x + y + 0.0)
    return int(10000 * ratio) / 100.0


class CFileReader:
    """CFileReader implements the interface to fetch code from C++ source files
    with a cache strategy. It allows the user to read source files in the cache
    without loading it, until a file not in the cache is met.

    To use this reader, simply call method `code_seg(file_path, offset, length)`
    """

    def __init__(self):
        self.__files__ = dict()  # map from path of source files to its code
        self.__cache_cap__ = 16  # the capability of the cache to load files
        return

    def __randomly_clean__(self):
        """This method randomly clean a file with its code from cache to limit the memory used.

        :return: the path of file of which code will be removed or empty if no file is cleaned
        """
        cleaned_files = list()
        while len(self.__files__) > self.__cache_cap__:
            # randomly select a file to be cleaned from cache
            index = random.randint(0, len(self.__files__)-1)
            removed_file = ''
            for file_path, _ in self.__files__.items():
                index -= 1
                removed_file = file_path
                if index < 0:
                    break
            self.__files__.pop(removed_file)  # remove the file
            cleaned_files.append(removed_file)
        return cleaned_files

    def __load_from_file__(self, file_path: str):
        """This method simply loads the code of file in given path to cache

        :param file_path: the path of source file, of which code is loaded
        :return: True iff. the loading succeeds or False otherwise.
        """
        if file_path in self.__files__:
            return True  # the code has been loaded in its cache
        elif not os.path.exists(file_path):
            return False  # cannot read because it does not exist
        elif os.path.isdir(file_path):
            return False  # cannot read because it is not text file

        # fetch the encoding of target file for loading
        raw_data = open(file_path, 'rb').read()
        file_status = chardet.detect(raw_data)
        encoding = 'utf-8'  # default: UTF-8
        if ('encoding' in file_status) and file_status['encoding']:
            encoding = file_status['encoding']

        self.__randomly_clean__()  # randomly clean one if out of cache

        # read the file with given encoding in safe way
        with open(file_path, mode='r', encoding=encoding) as reader:
            code_text = reader.read()
            self.__files__[file_path] = code_text
        return True

    def __load_file__(self, file_path: str):
        """This method loads the code of given file and returns its code

        :param file_path: the path of source file, of which file is read
        :return: the code of the file or raise FileNotFoundError otherwise
        """
        self.__load_from_file__(file_path)
        if file_path in self.__files__:
            code = self.__files__[file_path]
            code: str
            return code
        raise FileNotFoundError(file_path)

    def code_of_file(self, file_path: str):
        """This method returns the code of the source file.

        :param file_path:
        :return:
        """
        return self.__load_file__(file_path)

    def code_seg(self, file_path: str, offset: int, length: int):
        """This method reads the segment of code of given files in the range of [offset, offset+length)

        :param file_path: the path of source file of which code segment will be read
        :param offset:    the offset of the first character being read from the file
        :param length:    the number of characters being read that start from offset
        :return:          the code segment or FileNotFoundError if file_path is none
        """
        file_code = self.__load_file__(file_path)
        if offset < len(file_code):
            return file_code[offset: offset+length]
        raise IndexError('({}, {}) is out of {}'.format(offset, offset+length, len(file_code)))


if __name__ == '__main__':
    print('Start to run ccode.')

    pass_numb, fail_numb = 0, 0
    file_reader = CFileReader()
    for c_file in find_c_files_in('/Users/linhuan/Development/CcRepos'):
        try:
            file_reader.code_of_file(c_file)
            pass_numb += 1
        except FileNotFoundError:
            logging.error('\tnot-found: {}'.format(c_file))
            fail_numb += 1
        except UnicodeDecodeError as e:
            logging.error('\tdecode-err: {}'.format(e))
            fail_numb += 1

    print('\n{} pass, {} fail ({}%).'.
          format(pass_numb, fail_numb, __percent__(pass_numb, fail_numb)))
    print('Complete the ccode.')

