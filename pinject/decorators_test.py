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
import unittest

from pinject import arg_binding_keys
from pinject import bindings
from pinject import binding_keys
from pinject import decorators
from pinject import errors
from pinject import injection_contexts
from pinject import scoping


# TODO(kurts): have only one FakeObjectProvider for tests.
class FakeObjectProvider(object):

    def provide_class(self, cls, injection_context):
        return 'a-provided-{0}'.format(cls.__name__)

    def provide_from_binding_key(self, binding_key, injection_context):
        return 'provided with {0}'.format(binding_key)

    def call_with_injection(self, provider_fn, injection_context):
        return provider_fn()


# TODO(kurts): have only one call_provisor_fn() for tests.
_UNUSED_INJECTION_CONTEXT = (
    injection_contexts.InjectionContextFactory('unused').new())
def call_provisor_fn(a_binding):
    return a_binding.proviser_fn(_UNUSED_INJECTION_CONTEXT, FakeObjectProvider())


class AnnotateArgTest(unittest.TestCase):

    def test_adds_binding_in_pinject_decorated_fn(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def some_function(foo):
            return foo
        self.assertEqual([arg_binding_keys.new('foo', 'an-annotation')],
                         [binding_key for binding_key in getattr(some_function,
                                                                 decorators._ARG_BINDING_KEYS_ATTR)])


class InjectableTest(unittest.TestCase):

    def test_adds_wrapper_to_init(self):
        class SomeClass(object):
            @decorators.injectable
            def __init__(self, foo):
                return foo
        self.assertTrue(hasattr(SomeClass.__init__, decorators._IS_WRAPPER_ATTR))

    def test_cannot_be_applied_to_non_init_method(self):
        def do_bad_injectable():
            class SomeClass(object):
                @decorators.injectable
                def regular_fn(self, foo):
                    return foo
        self.assertRaises(errors.InjectableDecoratorAppliedToNonInitError,
                          do_bad_injectable)

    def test_cannot_be_applied_to_regular_function(self):
        def do_bad_injectable():
            @decorators.injectable
            def regular_fn(foo):
                return foo
        self.assertRaises(errors.InjectableDecoratorAppliedToNonInitError,
                          do_bad_injectable)


class ProvidesTest(unittest.TestCase):

    def test_sets_arg_values(self):
        @decorators.provides('an-arg-name', annotated_with='an-annotation',
                           in_scope='a-scope-id')
        def provide_foo():
            pass
        [provider_fn_binding] = bindings.get_provider_fn_bindings(provide_foo, ['foo'])
        self.assertEqual(binding_keys.new('an-arg-name', 'an-annotation'),
                         provider_fn_binding.binding_key)
        self.assertEqual('a-scope-id', provider_fn_binding.scope_id)

    def test_at_least_one_arg_must_be_specified(self):
        def do_bad_annotated_with():
            @decorators.provides()
            def provide_foo():
                pass
        self.assertRaises(errors.EmptyProvidesDecoratorError,
                          do_bad_annotated_with)

    def test_cannot_be_applied_twice(self):
        def do_bad_annotated_with():
            @decorators.provides(annotated_with='an-annotation')
            @decorators.provides(annotated_with='an-annotation')
            def provide_foo():
                pass
        self.assertRaises(errors.DuplicateDecoratorError,
                          do_bad_annotated_with)

    def test_uses_default_binding_when_arg_name_and_annotation_omitted(self):
        @decorators.provides(in_scope='unused')
        def provide_foo(self):
            pass
        [provider_fn_binding] = bindings.get_provider_fn_bindings(provide_foo, ['foo'])
        self.assertEqual(binding_keys.new('foo'),
                         provider_fn_binding.binding_key)

    def test_uses_default_scope_when_not_specified(self):
        @decorators.provides('unused')
        def provide_foo(self):
            pass
        [provider_fn_binding] = bindings.get_provider_fn_bindings(provide_foo, ['foo'])
        self.assertEqual(scoping.DEFAULT_SCOPE, provider_fn_binding.scope_id)


class GetProviderFnDecorationsTest(unittest.TestCase):

    def test_returns_defaults_for_undecorated_fn(self):
        def provide_foo():
            pass
        annotated_with, arg_names, in_scope_id = (
            decorators._get_provider_fn_decorations(
                provide_foo, ['default-arg-name']))
        self.assertEqual(None, annotated_with)
        self.assertEqual(['default-arg-name'], arg_names)
        self.assertEqual(scoping.DEFAULT_SCOPE, in_scope_id)

    def test_returns_defaults_if_no_values_set(self):
        @decorators.annotate_arg('foo', 'unused')
        def provide_foo(foo):
            pass
        annotated_with, arg_names, in_scope_id = (
            decorators._get_provider_fn_decorations(
                provide_foo, ['default-arg-name']))
        self.assertEqual(None, annotated_with)
        self.assertEqual(['default-arg-name'], arg_names)
        self.assertEqual(scoping.DEFAULT_SCOPE, in_scope_id)

    def test_returns_set_values_if_set(self):
        @decorators.provides('foo', annotated_with='an-annotation',
                             in_scope='a-scope-id')
        def provide_foo():
            pass
        annotated_with, arg_names, in_scope_id = (
            decorators._get_provider_fn_decorations(
                provide_foo, ['default-arg-name']))
        self.assertEqual('an-annotation', annotated_with)
        self.assertEqual(['foo'], arg_names)
        self.assertEqual('a-scope-id', in_scope_id)


class GetPinjectWrapperTest(unittest.TestCase):

    def test_sets_recognizable_wrapper_attribute(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def some_function(foo):
            return foo
        self.assertTrue(hasattr(some_function, decorators._IS_WRAPPER_ATTR))

    def test_raises_error_if_referencing_nonexistent_arg(self):
        def do_bad_annotate():
            @decorators.annotate_arg('foo', 'an-annotation')
            def some_function(bar):
                return bar
        self.assertRaises(errors.NoSuchArgToInjectError, do_bad_annotate)

    def test_reuses_wrapper_fn_when_multiple_decorators_decorators(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        @decorators.annotate_arg('bar', 'an-annotation')
        def some_function(foo, bar):
            return foo + bar
        self.assertEqual([arg_binding_keys.new('bar', 'an-annotation'),
                          arg_binding_keys.new('foo', 'an-annotation')],
                         [binding_key
                          for binding_key in getattr(some_function,
                                                     decorators._ARG_BINDING_KEYS_ATTR)])

    def test_raises_error_if_annotating_arg_twice(self):
        def do_bad_annotate():
            @decorators.annotate_arg('foo', 'an-annotation')
            @decorators.annotate_arg('foo', 'an-annotation')
            def some_function(foo):
                return foo
        self.assertRaises(errors.MultipleAnnotationsForSameArgError,
                          do_bad_annotate)

    def test_can_call_wrapped_fn_normally(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def some_function(foo):
            return foo
        self.assertEqual('an-arg', some_function('an-arg'))

    def test_can_introspect_wrapped_fn(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def some_function(foo, bar='BAR', *pargs, **kwargs):
            pass
        arg_names, varargs, keywords, defaults = inspect.getargspec(
            some_function)
        self.assertEqual(['foo', 'bar'], arg_names)
        self.assertEqual('pargs', varargs)
        self.assertEqual('kwargs', keywords)
        self.assertEqual(('BAR',), defaults)


class IsExplicitlyInjectableTest(unittest.TestCase):

    def test_non_injectable_class(self):
        class SomeClass(object):
            pass
        self.assertFalse(decorators.is_explicitly_injectable(SomeClass))

    def test_injectable_class(self):
        class SomeClass(object):
            @decorators.injectable
            def __init__(self):
                pass
        self.assertTrue(decorators.is_explicitly_injectable(SomeClass))


class GetInjectableArgBindingKeysTest(unittest.TestCase):

    def assert_fn_has_injectable_arg_binding_keys(self, fn, arg_binding_keys):
        self.assertEqual(
            arg_binding_keys, decorators.get_injectable_arg_binding_keys(fn))

    def test_fn_with_no_args_returns_nothing(self):
        self.assert_fn_has_injectable_arg_binding_keys(lambda: None, [])

    def test_fn_with_unannotated_arg_returns_unannotated_binding_key(self):
        self.assert_fn_has_injectable_arg_binding_keys(
            lambda foo: None, [arg_binding_keys.new('foo')])

    def test_fn_with_annotated_arg_returns_annotated_binding_key(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def fn(foo):
            pass
        self.assert_fn_has_injectable_arg_binding_keys(
            fn, [arg_binding_keys.new('foo', 'an-annotation')])

    def test_fn_with_arg_with_default_returns_nothing(self):
        self.assert_fn_has_injectable_arg_binding_keys(lambda foo=42: None, [])

    def test_fn_with_mixed_args_returns_mixed_binding_keys(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def fn(foo, bar, baz='baz'):
            pass
        self.assert_fn_has_injectable_arg_binding_keys(
            fn, [arg_binding_keys.new('foo', 'an-annotation'),
                 arg_binding_keys.new('bar')])
