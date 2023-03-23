"""This file implements the linters for checking code errors based on AST of C++ source files.

author: Lin Huan
Date:   2023/03/23
"""
import json
import os
import collections
import clang.cindex
import ccode


class AstVisitor:
    """AstVisitor implements a simple stack-based visitor over abstract syntax tree of C++ source files.
    """

    def __init__(self):
        self.__reader__ = ccode.CFileReader()
        self.__f_path__ = None
        self.__t_unit__ = None
        self.__c_stack__ = None
        self.__reports__ = None
        self.__linters__ = None
        return

    def __reset__(self, file_path: str, linters: list):
        """This method resets the status of AstVisitor for analyzing source file.

        :param file_path: the path of source file being checked for its errors
        :param linters: the list of static code linters for checking errors in
        :return: True if the compilation succeeds, or False otherwise
        """
        self.__f_path__ = None
        self.__t_unit__ = None
        self.__c_stack__ = None
        self.__reports__ = None
        self.__linters__ = None
        try:
            tran_unit = self.__reader__.parse_trans_unit(file_path)
            self.__f_path__ = file_path
            self.__t_unit__ = tran_unit
            self.__c_stack__ = collections.deque()
            self.__reports__ = list()
            self.__linters__ = list()
            if linters:
                for linter in linters:
                    if linter is None:
                        continue
                    if isinstance(linter, BaseLinter):
                        self.__linters__.append(linter)
            return True
        except clang.cindex.TranslationUnitLoadError:
            return False

    def do_report(self, rule_id: str, rule_name: str, rule_text: str, trg_node: clang.cindex.Cursor):
        """
        :param rule_id:
        :param rule_name:
        :param rule_text:
        :param trg_node:
        :return: this method simply updates the reports set in the visitor context
        """
        if (trg_node is None) or (self.__reports__ is None):
            return
        report = {
            'rule_id': rule_id,
            'rule_name': rule_name,
            'rule_text': rule_text,
            'ast_kind': str(trg_node.kind),
        }

        beg_pos = trg_node.extent.start
        end_pos = trg_node.extent.end
        beg_pos: clang.cindex.SourceLocation
        end_pos: clang.cindex.SourceLocation
        if beg_pos.file is not None:
            report['file'] = beg_pos.file.name
            report['line'] = beg_pos.line
            report['column'] = beg_pos.column
            try:
                code = self.__reader__.code_of_file(beg_pos.file.name)
                sub_code = code[beg_pos.offset: end_pos.offset]
                if len(sub_code) > 32:
                    sub_code = sub_code[0: 32] + '...'
                sub_code = sub_code.replace('\n', ' ')
                sub_code = sub_code.replace('\t', ' ')
                sub_code = sub_code.replace('\r', ' ')
                report['err_code'] = sub_code
            except UnicodeDecodeError:
                pass
        self.__reports__.append(report)
        return

    def __do_visit__(self, parent: clang.cindex.Cursor):
        """This method implements the recursive access to AST of C++ source code files.

        :param parent:
        :return:
        """
        # to avoid AST traversal when status is undefined
        if (self.__c_stack__ is None) or (parent is None):
            return

        # to avoid AST cursors not in the source file (included from others)
        beg_pos = parent.extent.start
        beg_pos: clang.cindex.SourceLocation
        if (beg_pos.file is None) or (beg_pos.file.name != self.__f_path__):
            return

        # perform the AST-based C++ source code linter
        if self.__linters__:
            for linter in self.__linters__:
                if linter is None:
                    continue
                linter: BaseLinter
                linter.check(self, parent)

        # recursively traverse the AST over the child nodes of the parent one
        self.__c_stack__.append(parent)
        for child in parent.get_children():
            if child is None:
                continue
            self.__do_visit__(child)
        self.__c_stack__.pop()
        return

    def do_file_check(self, file_path: str, linters: list, out_file: str):
        """This method performs static check of linters on the given C++ source file.

        :param file_path:
        :param linters:
        :param out_file:
        :return:
        """
        if self.__reset__(file_path, linters):
            if self.__linters__ and self.__t_unit__:
                self.__do_visit__(self.__t_unit__.cursor)
                with open(out_file, 'w') as writer:
                    writer.write(json.dumps(self.__reports__))
                    writer.close()
        raise InterruptedError('cannot do check for file: {}'.format(file_path))

    def do_all_checks(self, root_path: str, linters: list, out_file: str):
        """This method performs the linters for checking all the source files under root_dir.

        :param root_path:
        :param linters:
        :param out_file:
        :return:
        """
        reports = list()
        for c_file in self.__reader__.source_files_in(root_path):
            if self.__reset__(c_file, linters):
                if self.__linters__ and self.__t_unit__:
                    self.__do_visit__(self.__t_unit__.cursor)
                    if self.__reports__:
                        reports.extend(self.__reports__)
                        print('\tFind {} errors in: {}'.format(len(self.__reports__), c_file))
        with open(out_file, 'w') as writer:
            writer.write(json.dumps(reports))
            writer.close()
        return


class BaseLinter:
    """BaseLinter is the base class of linter for checking errors in C++ source file.
    """

    def check(self, visitor: AstVisitor, node: clang.cindex.Cursor):
        raise NotImplementedError('Please use implemented linter.')


