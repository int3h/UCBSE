#!/usr/bin/python

import argparse

class TokenList(list):
    def get(self):
        """ removes and returns the first element of the list """
        return self.pop(0)

    def get_expected(self, expected):
        """ 
        removes and returns the first element of the list and expects the poped 
        value to be equal to expected
        """
        actual = self.get()
        if actual != expected:
            raise LogicError("Expected '" + str(expected) + "', but got '" + 
                    str(actual) + "' instead")
        return actual

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

def expected(word, symbol):
    if word != symbol:
        raise LogicError("Expected '" + symbol + "'.");

class LogicError(Exception):
    pass

"""
Grammar for template files:
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

Grammar for TEMPLATE in js files:
    template_stmt : "TEMPLATE"! "("! "\"" id "\"" (","! js_stmt)* ")"!
    js_stmt : id | map
    map : "{" pair? ("," pair)* "}"
    pair : id ":" js
"""

FOR = "for"
IF = "if"
ELSE = "else"
IN = "in"
END = "end"
BEGIN_STMT = "<%"
END_STMT = "%>"
COMMA = ","
QUOTE = "\""
LBRACE = "{"
RBRACE = "}"
COLON = ":"
LPAREN = "("
RPAREN = ")"
TEMPLATE = "TEMPLATE"

RESERVED_WORDS = [FOR, IF, ELSE, IN, END]

""" AST """
class AST:
    def __init__(self, *args):
        self.child = args

""" JS AST """
class TemplateStmt_AST(AST):
    pass

class Map_AST(AST):
    pass

class Pair_AST(AST):
    pass

""" Template AST """
class Module_AST(AST):
    def __init__(self, *args):
        AST.__init__(self, *args)

    def out(self, indent=0):
        return "(module \n" + \
                "\n".join([c.out(indent+4) for c in self.child]) + ")"

    def codegen(self, indent=0):
        return "".join([c.codegen(indent+4) for c in self.child])

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

""" Template Parser """
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
    token_list.get_expected(BEGIN_STMT) 
    token_list.get_expected(IF) 
    js_stmt = js(token_list) # js
    token_list.get_expected(END_STMT)

    if_tuple = (js_stmt, stmt_list(token_list)) # stmt

    else_if_list = []
    
    while(token_list[1] == ELSE and token_list[2] == IF):
        token_list.get_expected(BEGIN_STMT) 
        token_list.get_expected(ELSE) 
        token_list.get_expected(IF) 
        js_stmt = js(token_list) # js
        token_list.get_expected(END_STMT)
        else_if_list.append((js_stmt, stmt_list(token_list))) # stmt
    
    else_stmt = None
    if(token_list[1] == ELSE):
        token_list.get_expected(BEGIN_STMT) 
        token_list.get_expected(ELSE) 
        token_list.get_expected(END_STMT) 
        else_stmt = stmt_list(token_list) 

    token_list.get_expected(BEGIN_STMT) 
    token_list.get_expected(END)
    token_list.get_expected(END_STMT)

    return If_AST(if_tuple, else_if_list, else_stmt)


def block(token_list):
    child_list = [] 
    i = 0
    while(token_list[0] != BEGIN_STMT):
        child_list.append(token_list.get())
        i += 1
     
    return Block_AST(*child_list)

def js(token_list):
    child_list = [] 
    while(token_list[0] != END_STMT):
        child_list.append(token_list.get())
    
    return Js_AST(*child_list)

def for_stmt(token_list):
    token_list.get_expected(BEGIN_STMT) 
    token_list.get_expected(FOR) 
    iterator_id = id_parse(token_list) # id
    token_list.get_expected(IN) # in 
    iterable = js(token_list) # js
    token_list.get_expected(END_STMT) 
    
    ast = For_AST(iterator_id, iterable, stmt_list(token_list)) # stmt

    token_list.get_expected(BEGIN_STMT)
    token_list.get_expected(END)
    token_list.get_expected(END_STMT) 

    return ast

def stmt(token_list):
    if token_list[0] != BEGIN_STMT:
        return block(token_list)

    if token_list[1] == FOR:
        return for_stmt(token_list)    
    elif token_list[1] == IF:
        return if_stmt(token_list)
    else: # id
        token_list.get()
        id_stmt = id_parse(token_list)
        token_list.get()
        return id_stmt

def id_parse(token_list):
    return Id_AST(token_list.get())

""" JS Parser """
def js_stmt(token_list):
    if token_list[0] == LBRACE:
        return map_stmt(token_list)
    else:
        return id_parse(token_list)

def map_stmt(token_list):
    pair_list = []
    token_list.get_expected(RBRACE)
    while(token_list[0] != RBRACE):
        if token_list[0] == COMMA:
            token_list.get_expected(COMMA) 
        pair_list.append(pair_stmt(token_list))

    token_list.get_expected(RBRACE)

    return Map_AST(*pair_list)

def pair_stmt(token_list):
    id_ast = id_parse(token_list) # id
    token_list.get_expected(COLON) 
    js_ast = js_stmt(token_list) # js
    return Pair_AST(id_ast, js_ast)

def template_stmt(token_list):
    template_args = []
    token_list.get_expected(TEMPLATE) 
    token_list.get_expected(LPAREN) 
    token_list.get_expected(QUOTE) 
    template_args.append(id_parse(token_list)) 
    token_list.get_expected(QUOTE) 
    
    while(token_list[0] != RPAREN):
        if token_list[0] == COMMA:
            token_list.get_expected(COMMA) 
        template_args.append(pair_stmt(token_list))
    
    token_list.get_expected(RPAREN)

    return TemplateStmt_AST(*template_args)

""" Main """
def tokens(file_path):
    template_file = open(file_path)
    template_str = template_file.read()
    template_file.close()
    
    # clean up input
    convert_token_list = [BEGIN_STMT, END_STMT]
    for token in convert_token_list:
        template_str = template_str.replace(token, " " + token + " ")
    
    # create token list
    return TokenList(template_str.strip().split())

def template_ast(file_path):
    token_list = tokens(file_path)
    return module(token_list).out()

def js_ast(file_path):
    token_list = tokens(file_path)
    return template_stmt(token_list).out()

def codegen(file_path):
    token_list = tokens(file_path)
    return module(token_list).codegen()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--templateast", help="prints the ast given a template file", action="store_true")
    parser.add_argument("--jsast", help="print the ast given a js file", action="store_true")
    parser.add_argument("file", help="input file")
    args = parser.parse_args()

    if args.templateast:
        print template_ast(args.file)
    elif args.jsast:
        print js_ast(args.file)
    else:
        print codegen(args.file)

if __name__ == "__main__":
    main()
