"""
Singleton class to manage the system clock.
"""

class SysClk:
    __instance__ = None

    def __init__(self):
        if SysClk.__instance__ is None:
            SysClk.__instance__ = self
        else:
            raise Exception("This class is a singleton!")

        SysClk.__instance__ = self
        self.__clk = 0

    @staticmethod
    def get_instance():
        if SysClk.__instance__ is None:
            SysClk()
        return SysClk.__instance__

    def get_clk(self):
        return self.__clk

    def tick(self):
        self.__clk += 1

    def reset(self):
        self.__clk = 0
    
    
"""
Useful utils
"""

from wdmsim.models.sim_instance import SimInstance


def execute_at_init(func):
    """
    Decorator to verify that the function is called at initialization
    """
    def wrapper(self, *args, **kwargs):
        try:
            if self.sysclk == 0:
                return func(self, *args, **kwargs)
            else:
                print("Cannot execute function, sysclk is not zero.")
        except AttributeError:
            if isinstance(self, SimInstance):
                print(f"Cannot execute function, sysclk is not defined in {self.__class__.__name__}")
            else:
                print("Cannot execute function, not a SimInstance.")
    return wrapper

def reset_sysclk(func):
    """
    Decorator to reset sysclk to zero
    """
    def wrapper(self, *args, **kwargs):
        try:
            self.sysclk = 0
            return func(self, *args, **kwargs)
        except AttributeError:
            if isinstance(self, SimInstance):
                print(f"Cannot execute function, sysclk is not defined in {self.__class__.__name__}")
            else:
                print("Cannot execute function, not a SimInstance.")
    return wrapper


