# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
from type_valuev3 import Type

class EnvironmentManager:
    def __init__(self):
        self.environment = [{}]

    def __len__(self):
        return len(self.environment)
    #returns environment at the top of the stack
    def top(self):
        return self.environment[-1]
    
    
    # returns a VariableDef object
    def get(self, symbol):
        for env in reversed(self.environment):
            if symbol in env:
                if env[symbol].type() == Type.REFARG:
                    return env[symbol].value()
                return env[symbol]

        return None

    def set(self, symbol, value):
        for env in reversed(self.environment):
            if symbol in env:
                if env[symbol].type() == Type.REFARG:
                    env[symbol].v.t = value.t
                    env[symbol].v.v = value.v
                    return
                env[symbol] = value
                return

        # symbol not found anywhere in the environment
        self.environment[-1][symbol] = value
  
    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value):
        self.environment[-1][symbol] = value

    # used when we enter a nested block to create a new environment for that block
    def push(self):
        self.environment.append({})  # [{}] -> [{}, {}]

    # used when we exit a nested block to discard the environment for that block
    def pop(self):
        self.environment.pop()