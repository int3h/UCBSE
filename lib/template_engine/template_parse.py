#!/usr/bin/python

import sys
import argparse

def out_indent(indent, *args):
    """
    >>> out_indent(4, 'a', 'b', 'c')
    '    a b c'
    """
    s = ""
    s += indent * " "
    s += " ".join(args)
    return s

def out_list(indent, delimeter=" ", *args):
    return out_indent(indent, delimeter.join(args))

def isreserved(word):
    for k in RESERVED_WORDS:
        if k == word:
            return True
    return False

class LogicError(Exception):
    pass

"""
Grammar:
    module : stmt*
    stmt : "<%"! "for"! id "in"! js "%>" stmt_list "<%"! "end"! "%>"
         | "<%"! "if"! js "%>" stmt_list 
           ("<%"! "else"! "if"! js "%>" stmt_list)?
           ("<%"! "else"! "%>" stmt_list)?
           "<%"! "end"! "%>"
         | "<%"! id "%>"
         | block
    stmt_list : stmt*
    id : [^\s]*         # includes obj.ref, obj, obj[index], etc.
    block : .*           # everything outside <% ... %>
    js : .*

AST:
    module: stmt | block
    for: id id block
    if: if = (js block) else if = ("else if" js block ...) else = block 

"""

FOR = "for"
IF = "if"
ELSE = "else"
IN = "in"
END = "end"
BEGIN_STMT = "<%"
END_STMT = "%>"

RESERVED_WORDS = [FOR, IF, ELSE, IN, END]

""" AST """
class AST:
    def __init__(self, *args):
        self.child = args


class Module_AST(AST):
    def __init__(self, *args):
        AST.__init__(self, *args)

    def out(self, indent=0):
        return "(module \n" + \
                "\n".join([c.out(indent+4) for c in self.child]) + ")"

class Block_AST(AST):
    def __init__(self, *args):
        AST.__init__(self, *args)

    def out(self, indent):
        return out_indent(indent, "(block " + " ".join(self.child) + ")")

class Id_AST(AST):
    def __init__(self, name):
        self.name = name

    def out(self, indent):
        return out_indent(indent, "(id " + self.name + ")")

class Js_AST(AST):
    def __init__(self, *args):
        AST.__init__(self, *args)

    def out(self, indent):
        return out_indent(indent, "(js " + " ".join(self.child) + ")")

class StmtList_AST(AST):
    def __init__(self, *args):
        AST.__init__(self, *args)
    def out(self, indent):
        return out_indent(indent, "(stmt_list \n" + "\n".join(
            [c.out(indent + 4) for c in self.child]) + ")")


class For_AST(AST):
    def __init__(self, iterator_id, iterable, stmt_list):
        self.iterator_id = iterator_id
        self.iterable = iterable
        self.stmt_list = stmt_list

    def out(self, indent):
        return out_indent(indent, "(for " + self.iterator_id.out(0) + " " + 
                self.iterable.out(0) + "\n" + self.stmt_list.out(indent + 4) 
                + ")")
        
class If_AST(AST):
    def __init__(self, if_stmt, else_if_list=None, else_stmt=None):
        self.if_stmt = if_stmt              # (js, stmt)
        self.else_if_list = else_if_list    # [(js, stmt), (js, stmt), ...]
        self.else_stmt = else_stmt          # block
    
    def out(self, indent):
        s = ""
        s += "(if \n" + self.if_stmt[0].out(indent + 4) + "\n" + \
                self.if_stmt[1].out(indent + 4) + ")\n"
        
        if self.else_if_list:
            t = ""
            t += "\n".join(["(else if \n" + js.out(indent + 4) + "\n" + 
                    stmt.out(indent + 4) + ")"
                    for js, stmt in self.else_if_list])
            s += out_indent(indent, t + "\n")

        if self.else_stmt:
            s += out_indent(indent, 
                    "(else \n" + self.else_stmt.out(indent + 4) + ")")

        return out_indent(indent, s)

""" Parser """
def module(token_list):
    return Module_AST(*stmt_list(token_list).child)

def stmt_list(token_list):
    stmt_list = []
    while len(token_list) > 0:
        if token_list >= 2:
            if token_list[1] == ELSE or \
               token_list[1] == ELSE and token_list[2] == IF or \
               token_list[1] == END:
                   break
        stmt_list.append(stmt(token_list))
    return StmtList_AST(*stmt_list)

def if_stmt(token_list):
    token_list.pop(0)           # <%
    token_list.pop(0)           # "if"
    js_stmt = js(token_list)    # js
    token_list.pop(0)           # %>

    if_tuple = (js_stmt, stmt_list(token_list)) # stmt

    else_if_list = []
    
    while(token_list[1] == ELSE and token_list[2] == IF):
        token_list.pop(0) # <%
        token_list.pop(0) # else
        token_list.pop(0) # if
        js_stmt = js(token_list) # js
        token_list.pop(0) # %>
        else_if_list.append((js_stmt, stmt_list(token_list))) # stmt
    
    else_stmt = None
    if(token_list[1] == ELSE):
        token_list.pop(0) # <%
        token_list.pop(0) # else
        token_list.pop(0) # %>
        else_stmt = stmt_list(token_list) # stmt

    token_list.pop(0) # <%
    if token_list.pop(0) != END: # end
        raise LogicError("Expected 'end' statement")
    token_list.pop(0) # %>

    return If_AST(if_tuple, else_if_list, else_stmt)


def block(token_list):
    child_list = [] 
    i = 0
    while(token_list[0] != BEGIN_STMT):
        child_list.append(token_list.pop(0))
        i += 1
     
    return Block_AST(*child_list)

def js(token_list):
    child_list = [] 
    while(token_list[0] != END_STMT):
        child_list.append(token_list.pop(0))
    
    return Js_AST(*child_list)

def for_stmt(token_list):
    token_list.pop(0) # <%
    token_list.pop(0) # for
    iterator_id = id_parse(token_list) # id
    token_list.pop(0) # in 
    iterable = js(token_list) # js
    token_list.pop(0) # %>
    
    ast = For_AST(iterator_id, iterable, stmt_list(token_list)) # stmt

    token_list.pop(0) # <%
    if token_list.pop(0) != END:
        raise LogicError("Expected 'end' statement")
    token_list.pop(0) # %>

    if len(token_list) >= 2 and token_list[1] == END:
        raise LogicError("Unmatching 'end' statement")

    return ast

def stmt(token_list):
    if token_list[0] != BEGIN_STMT:
        return block(token_list)

    if token_list[1] == FOR:
        return for_stmt(token_list)    
    elif token_list[1] == IF:
        return if_stmt(token_list)
    else: # id
        token_list.pop(0)
        id_stmt = id_parse(token_list)
        token_list.pop(0)
        return id_stmt

def id_parse(token_list):
    return Id_AST(token_list.pop(0))

""" Main """
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ast", help="print the ast", action="store_true")
    parser.add_argument("file", help="the template file")
    args = parser.parse_args()

    template_file = open(args.file)
    template_str = template_file.read()
    template_file.close()
    
    # clean up input
    convert_token_list = [BEGIN_STMT, END_STMT]
    for token in convert_token_list:
        template_str = template_str.replace(token, " " + token + " ")
    
    # create tokens and begin parsing
    token_list = template_str.strip().split()
    
    if args.ast:
        print module(token_list).out()

if __name__ == "__main__":
    main()
