#!/usr/bin/python

import argparse
import re
import os
from string import Template

js_path = None

class TokenList(list):
    def get(self):
        """ removes and returns the first element of the list """
        return self.pop(0)

    def get_expected(self, *args):
        """ 
        removes and returns the first element of the list and expects the poped 
        value to be equal to expected
        """
        actual = self.get()

        for expected in args:
            if actual == expected:
                return actual

        raise LogicError("Expected '" + "' or '".join(expected) + "', but got '"
                + str(actual) + "' instead")

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
    js_file : js_stmt*
    js_stmt : js_block | template_stmt | css_stmt
    template_stmt : "TEMPLATE"! "("! "\"" id "\"" (","! js_expr)* ")"!
    css_stmt : "CSS"! "("! "\"" id "\"" ")"!
    js_expr : id | map
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
DOUBLEQUOTE = "\""
SINGLEQUOTE = "'"
LBRACE = "{"
RBRACE = "}"
COLON = ":"
SEMICOLON = ";"
LPAREN = "("
RPAREN = ")"
TEMPLATE = "TEMPLATE"
CSS = "CSS"

RESERVED_WORDS = [FOR, IF, ELSE, IN, END]

""" AST """
class AST:
    count = 0
    def __init__(self, *args):
        self.child = args
        self.uid = self.count
        AST.count += 1

    def id_var(self):
        return "_" + str(self.uid)

""" JS AST """
class JsFile_AST(AST):
    def out(self, indent=0):
        return out_indent(indent, "(js_file \n" + \
                "\n".join([c.out(indent+4) for c in self.child]) + ")")

    def codegen(self, indent=0):
        return out_indent(indent, 
                "\n".join([c.codegen(indent+4) for c in self.child]))

class TemplateStmt_AST(AST):
    def out(self, indent):
        return out_indent(indent, "(template_stmt \n" + \
                "\n".join([c.out(indent+4) for c in self.child]) + ")")

    def codegen(self, indent=0):
        fp = open(os.path.join(os.path.dirname(js_path), 
                                self.child[0].name + ".html.te"))
        fp_str = fp.read()
        fp.close()
        return out_indent(indent, template_ast(fp_str).codegen())

class CssStmt_AST(AST):
    def out(self, indent=0):
        return out_indent(indent, "(css_stmt \n" + \
                "\n".join([c.out(indent+4) for c in self.child]) + ")")

    def codegen(self, indent=0):
        pass

class Map_AST(AST):
    def out(self, indent=0):
        return out_indent(indent, "(map \n" + \
                "\n".join([c.out(indent+4) for c in self.child]) + ")")

class Pair_AST(AST):
    def out(self, indent=0):
        return out_indent(indent, "(pair " + \
                self.child[0].out(0) + " " + self.child[1].out(0) + ")")

class JsBlock_AST(AST):
    def out(self, indent=0):
        return out_indent(indent, "(js_block " + self.child[0] + ")")

    def codegen(self, indent=0):
        return out_indent(indent, self.child[0])


""" Template AST """
class Module_AST(AST):
    def out(self, indent=0):
        return "(module \n" + \
                "\n".join([c.out(indent+4) for c in self.child]) + ")"

    def codegen(self, indent=0):
        return "".join([c.codegen(indent+4) for c in self.child])

class Block_AST(AST):
    def out(self, indent):
        return out_indent(indent, "(block " + " ".join(self.child) + ")")

    def codegen(self, indent=0):
        return DOUBLEQUOTE + " ".join(self.child) + DOUBLEQUOTE

class Id_AST(AST):
    def __init__(self, name):
        self.name = name

    def out(self, indent):
        return out_indent(indent, "(id " + self.name + ")")

    def codegen(self, indent=0):
        return self.name

class Js_AST(AST):
    def out(self, indent):
        return out_indent(indent, "(js " + " ".join(self.child) + ")")

    def codegen(self, indent=0):
        return "".join(self.child)

class StmtList_AST(AST):
    def out(self, indent):
        return out_indent(indent, "(stmt_list \n" + "\n".join(
            [c.out(indent + 4) for c in self.child]) + ")")

    def codegen(self, indent=0):
        return " + ".join([c.codegen(indent+4) for c in self.child])

