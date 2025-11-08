#!/usr/bin/env python3
"""Pre-commit hook to remove inline comments from function bodies."""

import ast
import sys
from typing import List


class InlineCommentRemover(ast.NodeVisitor):
    """Remove inline comments from function bodies"""

    def __init__(self, filename: str, lines: List[str]):
        self.filename = filename
        self.lines = lines
        self.lines_to_remove = set()
        self.modified = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions"""
        if not node.body:
            self.generic_visit(node)
            return

        body_start = node.body[0].lineno - 1
        body_end = node.body[-1].end_lineno or (body_start + 1)

        for line_num in range(body_start, body_end):
            if line_num >= len(self.lines):
                break

            line = self.lines[line_num]
            stripped = line.strip()

            if not stripped or stripped.startswith('"""') or stripped.startswith("'''"):
                continue

            comment_pos = line.find("#")
            if comment_pos != -1:
                before_comment = line[:comment_pos]
                single_q = before_comment.count("'") - before_comment.count("\\'")
                double_q = before_comment.count('"') - before_comment.count('\\"')

                if single_q % 2 == 0 and double_q % 2 == 0:
                    if before_comment.strip():
                        self.lines[line_num] = before_comment.rstrip()
                        self.modified = True
                    else:
                        self.lines_to_remove.add(line_num)
                        self.modified = True

        self.generic_visit(node)


def process_file(filepath: str) -> bool:
    """Process single file, remove comments and return if modified"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        tree = ast.parse(content, filename=filepath)
        remover = InlineCommentRemover(filepath, lines)
        remover.visit(tree)

        if remover.modified:
            keep = [lines[i] for i in range(len(lines)) if i not in remover.lines_to_remove]
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(keep))
            print(f"Fixed: {filepath}")
            return True
        return False

    except SyntaxError:
        return False
    except Exception:
        return False


def main(argv: List[str] | None = None) -> int:
    """Main function"""
    argv = argv or sys.argv[1:]

    modified = False
    for filepath in argv:
        if process_file(filepath):
            modified = True

    return 1 if modified else 0


if __name__ == "__main__":
    sys.exit(main())
