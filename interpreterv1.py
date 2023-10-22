from brewparse import parse_program
from intbase import InterpreterBase
from intbase import ErrorType
from element import Element

class Interpreter(InterpreterBase):
    dictionary = dict()                     #dictionary of all existing variables to values

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor

    #parses program string into program node and runs main node
    def run(self, program):
        program_node = parse_program(program)
        func_node = program_node.get('functions')       
        self.run_func(func_node[0]) #func_node[0] in v1 references main() function

    #parses statements from main()
    def run_func(self, func_node):
        if func_node.get('name') != 'main':
                super().error(
                    ErrorType.NAME_ERROR, 
                    "No main() function was found",
                )     
        for statement in func_node.get('statements'):
            self.run_statement(statement)
    
    #calls respective assignment or function call
    def run_statement(self, statement_node):
        if statement_node.elem_type == '=':
            self.do_assignment(statement_node)
        elif statement_node.elem_type == 'fcall':   #print()
            self.func_statement_call(statement_node)
        
    #assigns variable to their expression value
    def do_assignment(self, statement_node):
        target_var_name = statement_node.get('name')
        source_node = statement_node.get('expression')
        resulting_value = self.evaluate_expression(source_node)
        self.dictionary[target_var_name] = resulting_value
    
    #handles types of expressions ... variables, ints, strings, operators, fcalls
    def evaluate_expression(self, expression_node):
        if expression_node.elem_type == 'var':
            var_name = expression_node.get('name')
            if not var_name in self.dictionary:
                 super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {var_name} has not been defined",
                )
            else:
                return self.dictionary[var_name]
        elif expression_node.elem_type == 'int' or expression_node.elem_type == 'string':
                return expression_node.get('val')
        elif expression_node.elem_type == '+' or expression_node.elem_type == '-':
                return self.evaluate_binary_operator(expression_node)
        elif expression_node.elem_type == 'fcall':  #inputi()
                return self.func_expression_call(expression_node)
    
    #handles +/- expressions
    def evaluate_binary_operator(self, expression_node):
        #do type checking right here
        first_operator = self.evaluate_expression(expression_node.get('op1'))
        second_operator = self.evaluate_expression(expression_node.get('op2'))

        if expression_node.get('op1').elem_type == 'string' or expression_node.get('op2').elem_type == 'string':
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible types for arithmetic operation",
            )

        if expression_node.elem_type == '+':
            return first_operator + second_operator
        elif expression_node.elem_type == '-':
             return first_operator - second_operator
    
    def func_expression_call(self, expression_node):
         if expression_node.get('name') == 'inputi':
            if len(expression_node.get('args')) > 1:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"No inputi() function found that takes > 1 parameter",
                )
            else:
                if len(expression_node.get('args')) != 0:
                    super().output(self.evaluate_expression(expression_node.get('args')[0]))
                return super().get_input()
             
                 
    
    def func_statement_call(self, statement_node):
        if statement_node.get('name') == 'print':
            arguments = statement_node.get('args')
            print_expression = ""
            for arg in arguments:
                print_expression += str(self.evaluate_expression(arg))   
            super().output(print_expression)