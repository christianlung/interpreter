import copy
from enum import Enum

from brewparse import parse_program
from env_v3 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev3 import Type, Value, create_value, get_printable
from lambdav3 import Lambda, Closure


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        print(ast)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        main_func = self.__get_func_by_name("main", 0)
        self.__run_statements(main_func.get("statements"))

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def

    def __get_func_by_name(self, name, num_params):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.TYPE_ERROR, f"Function {name} not found")
        candidate_funcs = self.func_name_to_ast[name]
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements):
        self.env.push()
        for statement in statements:
            if self.trace_output:
                print(statement)
            status = ExecStatus.CONTINUE
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                self.__call_func(statement)
            elif statement.elem_type == "=":
                self.__assign(statement)
            elif statement.elem_type == InterpreterBase.RETURN_DEF:
                status, return_val = self.__do_return(statement)
            elif statement.elem_type == Interpreter.IF_DEF:
                status, return_val = self.__do_if(statement)
            elif statement.elem_type == Interpreter.WHILE_DEF:
                status, return_val = self.__do_while(statement)

            if status == ExecStatus.RETURN:
                self.env.pop()
                return (status, return_val)
        self.env.pop()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __call_func(self, call_node):
        func_name = call_node.get("name")
        if func_name == "print":
            return self.__call_print(call_node)
        if func_name == "inputi":
            return self.__call_input(call_node)
        if func_name == "inputs":
            return self.__call_input(call_node)

        actual_args = call_node.get("args")
        #extracting formal args
        is_lambda = False
        func_var = self.env.get(func_name)
        if func_var is not None:
            if func_var.type() == Type.FUNCTION: #if variable stores a function
                func_ast = self.__get_func_by_name(func_var.value(), len(actual_args))
                formal_args = func_ast.get("args")
            elif func_var.type() == Type.CLOSURE:  #if variable stores a lambda
                formal_args = func_var.value().lamb().args()
                env_var = func_var.value().lenv()
                is_lambda = True
            else: # if variable does not hold a function or lambda
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"{func_name} is not a lambda or function",
                )
            if len(actual_args) != len(formal_args): # if # of args don't match
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"{func_name} has wrong number of args",
                )
        elif func_name in self.func_name_to_ast:
            func_ast = self.__get_func_by_name(func_name, len(actual_args)) #if function in table
            formal_args = func_ast.get("args")
        else:
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Function {func_name} not found",
                )
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )

        if is_lambda:
            self.env.push()
            for envs in env_var.environment:
                for var, val in envs.items():
                    self.env.create(var,val)

        self.env.push()
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            if formal_ast.elem_type == InterpreterBase.REFARG_DEF:
                if actual_ast.elem_type == InterpreterBase.VAR_DEF:
                    result = Value(Type.REFARG, self.env.get(actual_ast.get("name")))
            else:
                result = copy.deepcopy(self.__eval_expr(actual_ast))
            arg_name = formal_ast.get("name")
            self.env.create(arg_name, result) 
        if is_lambda:
            _, return_val = self.__run_statements(func_var.value().lamb().stats())
        else:
            _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop()

        if is_lambda:
            func_var.value().update(self.env.top())
            self.env.pop()
        
        return return_val

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
            return Value(Type.INT, int(inp))
        if call_ast.get("name") == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        if self.env.get(var_name) is not None and self.env.get(var_name).type() == Type.REFARG:
            self.env.get(var_name).v.t = value_obj.t
            self.env.get(var_name).v.v = value_obj.v
        else:
            self.env.set(var_name, value_obj)

    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.NIL_DEF:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.LAMBDA_DEF:
            return Value(Type.CLOSURE, Closure(Lambda(expr_ast.get("args"), expr_ast.get("statements")), copy.deepcopy(self.env)))
        if expr_ast.elem_type == InterpreterBase.REFARG_DEF:
            return Value(Type.REFARG, expr_ast.get("name"))
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get("name")
            if var_name in self.func_name_to_ast:
                if len(self.func_name_to_ast[var_name]) != 1:
                    super().error(ErrorType.NAME_ERROR, f"{var_name} is ambiguous")
                return Value(Type.FUNCTION, var_name)
            else:
                val = self.env.get(var_name)
                if val is None:
                    super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
                return val
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_DEF:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_DEF:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not bool(x))

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything, allow BOOL and INT comparisons
        if oper in ["==", "!="]:
            return True
        if (obj1.type() == Type.REFARG and obj1.value().type() == obj2.type()): 
            return True
        if (obj2.type() == Type.REFARG and obj2.value().type() == obj1.type()):
            return True
        if obj1.type() in [Type.BOOL, Type.INT] and obj1.type() in [Type.BOOL, Type.INT]:
            return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f):
        #maybe add type checking in here
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        return Value(t, f(value_obj.value()))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            Type.INT, int(x.value()) + int(y.value())
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            Type.INT, int(x.value()) - int(y.value())
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            Type.INT, int(x.value()) * int(y.value())
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            Type.INT, int(x.value()) // int(y.value())
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, y.type() in [Type.BOOL, Type.INT] and bool(x.value()) == bool(y.value())
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, y.type() not in [Type.BOOL, Type.INT] or bool(x.value()) != bool(y.value())
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        self.op_to_lambda[Type.INT]["&&"] = lambda x, y: Value(
            Type.BOOL, bool(x.value()) and bool(y.value())
        )
        self.op_to_lambda[Type.INT]["||"] = lambda x, y: Value(
            Type.BOOL, bool(x.value()) or bool(y.value())
        )

        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), bool(x.value()) and bool(y.value())
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), bool(x.value()) or bool(y.value())
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, y.type() in [Type.BOOL, Type.INT] and bool(x.value()) == bool(y.value())
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, y.type() not in [Type.BOOL, Type.INT] or bool(x.value()) != bool(y.value())
        )
        self.op_to_lambda[Type.BOOL]["+"] = lambda x, y: Value(
            Type.INT, int(x.value()) + int(y.value())
        )
        self.op_to_lambda[Type.BOOL]["-"] = lambda x, y: Value(
            Type.INT, int(x.value()) - int(y.value())
        )
        self.op_to_lambda[Type.BOOL]["*"] = lambda x, y: Value(
            Type.INT, int(x.value()) * int(y.value())
        )
        self.op_to_lambda[Type.BOOL]["/"] = lambda x, y: Value(
            Type.INT, int(x.value()) // int(y.value())
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        # set up operations on functions
        self.op_to_lambda[Type.FUNCTION] = {}
        self.op_to_lambda[Type.FUNCTION]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.FUNCTION]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        # set up operations on lambdas 
        self.op_to_lambda[Type.LAMBDA] = {}
        self.op_to_lambda[Type.LAMBDA]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.LAMBDA]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        # set up operations on closures
        self.op_to_lambda[Type.CLOSURE] = {}
        self.op_to_lambda[Type.CLOSURE]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.CLOSURE]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        # set up operations on refs
        self.op_to_lambda[Type.REFARG] = {}
        self.op_to_lambda[Type.REFARG]["=="] = lambda x, y: Value(
            Type.BOOL, bool(x.value().value()) == bool(y.value())
        )
        self.op_to_lambda[Type.REFARG]["!="] = lambda x, y: Value(
            Type.BOOL, bool(x.value().value()) != bool(y.value())
        )

    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        if result.type() not in  [Type.BOOL, Type.INT]:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if bool(result.value()):
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_while(self, while_ast):
        cond_ast = while_ast.get("condition")
        run_while = Interpreter.TRUE_VALUE
        while run_while.value():
            run_while = self.__eval_expr(cond_ast)
            if run_while.type() not in [Type.BOOL, Type.INT]:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for while condition",
                )
            if bool(run_while.value()):
                statements = while_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.deepcopy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, value_obj)
    