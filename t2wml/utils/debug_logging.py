#Just some basic debugging wrappers

import logging
t2wml_log=logging.getLogger("t2wml-api")
t2wml_log.addHandler(logging.NullHandler())

def fake_basic_debug(func=None):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def real_basic_debug(func=None):
    def wrapper(*args, **kwargs):
        try:
            function_name = func.__func__.__qualname__
        except:
            function_name = func.__qualname__
        t2wml_log.info(f"calling {function_name}")
        try:
            result= func(*args, **kwargs)
            t2wml_log.info(f"returned from {function_name}")
            return result
        except Exception as e:
            t2wml_log.error(f"{function_name} raised {str(e)}")
            raise e
    return wrapper

basic_debug = fake_basic_debug #makes switching between log and non-log version trivial

def details_debug(func=None):
    def wrapper(*args, **kwargs):
        try:
            function_name = func.__func__.__qualname__
        except:
            function_name = func.__qualname__
        t2wml_log.info(f"calling {function_name}") 
        t2wml_log.debug(f"with args {str(args)} and kwargs {str(kwargs)}")
        try:
            result= func(*args, **kwargs)
            t2wml_log.debug(f"{function_name} returned result: {result}")
            return result
        except Exception as e:
            t2wml_log.error(f"{function_name} raised {str(e)}")
            raise e
    return wrapper