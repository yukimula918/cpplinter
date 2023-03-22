import logging
import collections
import os.path
import datetime
import clang.cindex


class SourceCode:
    """SourceCode implements the interface to read code from source files based on cache strategy.
    """

    def __init__(self):
        self.file_code = dict()
        self.encoding = 'utf-8'
        return

    def __read__(self, file_path: str, encoding='utf-8'):
        """__read__ returns the code of given file with a specified encoding

        :param file_path:
        :param encoding:
        :return:
        """
        if not (file_path in self.file_code):
            reader = open(file_path, 'rb')
            content = reader.read()
            try:
                code = content.decode(encoding)
            except UnicodeDecodeError:
                code = content.decode(self.encoding)  # use default encoding
            self.file_code[file_path] = code
        return self.file_code[file_path]

    def code_in(self, code_range: clang.cindex.SourceRange):
        if code_range is None:
            return ''
        beg_pos = code_range.start
        beg_pos: clang.cindex.SourceLocation
        code = self.__read__(beg_pos.file.name)
        end_pos = code_range.end
        end_pos: clang.cindex.SourceLocation
        return code[beg_pos.offset: end_pos.offset]


def cpp_files_in(dir_path: str):
    """cpp_files_in returns the set of cpp, hpp, c and h files under the directory of input path

    :param dir_path: the path of root directory of C++ project under analysis
    :return: the set of paths of c, cpp, h, hpp files collected in the project
    """
    queue = collections.deque()
    queue.append(dir_path)
    code_files = set()
    while len(queue) > 0:
        file_path = queue.popleft()
        file_path: str
        if os.path.isdir(file_path):
            for child_name in os.listdir(file_path):
                queue.append(os.path.join(file_path, child_name))
        elif file_path.endswith('.c') or file_path.endswith('.cpp') or \
                file_path.endswith('.h') or file_path.endswith('.hpp'):
            code_files.add(file_path)
    return code_files


def parse(c_index: clang.cindex.Index, code_file: str):
    try:
        return c_index.parse(code_file, args=[])
    except clang.cindex.TranslationUnitLoadError as e:
        logging.error('Unable to parse: {}'.format(e))
        return None


if __name__ == '__main__':
    print('Hello, cpplinter.')
    clang.cindex.Config.set_library_path('/opt/homebrew/opt/llvm/lib')  # set the libclang library path
    clang_index = clang.cindex.Index.create()
    repos_dir = '/Users/linhuan/Development/CcRepos'

    pass_numb, fail_numb = 0, 0
    beg_time = datetime.datetime.now()
    for code_file_path in cpp_files_in(repos_dir):
        unit = parse(clang_index, code_file_path)
        if unit is None:
            fail_numb += 1
        else:
            pass_numb += 1
            print('\tpass: {}'.format(code_file_path))
    end_time = datetime.datetime.now()
    duration = end_time - beg_time
    pass_rate = 0.0
    if pass_numb > 0:
        pass_rate = (pass_numb + 0.0) / (pass_numb + fail_numb)
        pass_rate = int(10000 * pass_rate) / 100.0
    print('\n{} pass; {} fail; {}% using {} seconds.'.
          format(pass_numb, fail_numb, pass_rate, int(duration.total_seconds())))

