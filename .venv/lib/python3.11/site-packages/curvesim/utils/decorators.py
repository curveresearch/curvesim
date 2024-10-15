import functools
import inspect
import re

from curvesim.exceptions import CurvesimException


def cache(user_function, /):
    """
    Simple lightweight unbounded cache.  Sometimes called "memoize".

    Returns the same as lru_cache(maxsize=None), creating a thin wrapper
    around a dictionary lookup for the function arguments. Because it
    never needs to evict old values, this is smaller and faster than
    lru_cache() with a size limit.

    The cache is threadsafe so the wrapped function can be used in
    multiple threads.

    ----
    This isn't in functools until python 3.9, so we copy over the
    implementation as in:
    https://github.com/python/cpython/blob/3.11/Lib/functools.py#L648
    """
    return functools.lru_cache(maxsize=None)(user_function)


def override(method):
    """
    Method decorator to signify and check a method overrides a method
    in a super class.

    Implementation taken from https://stackoverflow.com/a/14631397/1175053
    """
    stack = inspect.stack()
    base_classes = re.search(r"class.+\((.+)\)\s*\:", stack[2][4][0]).group(1)

    # handle multiple inheritance
    base_classes = [s.strip() for s in base_classes.split(",")]
    if not base_classes:
        raise CurvesimException("override decorator: unable to determine base class")

    # stack[0]=overrides, stack[1]=inside class def'n, stack[2]=outside class def'n
    derived_class_locals = stack[2][0].f_locals

    # replace each class name in base_classes with the actual class type
    for i, base_class in enumerate(base_classes):

        if "." not in base_class:
            base_classes[i] = derived_class_locals[base_class]

        else:
            components = base_class.split(".")

            # obj is either a module or a class
            obj = derived_class_locals[components[0]]

            for c in components[1:]:
                assert inspect.ismodule(obj) or inspect.isclass(obj)
                obj = getattr(obj, c)

            base_classes[i] = obj

    if not any(hasattr(cls, method.__name__) for cls in base_classes):
        raise CurvesimException(
            f'Overridden method "{method.__name__}" was not found in any super class.'
        )
    return method