class For_AST(AST):
    def __init__(self, iterator_id, iterable, stmt_list):
        self.iterator_id = iterator_id
        self.iterable = iterable
        self.stmt_list = stmt_list

    def out(self, indent):
        return out_indent(indent, "(for " + self.iterator_id.out(0) + " " + 
                self.iterable.out(0) + "\n" + self.stmt_list.out(indent + 4) 
                + ")")
        
    def codegen(self, indent=0):
        t = Template(
"""(function(arr){ 
	var _s = "";  
	for(var i = 0; i < arr.length; i++) {
        $iterator_id = arr[i]
		_s += $stmt_list;
    }
	return _s;
}($iterable));""")
        return t.substitute({
                'iterator_id' : self.iterator_id.codegen(), 
                'iterable' : self.iterable.codegen(),
                'stmt_list' : self.stmt_list.codegen()
            })


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

    def codegen(self, indent=0):
        arg_list = [self.if_stmt]

        if self.else_if_list:
            arg_list.extend(self.else_if_list)

        var_list = [arg[0].id_var() for arg in arg_list]
        js_list = [arg[0].codegen() for arg in arg_list]
        stmt_list = []
        i = 0

        if_template = Template("if($js) { _s += $stmt; }")
        else_if_template = Template("else if($js) { _s += $stmt; }")
        else_template = Template("else { _s += $stmt; }")

        while i < len(arg_list):
            #js = arg_list[i][0].id_var()
            js = arg_list[i][0].codegen()
            stmt = arg_list[i][1].codegen()
            if i == 0:
                stmt_list.append(if_template.substitute(
                    {'js' : js, 'stmt' : stmt}))
            else:
                stmt_list.append(else_if_template.substitute(
                    {'js' : js, 'stmt' : stmt}))
            i += 1
        if self.else_stmt:
            stmt_list.append(else_template.substitute(
                {'stmt' : self.else_stmt.codegen()}))

#        return Template(
#"""(function($var_list) { 
#	var _s;
#    $stmt_list
#	return _s;
#}($js_list));""").substitute({
#        'var_list' : ", ".join(var_list), 
#        'stmt_list' : " ".join(stmt_list),
#        'js_list' : ", ".join(js_list),
#    })
        return Template(
"""(function() { 
	var _s;
    $stmt_list
	return _s;
}());""").substitute({
        'stmt_list' : " ".join(stmt_list),
    })

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
    js_ast = js(token_list) # js
    token_list.get_expected(END_STMT)

    if_tuple = (js_ast, stmt_list(token_list)) # stmt

    else_if_list = []
    
    while(token_list[1] == ELSE and token_list[2] == IF):
        token_list.get_expected(BEGIN_STMT) 
        token_list.get_expected(ELSE) 
        token_list.get_expected(IF) 
        js_ast = js(token_list) # js
        token_list.get_expected(END_STMT)
        else_if_list.append((js_ast, stmt_list(token_list))) # stmt
    
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
def js_file(token_list):
    js_file_args = []
    while len(token_list) > 0:
        js_file_args.append(js_stmt(token_list))
    return JsFile_AST(*js_file_args)

def js_stmt(token_list):
    if re.match(TEMPLATE + "\s*\(", token_list[0]):
        return template_stmt(create_token_list(token_list.get(), 
                [COMMA, TEMPLATE, LPAREN, RPAREN, LBRACE, RBRACE, COLON,
                DOUBLEQUOTE, SINGLEQUOTE]))
    elif re.match(CSS + "\s*\(", token_list[0]):
        return css_stmt(create_token_list(token_list.get(),
            [COMMA, DOUBLEQUOTE, SINGLEQUOTE, LPAREN, RPAREN]))
    else:
        return js_block(token_list)

def css_stmt(token_list):
    template_args = []
    token_list.get_expected(CSS) 
    token_list.get_expected(LPAREN) 
    token_list.get_expected(DOUBLEQUOTE, SINGLEQUOTE) 
    template_args.append(id_parse(token_list)) 
    token_list.get_expected(DOUBLEQUOTE, SINGLEQUOTE) 
    return CssStmt_AST(*template_args)

def js_block(token_list):
    return JsBlock_AST(token_list.get())

def js_expr(token_list):
    if token_list[0] == LBRACE:
        return map_stmt(token_list)
    else:
        return id_parse(token_list)

def map_stmt(token_list):
    pair_list = []
    token_list.get_expected(LBRACE)
    while(token_list[0] != RBRACE):
        if token_list[0] == COMMA:
            token_list.get_expected(COMMA) 
        pair_list.append(pair_stmt(token_list))

    token_list.get_expected(RBRACE)

    return Map_AST(*pair_list)