class FuncBodySizeLinter(BaseLinter):
    """FuncBodySizeLinter implements the linter for checking the size of function body.
    """

    def __init__(self, max_body_size: int):
        self.__max_body_size__ = max_body_size
        return

    def check(self, visitor: AstVisitor, node: clang.cindex.Cursor):
        if (visitor is None) or (node is None):
            return
        func_kind = '{}'.format(node.kind)
        if func_kind.endswith('CXX_METHOD') or func_kind.endswith('FUNCTION_DECL'):
            for child in node.get_children():
                if child is None:
                    continue
                child: clang.cindex.Cursor
                child_kind = '{}'.format(child.kind)
                if child_kind.endswith('COMPOUND_STMT'):
                    beg_pos = child.extent.start
                    end_pos = child.extent.end
                    beg_pos: clang.cindex.SourceLocation
                    end_pos: clang.cindex.SourceLocation
                    length = end_pos.line - beg_pos.line
                    if (self.__max_body_size__ > 0) and (length > self.__max_body_size__):
                        visitor.do_report('CPP-000000', 'too_long_func_body',
                                          'too long function body: {} lines'.format(length), child)
        return


class FuncParamNumLinter(BaseLinter):
    """FuncParamNumLinter implements the linter for checking the number of parameters.
    """

    def __init__(self, max_param_num: int):
        self.__max_param_num__ = max_param_num
        return

    def check(self, visitor: AstVisitor, node: clang.cindex.Cursor):
        if (visitor is None) or (node is None):
            return
        parent_kind = '{}'.format(node.kind)
        if parent_kind.endswith('CXX_METHOD') or parent_kind.endswith('FUNCTION_DECL'):
            param_numb = 0
            for child in node.get_children():
                if child is None:
                    continue
                child: clang.cindex.Cursor
                child_kind = '{}'.format(child.kind)
                if child_kind.endswith('PARM_DECL'):
                    param_numb += 1
            if (self.__max_param_num__ > 0) and (param_numb > self.__max_param_num__):
                visitor.do_report('CPP-000001', 'too_many_params_in_func',
                                  'there are too many parameters in func: {} params found'.format(param_numb),
                                  node)
        return


class MagicNumbUseLinter(BaseLinter):
    """MagicNumbUseLinter implements the linter to check the invalid usage of magic numbers.
    """

    def __init__(self, ignore_numbers: list):
        self.__ignore_numbers__ = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
        for ignore_number in ignore_numbers:
            if isinstance(ignore_number, int):
                self.__ignore_numbers__.append(ignore_number)
            if isinstance(ignore_number, float):
                self.__ignore_numbers__.append(ignore_number)
        return

    def __is_ignore_magic__(self, value):
        if isinstance(value, int):
            if (value < 10) and (value > -10):
                return True
            if value in self.__ignore_numbers__:
                return True
            if -value in self.__ignore_numbers__:
                return True
            if value % 10 == 0:
                return True
            if value % 1024 == 0:
                return True
            return False
        if isinstance(value, float):
            if (value < 10) and (value > -10):
                return True
            if value in self.__ignore_numbers__:
                return True
            if -value in self.__ignore_numbers__:
                return True
            return False
        return True

    def check(self, visitor: AstVisitor, node: clang.cindex.Cursor):
        if (visitor is None) or (node is None):
            return
        beg_pos = node.extent.start
        end_pos = node.extent.end
        beg_pos: clang.cindex.SourceLocation
        end_pos: clang.cindex.SourceLocation
        try:
            code = visitor.__reader__.code_of_file(beg_pos.file.name)
        except UnicodeDecodeError:
            return

        node_kind = '{}'.format(node.kind)
        value = None
        if node_kind.endswith('INTEGER_LITERAL'):
            sub_code = code[beg_pos.offset: end_pos.offset]
            try:
                value = int(sub_code)
            except ValueError:
                return
            if self.__is_ignore_magic__(value):
                return
        elif node_kind.endswith('FLOATING_LITERAL'):
            sub_code = code[beg_pos.offset: end_pos.offset]
            try:
                value = float(sub_code)
            except ValueError:
                return
            if self.__is_ignore_magic__(value):
                return
        if value is None:
            return

        parent = visitor.__c_stack__[-1]
        parent: clang.cindex.Cursor
        parent_kind = '{}'.format(parent.kind)
        if not parent_kind.endswith('VAR_DECL'):  # TODO: add more context-based ignorance
            visitor.do_report('CPP-000003', 'magic_number_usage',
                              'magic number {} should not be used'.format(value), node)
        return


if __name__ == '__main__':
    # initialize the AST visitor
    ccode.set_clang_libpath('/opt/homebrew/opt/llvm/lib')
    root_dir = '/Users/linhuan/Development/CcRepos/cppast'
    out_dir = '/Users/linhuan/Development/MyRepos/cpplinter/output'

    lint_visitor = AstVisitor()
    all_linters = [
        FuncBodySizeLinter(16),
        FuncParamNumLinter(4),
        MagicNumbUseLinter([])
    ]
    lint_visitor.do_all_checks(root_dir, all_linters,
                               os.path.join(out_dir, 'issues.json'))

