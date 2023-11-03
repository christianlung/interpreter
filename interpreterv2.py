from env_v1 import EnvironmentManager
from type_valuev1 import Type, Value, create_value, get_printable
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
import copy


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", "<", "<=", ">", ">=", "||", "&&"}
    UN_OPS = {"!", "neg"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # uses the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        print(ast)
        self.__set_up_function_table(ast)
        main_func = self.__get_func_by_name("main")
        self.env = EnvironmentManager()
        self.__run_statements(main_func.get("statements"))

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            self.func_name_to_ast[func_def.get("name")] = func_def

    def __get_func_by_name(self, name):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        return self.func_name_to_ast[name]

    def __run_statements(self, statements):
        # all statements of a function are held in arg3 of the function AST node
        for statement in statements:
            if self.trace_output:
                print(statement)
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                self.__call_func(statement)
            elif statement.elem_type == "=":
                self.__assign(statement)
            elif statement.elem_type == "if":
                self.__handle_if(statement)
            elif statement.elem_type == "while":
                self.__handle_while(statement)
            elif statement.elem_type == "return":
                self.__handle_return(statement)
        return Interpreter.NIL_DEF

    def __call_func(self, call_node):
        func_name = call_node.get("name")
        if func_name == "print":
            return self.__call_print(call_node)
        elif func_name == "inputi":
            return self.__call_input(call_node)
        elif func_name in self.func_name_to_ast:
            return self.__run_statements(self.__get_func_by_name(func_name).get("statements"))
        # add code here later to call other functions
        super().error(ErrorType.NAME_ERROR, f"Function {func_name} not found")

    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.get("args"):
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, call_ast):
        args = call_ast.get("args")
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if call_ast.get("name") == "inputi":
            try:
                return Value(Type.INT, int(inp))
            except ValueError:
                return Value(Type.STRING, inp)
        # we can support inputs here later

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        self.env.set(var_name, value_obj)

    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == Interpreter.NIL_DEF:
            return Value(Type.NIL, "")
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get("name")
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS or expr_ast.elem_type in Interpreter.UN_OPS:
            return self.__eval_op(expr_ast)

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible operator {arith_ast.get_type} for type {left_value_obj.type()}",
                )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        if arith_ast.elem_type in Interpreter.BIN_OPS:
            right_value_obj = self.__eval_expr(arith_ast.get("op2"))
            if left_value_obj.type() != right_value_obj.type():
                if arith_ast.elem_type == "==" or arith_ast.elem_type == "!=":
                    return Value( Type.BOOL, InterpreterBase.FALSE_DEF)
                else:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Incompatible types for {arith_ast.elem_type} operation",
                    )
            return f(left_value_obj, right_value_obj)
        return f(left_value_obj)
    
    def __handle_if(self, if_node):
        cond = self.__eval_expr(if_node.get("condition"))   #returns a Value object
        if cond.type() != Type.BOOL:
            super().error(
                        ErrorType.TYPE_ERROR,
                        f"Condition does not evaluate to Bool",
                    )
        if cond.value():
            self.__run_statements(if_node.get("statements"))
        elif if_node.get("else_statements") is not None:
            self.__run_statements(if_node.get("else_statements"))

    def __handle_while(self, while_node):
        cond = self.__eval_expr(while_node.get("condition"))
        if cond.type() != Type.BOOL:
            super().error(
                        ErrorType.TYPE_ERROR,
                        f"Condition does not evaluate to Bool",
                    )
        while self.__eval_expr(while_node.get("condition")).value():
            self.__run_statements(while_node.get("statements"))
    
    def __handle_return(self, return_node):
        expr = return_node.get("expression")
        if expr is None:
            return Interpreter.NIL_DEF
        return copy.deepcopy(self.__eval_expr(expr))
        

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value( x.type(), x.value() + y.value() )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value( x.type(), x.value() - y.value() )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value( x.type(), x.value() * y.value() )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value( x.type(), x.value() // y.value() )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value( Type.BOOL, x.value() == y.value() )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value( Type.BOOL, x.value() != y.value() )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value( Type.BOOL, x.value() < y.value() )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value( Type.BOOL, x.value() <= y.value() )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value( Type.BOOL, x.value() > y.value() )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value( Type.BOOL, x.value() >= y.value() )
        self.op_to_lambda[Type.INT]["neg"] = lambda x: Value( Type.INT, x.value() * -1 )

        # set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value( x.type(), x.value() + y.value() )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value( Type.BOOL, x.value() == y.value() )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value( Type.BOOL, x.value() != y.value() )

        # set up operation on booleans
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value( Type.BOOL, x.value() or y.value() )
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value( Type.BOOL, x.value() and y.value() )
        self.op_to_lambda[Type.BOOL]["!"] = lambda x: Value( x.type(), not x.value() )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x,y: Value( Type.BOOL, x.value() == y.value() )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x,y: Value( Type.BOOL, x.value() != y.value() )

interpreter = Interpreter()
program = """
func fact(n) {
  return n;
}

func main(){
    print(fact(5));
}
"""

interpreter.run(program)