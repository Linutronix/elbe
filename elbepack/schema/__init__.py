import importlib.resources


def xml_schema_file(name):
    return importlib.resources.files(__name__).joinpath(name).open('r')
