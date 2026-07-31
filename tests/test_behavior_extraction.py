"""Tests for behavioral extraction from function bodies."""
import ast
import pytest
from architecture_model.manifest.behavior import extract_call_order, extract_control_flow, extract_guards


class TestCallOrder:
    def test_simple_sequence(self):
        code = 'def f(x):\n    validate(x)\n    result = transform(x)\n    save(result)\n    return result\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == ["validate", "transform", "save"]

    def test_method_calls(self):
        code = 'def run(self):\n    self.setup()\n    data = self.fetch()\n    self.process(data)\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == ["self.setup", "self.fetch", "self.process"]

    def test_nested_calls_innermost_first(self):
        code = 'def f(x):\n    return save(transform(validate(x)))\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == ["validate", "transform", "save"]

    def test_conditional_calls_all_branches(self):
        code = 'def f(x):\n    check(x)\n    if x > 0:\n        positive(x)\n    else:\n        negative(x)\n    finish()\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == ["check", "positive", "negative", "finish"]

    def test_no_calls_empty(self):
        code = 'def f():\n    return 1 + 2\n'
        func = ast.parse(code).body[0]
        assert extract_call_order(func) == []


class TestControlFlow:
    def test_try_except(self):
        code = 'def f():\n    try:\n        do()\n    except ValueError:\n        handle()\n'
        func = ast.parse(code).body[0]
        assert "try_except" in extract_control_flow(func)

    def test_for_loop(self):
        code = 'def f(items):\n    for i in items:\n        process(i)\n'
        func = ast.parse(code).body[0]
        assert "for_loop" in extract_control_flow(func)

    def test_while_loop(self):
        code = 'def f():\n    while True:\n        pass\n'
        func = ast.parse(code).body[0]
        assert "while_loop" in extract_control_flow(func)

    def test_with_context(self):
        code = 'def f():\n    with open("x") as fh:\n        pass\n'
        func = ast.parse(code).body[0]
        assert "with_context" in extract_control_flow(func)

    def test_generator(self):
        code = 'def f():\n    yield 1\n    yield 2\n'
        func = ast.parse(code).body[0]
        assert "generator" in extract_control_flow(func)

    def test_if_chain(self):
        code = 'def f(x):\n    if x == 1:\n        pass\n    elif x == 2:\n        pass\n    elif x == 3:\n        pass\n'
        func = ast.parse(code).body[0]
        assert "if_chain" in extract_control_flow(func)

    def test_recursion(self):
        code = 'def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n'
        func = ast.parse(code).body[0]
        assert "recursion" in extract_control_flow(func)

    def test_async_for(self):
        code = 'async def f():\n    async for item in stream():\n        pass\n'
        func = ast.parse(code).body[0]
        assert "async_for" in extract_control_flow(func)

    def test_async_with(self):
        code = 'async def f():\n    async with lock():\n        pass\n'
        func = ast.parse(code).body[0]
        assert "async_with" in extract_control_flow(func)

    def test_no_flow_empty(self):
        code = 'def f():\n    return 42\n'
        func = ast.parse(code).body[0]
        assert extract_control_flow(func) == []


class TestGuards:
    def test_assert_guard(self):
        code = 'def f(x):\n    assert x > 0\n    return x * 2\n'
        func = ast.parse(code).body[0]
        assert any("assert" in g for g in extract_guards(func))

    def test_raise_guard(self):
        code = 'def f(x):\n    if x is None:\n        raise ValueError("x required")\n    return x\n'
        func = ast.parse(code).body[0]
        assert any("raise" in g for g in extract_guards(func))

    def test_early_return_guard(self):
        code = 'def f(x):\n    if not x:\n        return None\n    return process(x)\n'
        func = ast.parse(code).body[0]
        assert any("return" in g for g in extract_guards(func))

    def test_no_guards(self):
        code = 'def f(x):\n    return x + 1\n'
        func = ast.parse(code).body[0]
        assert extract_guards(func) == []

    def test_only_first_6_stmts(self):
        code = 'def f(x):\n    a = 1\n    b = 2\n    c = 3\n    d = 4\n    e = 5\n    f = 6\n    assert x > 0\n    return x\n'
        func = ast.parse(code).body[0]
        # assert is at stmt 7, beyond first 6
        assert extract_guards(func) == []
