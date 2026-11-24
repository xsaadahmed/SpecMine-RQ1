"""Narrow source-only checks for framework tests and declaration-only headers."""
from pathlib import PurePosixPath

from detector import parser_for, result, walk


def windows_type_header(source, path):
    """Recognize a complete, narrowly defined Windows compatibility header."""
    if PurePosixPath(path).suffix.lower() not in {'.h', '.hh', '.hpp'}:
        return None
    lines = source.splitlines()
    supported = {
        '#pragma once', '#ifdef _WIN32', '#ifndef NOMINMAX', '#define NOMINMAX',
        '#include <BaseTsd.h>', '#endif', 'typedef SSIZE_T ssize_t;',
    }
    # Ignore only complete one-line comments. Reject continuation lines,
    # preprocessor branches with unknown contents, and all executable code.
    items = [(number, text.strip()) for number, text in enumerate(lines, 1)
             if text.strip() and not text.lstrip().startswith('//')]
    if any(text not in supported for _, text in items) or any(line.rstrip().endswith('\\') for line in lines):
        return None
    shape = ('#pragma once', '#ifdef _WIN32', '#ifndef NOMINMAX', '#define NOMINMAX',
             '#endif', '#include <BaseTsd.h>', 'typedef SSIZE_T ssize_t;', '#endif')
    if tuple(text for _, text in items) != shape:
        return None
    number, symbol = items[-2]
    return result('not_test','cpp','Complete header contains a platform guard and a type alias only',
                  [{'line':number,'symbol':symbol,'kind':'type_alias'}])


def registered_case(source, path):
    suffix = PurePosixPath(path).suffix.lower()
    language = {'.scala':'scala','.rb':'ruby'}.get(suffix)
    if language is None or len(source.encode())>200_000:
        return None
    raw = source.encode()
    root = parser_for(language).parse(raw).root_node
    if root.has_error:
        return None

    def text(node):
        return raw[node.start_byte:node.end_byte].decode() if node else ''

    def reference(node,symbol,kind):
        return {'line':node.start_point.row+1,'symbol':symbol,'kind':kind}

    if language=='scala':
        imports = {text(node) for node in root.named_children if node.type=='import_declaration'}
        required = {'import org.scalatest.wordspec.AnyWordSpec',
                    'import org.scalatest.matchers.should.Matchers'}
        if not required.issubset(imports):
            return None
        if any(node.type in {'class_definition','trait_definition','object_definition','function_definition'}
               and text(node.child_by_field_name('name')) in {'AnyWordSpec','Matchers','shouldBe'}
               for node in walk(root)):
            return None
        def operand(node,name):
            return node.child_by_field_name(name)
        def named_infix(node,operator):
            left,right = operand(node,'left'),operand(node,'right')
            return (node.type=='infix_expression' and text(operand(node,'operator'))==operator
                    and left and left.type=='string' and right and right.type=='block')
        for suite in root.named_children:
            if suite.type!='class_definition' or text(operand(suite,'extend')).split()[:2]!=['extends','AnyWordSpec']:
                continue
            body = operand(suite,'body')
            if body is None:
                continue
            for group in body.named_children:
                if not named_infix(group,'should'):
                    continue
                for case in operand(group,'right').named_children:
                    if not named_infix(case,'in'):
                        continue
                    statements = operand(case,'right').named_children
                    check = next((n for n in statements if n.type=='infix_expression'
                                  and text(operand(n,'operator'))=='shouldBe'),None)
                    if check is not None:
                        return result('automated_test','scala','ScalaTest AnyWordSpec registers a case with a direct expectation',
                                      [reference(operand(case,'operator'),'in','registration'),
                                       reference(operand(check,'operator'),'shouldBe','assertion')])
        return None
    if not any(text(n) in {'require "test_helper"', "require 'test_helper'"} for n in root.named_children):
        return None
    for suite in root.named_children:
        superclass = text(suite.child_by_field_name('superclass')).split()
        # An unqualified project class alone cannot establish the Rails DSL.
        if suite.type!='class' or superclass not in (['<','ActionDispatch::IntegrationTest'],
                                                      ['<','ActiveSupport::TestCase']):
            continue
        body = suite.child_by_field_name('body')
        if not body or any(n.type=='method' and text(n.child_by_field_name('name'))=='test' for n in walk(body)):
            continue
        for case in body.named_children:
            method = case.child_by_field_name('method')
            args = case.child_by_field_name('arguments')
            block = case.child_by_field_name('block')
            statements = block.child_by_field_name('body') if block else None
            if (case.type!='call' or case.child_by_field_name('receiver') or text(method)!='test'
                    or not args or len(args.named_children)!=1 or args.named_children[0].type!='string'
                    or not statements):
                continue
            for check in statements.named_children:
                name = check.child_by_field_name('method')
                if (check.type=='call' and not check.child_by_field_name('receiver') and
                        text(name) in {'assert','assert_equal','assert_response','assert_match','refute'} and
                        check.child_by_field_name('arguments')):
                    return result('automated_test','ruby','Rails test DSL registers a block containing a direct assertion',
                                  [reference(method,'test','registration'),reference(name,text(name),'assertion')])
    return None
