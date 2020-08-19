from pytest import fixture


@fixture
def app():
    from sof_wrapper.app import create_app
    return create_app(testing=True)
