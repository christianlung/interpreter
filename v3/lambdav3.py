import copy 

class Lambda:
    #hold function and copy of captured variables
    def __init__(self, args, statements):
        self.a = args
        self.s = statements
    
    def args(self):
        return self.a

    def stats(self):
        return self.s

class Closure:
    def __init__(self, lamb, env):
        self.l = lamb
        self.e = env
    
    def lamb(self):
        return self.l
    
    def lenv(self):
        return self.e
    
    def update(self, env):
        self.e.environment.append(env)