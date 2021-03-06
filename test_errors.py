#!/usr/bin/python

"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect
import sys
import traceback
import types

from pinject import bindings
from pinject import errors
from pinject import object_graph


def _print_raised_exception(exc, fn, *pargs, **kwargs):
    try:
        fn(*pargs, **kwargs)
        raise Exception('failed to raise')
    except exc:
        traceback.print_exc()


def print_ambiguous_arg_name_error():
    class SomeClass():
        def __init__(self, foo):
            pass
    class Foo():
        pass
    class _Foo():
        pass
    obj_graph = object_graph.new_object_graph(classes=[SomeClass, Foo, _Foo])
    _print_raised_exception(errors.AmbiguousArgNameError,
                            obj_graph.provide, SomeClass)


def print_bad_dependency_scope_error():
    class Foo(object):
        pass
    class Bar(object):
        def __init__(self, foo):
            pass
    obj_graph = object_graph.new_object_graph(
        classes=[Foo, Bar], is_scope_usable_from_scope=lambda _1, _2: False)
    _print_raised_exception(errors.BadDependencyScopeError,
                            obj_graph.provide, Bar)


def print_conflicting_bindings_error():
    class SomeBindingSpec(bindings.BindingSpec):
        def configure(self, bind):
            bind('foo', to_instance=1)
            bind('foo', to_instance=2)
    _print_raised_exception(errors.ConflictingBindingsError,
                            object_graph.new_object_graph,
                            binding_specs=[SomeBindingSpec()])


all_print_method_pairs = inspect.getmembers(
    sys.modules[__name__],
    lambda x: (type(x) == types.FunctionType and
               x.__name__.startswith('print_') and
               x.__name__.endswith('_error')))
all_print_method_pairs.sort(key=lambda x: x[0])
all_print_methods = [value for name, value in all_print_method_pairs]
for print_method in all_print_methods:
    print '#' * 78
    print_method()
print '#' * 78
