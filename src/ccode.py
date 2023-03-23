"""This file implements the code models used to analyze C++ code.

author: Lin Huan
Date:   2023/03/23
"""
import collections
import json
import os
from typing import TextIO

import chardet
import random
import logging
import clang.cindex


def set_clang_libpath(lib_path: str):
    """This method is used to reset the library path of libclang to avoid
    compile error in static analysis.

    :param lib_path: the path of directory of the libclang library files
    :return:
    """
    clang.cindex.Config.set_library_path(lib_path)
    return


class CFileReader:
    """CFileReader implements the interface to fetch code from C++ source files
    with a cache strategy. It allows the user to read source files in the cache
    without loading it, until a file not in the cache is met.

    To use CFileReader, simply invoke `code_segment(file_path, offset, length)`.
    """

    def __init__(self):
        self.__files__ = dict()  # map from path of source files to its code
        self.__cache_cap__ = 16  # the capability of the cache to load files
        self.__suffix__ = ['.c', '.cpp', '.h', '.hpp']  # suffix of source file
        self.__parser__ = clang.cindex.Index.create()  # used to parse AST file
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
        if not self.is_source_file(file_path):
            raise TypeError('not C++ file: {}'.format(file_path))
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

    def code_segment(self, file_path: str, offset: int, length: int):
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

    def is_source_file(self, file_path: str):
        """
        :param file_path:
        :return: True if the path of input file is a source code file in C++.
        """
        if not os.path.exists(file_path):
            return False
        elif os.path.isdir(file_path):
            return False
        for suffix in self.__suffix__:
            if file_path.endswith(suffix):
                return True
        return False

    def source_files_in(self, root_path: str):
        """This method finds the set of paths of source code files in the root directory.

        :param root_path: the path of root of the project's directory
        :return: the set of paths of source files in root_path of C++
        """
        queue = collections.deque()
        queue.append(root_path)
        source_files = set()
        while len(queue) > 0:
            file_path = queue.popleft()
            file_path: str
            if not os.path.exists(file_path):
                continue
            elif os.path.isdir(file_path):
                for child_name in os.listdir(file_path):
                    queue.append(os.path.join(file_path, child_name))
            else:
                for suffix in self.__suffix__:
                    if file_path.endswith(suffix):
                        source_files.add(file_path)
                        break
        return source_files

    def parse_trans_unit(self, file_path: str):
        """
        :param file_path: the path of source file being parsed
        :return: the Index of Clang AST traversal
        """
        if self.is_source_file(file_path):
            return self.__parser__.parse(file_path)
        raise FileNotFoundError('{}'.format(file_path))


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


def __ast2json__(reader: CFileReader, src_file: str, node: clang.cindex.Cursor):
    if node is None:
        return None

    node_extend = node.extent
    node_extend: clang.cindex.SourceRange
    beg_pos = node_extend.start
    end_pos = node_extend.end
    beg_pos: clang.cindex.SourceLocation
    end_pos: clang.cindex.SourceLocation
    file_name = ''
    if (beg_pos.file is not None) and (beg_pos.file.name == src_file):
        file_name = beg_pos.file.name
    else:
        return None

    sub_code = ''
    if os.path.exists(file_name):
        try:
            code = reader.code_of_file(file_name)
            sub_code = code[beg_pos.offset: end_pos.offset]
            sub_code = sub_code.replace('\n', ' ')
            sub_code = sub_code.replace('\t', ' ')
        except TypeError:
            pass
    if len(sub_code) > 32:
        sub_code = sub_code[0: 32] + '...'

    parent = {
        'kind': str(node.kind),
        'line': beg_pos.line,
        'column': beg_pos.column,
        'code': sub_code,
        'size': 0,
        'children': list()
    }

    node_def = node.get_definition()
    if node_def is not None:
        node_def: clang.cindex.Cursor
        def_pos = node_def.location
        def_pos: clang.cindex.SourceLocation
        parent['def'] = {
            'kind': '{}'.format(node_def.kind),
            'file': '{}'.format(def_pos.file.name),
            'line': def_pos.line,
            'column': def_pos.column,
        }

    child_number = 0
    for child in node.get_children():
        child_node = __ast2json__(reader, src_file, child)
        child_number += 1
        if child_node is not None:
            parent['children'].append(child_node)
    parent['size'] = child_number
    return parent


def do_visit_ast(reader: CFileReader, src_file: str, out_file: str,
                 translation_unit: clang.cindex.TranslationUnit):
    """
    :param reader:   used to read source code of the C++ file
    :param src_file: the path of source code file be analyzed
    :param out_file: the path of output file to write results
    :param translation_unit: AST translation unit of C++ file
    :return: None
    """
    with open(out_file, 'w') as writer:
        text = json.dumps(__ast2json__(reader, src_file, translation_unit.cursor))
        writer.write(text)
        writer.close()
    return


if __name__ == '__main__':
    # set the libclang library path
    set_clang_libpath('/opt/homebrew/opt/llvm/lib')
    pass_numb, fail_numb = 0, 0
    file_reader = CFileReader()
    root_dir = '/Users/linhuan/Development/MyRepos/cpplinter/examples'
    out_dir = '/Users/linhuan/Development/MyRepos/cpplinter/output'

    # traverse source file and parse
    for c_file in file_reader.source_files_in(root_dir):
        try:
            # file_reader.code_of_file(c_file)
            # file_reader.parse_trans_unit(c_file)
            unit = file_reader.parse_trans_unit(c_file)
            o_file = os.path.join(out_dir, os.path.basename(c_file) + '.json')
            do_visit_ast(file_reader, c_file, o_file, unit)
            pass_numb += 1
        except FileNotFoundError:
            logging.error('\tnot-found: {}'.format(c_file))
            fail_numb += 1
        except UnicodeDecodeError as e:
            logging.error('\tdecode-err: {}'.format(e))
            fail_numb += 1
        except clang.cindex.TranslationUnitLoadError:
            logging.error('\tcannot compile: {}'.format(c_file))
            fail_numb += 1

    # print the summary and exit it
    print('\nSummary: {} pass, {} fail ({}%).'.
          format(pass_numb, fail_numb, __percent__(pass_numb, fail_numb)))

