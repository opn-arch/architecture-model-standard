def test_instrumented_is_transparent_when_no_store():
    from architecture_model.sil.decorators import instrumented

    calls = []

    @instrumented("stage:test")
    def add(a, b):
        calls.append((a, b))
        return a + b

    assert add(2, 3) == 5
    assert calls == [(2, 3)]


def test_instrumented_reraises_exceptions_when_no_store():
    from architecture_model.sil.decorators import instrumented
    import pytest

    @instrumented("stage:boom")
    def boom():
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        boom()


def test_instrumented_works_on_methods():
    from architecture_model.sil.decorators import instrumented

    class Stage:
        @instrumented("stage:x")
        def run(self, ctx):
            return ctx * 2

    assert Stage().run(21) == 42
