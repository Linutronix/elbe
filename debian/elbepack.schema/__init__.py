import pathlib


def xml_schema_file(name):
    return pathlib.Path('/usr/share/xml/elbe-common').joinpath(name).open('r')