def pair_stmt(token_list):
    id_ast = id_parse(token_list) # id
    token_list.get_expected(COLON) 
    js_ast = js_expr(token_list) # js
    return Pair_AST(id_ast, js_ast)

def template_stmt(token_list):
    template_args = []
    token_list.get_expected(TEMPLATE) 
    token_list.get_expected(LPAREN) 
    token_list.get_expected(DOUBLEQUOTE, SINGLEQUOTE) 
    template_args.append(id_parse(token_list)) 
    token_list.get_expected(DOUBLEQUOTE, SINGLEQUOTE) 
    
    while(len(token_list) > 1):
        token_list.get_expected(COMMA) 
        if token_list[0] == LBRACE:
            template_args.append(map_stmt(token_list))
        else:
            template_args.append(id_parse(token_list))
    
    token_list.get_expected(RPAREN)

    return TemplateStmt_AST(*template_args)

""" Main """
def create_token_list(template_str, tokens=[]):
    # clean up input
    for token in tokens:
        template_str = template_str.replace(token, " " + token + " ")
    
    # create token list
    return TokenList(template_str.strip().split())

def template_ast(template_str):
    token_list = create_token_list(template_str, [BEGIN_STMT, END_STMT])
    return module(token_list)

def js_ast(js_str):
    token_list = js_lexer(js_str)
    return js_file(token_list)

def js_lexer(js_str, tokens=[TEMPLATE, CSS]):
    """
    >>> tokens = ["TEMPLATE", "CSS"]
    >>> js_lexer("TEMPLATE()", tokens) 
    ['TEMPLATE()']
    >>> js_lexer("TEMPLATE()CSS()", tokens) 
    ['TEMPLATE()', 'CSS()']
    >>> js_lexer("aaaTEMPLATE()bbbCSS()ccc", tokens) 
    ['aaa', 'TEMPLATE()', 'bbb', 'CSS()', 'ccc']
    >>> js_lexer("TEMPLATE()aaaCSS()bbbTEMPLATE()cccCSS()ddd", tokens) 
    ['TEMPLATE()', 'aaa', 'CSS()', 'bbb', 'TEMPLATE()', 'ccc', 'CSS()', 'ddd']
    >>> js_lexer("TEMPLATETEMPLATE()", tokens) 
    ['TEMPLATE', 'TEMPLATE()']
    >>> js_lexer("TEMPLATE    ()", tokens) 
    ['TEMPLATE    ()']
    >>> js_lexer("TEMPLATEaaa()", tokens) 
    ['TEMPLATEaaa()']
    >>> js_lexer("TEMPLATE(aaa, { aaa : bbb(()()) })", tokens) 
    ['TEMPLATE(aaa, { aaa : bbb(()()) })']
    """

    token_list = TokenList()

    pattern = re.compile("(" + "|".join(tokens) + ")\s*\(")

    while True:
        pos = 0
        end_pos = len(js_str)
        found = pattern.match(js_str[pos:end_pos])

        if found:
            token_start = 0
            token_end = found.end() - 1
        else:
            found = pattern.search(js_str[pos:end_pos])
            if found:
                # if we find a token, create token out of the text before it
                # and append it to token_lis
                token_start = found.start()
                token_end = found.end() - 1
                token_list.append(js_str[0:token_start])
            else:
                # if cannot find token, create token for rest of string and 
                # break out of loop
                if pos != end_pos:
                    token_list.append(js_str[pos:end_pos])
                break

        paren_stack = 0
        while True:
            if js_str[token_end] == LPAREN:
                paren_stack += 1
            elif js_str[token_end] == RPAREN:
                paren_stack -= 1

            token_end += 1

            if paren_stack == 0:
                token_list.append(js_str[token_start:token_end])
                break
                
        js_str = js_str[token_end:end_pos]
        
    return token_list

def main():
    """ arguments """
    parser = argparse.ArgumentParser()
    parser.add_argument(
            "--templateast", 
            help="prints the ast given a template file", 
            action="store_true")
    parser.add_argument(
            "--jsast", 
            help="print the ast given a js file", 
            action="store_true")
    parser.add_argument("file", help="input file")
    args = parser.parse_args()
    
    global js_path
    js_path = args.file
    
    """ read file """
    fp = open(args.file)
    fp_str = fp.read()
    fp.close()
    
    """ execute program """
    if args.templateast:
        print template_ast(fp_str).out()
    elif args.jsast:
        print js_ast(fp_str).out()
    else:
        print js_ast(fp_str).codegen()

if __name__ == "__main__":
    main()
