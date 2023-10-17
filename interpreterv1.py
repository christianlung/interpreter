from brewparse import parse_program
from intbase import InterpreterBase
from element import Element

class Interpreter(InterpreterBase):
    dictionary = dict()

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor

    #parses program string into program node and runs main node
    def run(self, program):
        program_node = parse_program(program)
        func_node = program_node.get('functions')
        self.run_func(func_node[0]) #func_node[0] in v1 references main() function

    #parses statements from main()
    def run_func(self, func_node):
        for statement in func_node.get('statements'):
            self.run_statement(statement)
    
    #calls respective assignment or function call
    def run_statement(self, statement_node):
        if statement_node.elem_type == '=':
            self.do_assignment(statement_node)
        elif statement_node.elem_type == 'fcall':
            self.func_call(statement_node)
        
    #assigns variable to their expression value
    def do_assignment(self, statement_node):
        target_var_name = statement_node.get('name')
        print(target_var_name)
        source_node = statement_node.get('expression')
        resulting_value = self.evaluate_expression(source_node)
        self.dictionary[target_var_name] = resulting_value
        # print(target_var_name, ' is assigned to ', resulting_value)
    
    #handles types of expressions
    def evaluate_expression(self, expression_node):
        if expression_node.elem_type == 'var':
            return self.dictionary[expression_node.get('name')]
                # return expression_node.get('name')
        elif expression_node.elem_type == 'int' or expression_node.elem_type == 'string':
                return expression_node.get('val')
        elif expression_node.elem_type == '+' or expression_node.elem_type == '-':
                return self.evaluate_binary_operator(expression_node)
    
    #handles +/- expressions
    def evaluate_binary_operator(self, expression_node):
        first_operator = self.evaluate_expression(expression_node.get('op1'))
        second_operator = self.evaluate_expression(expression_node.get('op2'))
        if expression_node.elem_type == '+':
            return first_operator + second_operator
        elif expression_node.elem_type == '-':
             return first_operator - second_operator
                 
    
    # def func_call(self, func_node):
    #     arguments = func_node.get('args')
    #     print_expression
    #     for arg in arguments:
    #         print_expression += str(self.evaluate_expression(arg))   
    #     print(print_expression)
