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