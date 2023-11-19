# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
class EnvironmentManager:
    def __init__(self):
        self.environment = [{}]

    def __len__(self):
        return len(self.environment)
    #returns environment at the top of the stack
    def top(self):
        return self.environment[-1]
    
    def second_to_top(self):
        return self.environment[-2]
    
    # returns a VariableDef object
    def get(self, symbol):
        for env in reversed(self.environment):
            if symbol in env:
                return env[symbol]

        return None

    def set(self, symbol, value):
        for env in reversed(self.environment):
            if symbol in env:
                env[symbol] = value
                return

        # symbol not found anywhere in the environment
        self.environment[-1][symbol] = value

    def copy_down(self):
        if len(self.environment)>1:
            for var in self.environment[-3].keys():
                if var in self.environment[-2].keys():
                    self.environment[-3][var] = self.environment[-2][var]

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