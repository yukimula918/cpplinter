"""This file implements the linters to check C++ code in AST way.

author: Lin Huan
Date:   2023/03/23
"""
import json
import os
import collections
import clang.cindex
import ccode


class ASTVisitor:
    """ASTVisitor implements the visitor to traverse AST of C++ file.
    """

    def __init__(self, reader: ccode.CFileReader, file_path: str):
        self.reader = reader
        self.tran_unit = reader.parse_trans_unit(file_path)
        self.file_path = file_path
        self.ast_stack = collections.deque()
        self.reports = list()
        return

    def __visit__(self, parent: clang.cindex.Cursor, funcs: list):
        # invalid parameters
        if (parent is None) or (self.tran_unit is None):
            return

        # to avoid AST cursors not in the source file (included from others)
        beg_pos = parent.location
        beg_pos: clang.cindex.SourceLocation
        if (beg_pos.file is None) or (beg_pos.file.name != self.file_path):
            return

        # to perform the static check in the given parent node
        for func in funcs:
            if func is None:
                continue
            func(self, parent)

        # recursively traverse the child nodes
        self.ast_stack.append(parent)
        for child in parent.get_children():
            self.__visit__(child, funcs)
        self.ast_stack.pop()
        return

    def do_report(self, rule_id: str, rule_name: str, trg_node: clang.cindex.Cursor, rule_msg: str):
        """This method generates an error report w.r.t. the linter's rule and given code position

        :param rule_id:
        :param rule_name:
        :param trg_node:
        :param rule_msg:
        :return: it simply updates the reports field of the visitor
        """
        if trg_node is not None:
            report = {
                'id': len(self.reports),
                'rule_id': rule_id,
                'rule_name': rule_name,
                'rule_text': rule_msg,
                'ast_kind': str(trg_node.kind),
            }
            pos = trg_node.location
            pos: clang.cindex.SourceLocation
            end = trg_node.extent.end
            end: clang.cindex.SourceLocation
            if pos.file is not None:
                report['file'] = pos.file.name
                report['line'] = pos.line
                report['column'] = pos.column
                code = self.reader.code_of_file(pos.file.name)
                sub_code = code[pos.offset: end.offset]
                if len(sub_code) > 32:
                    sub_code = sub_code[0: 32] + '...'
                sub_code = sub_code.replace('\n', ' ')
                sub_code = sub_code.replace('\t', ' ')
                sub_code = sub_code.replace('\r', ' ')
                report['err_code'] = sub_code
            self.reports.append(report)
        return

    @staticmethod
    def do_visit(reader: ccode.CFileReader, file_path: str, linters: list):
        visitor = ASTVisitor(reader, file_path)
        visitor.__visit__(visitor.tran_unit.cursor, linters)
        return visitor.reports


__MAX_FUNC_PARAM_NUMB__ = 8


def func_params_linter(visitor: ASTVisitor, node: clang.cindex.Cursor):
    """This method implements the linter to check the length of parameters at function declaration

    :param visitor:
    :param node:
    :return:
    """
    if (visitor is None) or (node is None):
        return

    return


if __name__ == "__main__":
    # initialize the AST visitor
    ccode.set_clang_libpath('/opt/homebrew/opt/llvm/lib')
    pass_numb, fail_numb = 0, 0
    file_reader = ccode.CFileReader()
    root_dir = '/Users/linhuan/Development/MyRepos/cpplinter/examples'
    out_dir = '/Users/linhuan/Development/MyRepos/cpplinter/output'

    # check the C++ source files
    for c_file in file_reader.source_files_in(root_dir):
        o_file = os.path.join(out_dir, os.path.basename(c_file) + '.err.json')
        err_reports = ASTVisitor.do_visit(file_reader, c_file, [func_params_linter])
        with open(o_file, 'w') as writer:
            writer.write(json.dumps(err_reports))
        print('\tFind {} errors in: {}'.format(len(err_reports), c_file))

