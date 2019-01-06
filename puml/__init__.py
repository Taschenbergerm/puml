
# pylint: disable-msg=W0614,W0401,W0611,W0622

# flake8: noqa


__version__ = 0.0.1

__docformat__ = 'restructuredtext'

__docs__ = """ A small python class that generates a plant-uml file for class relationships of an object and all its parents,
 without parsing any file and without initiating it.  Therefore only methods are shown ( so far) while attributes are left out
 """
 __release__ = 1 
 __license__ = "AGPL-3.0"


__docformat__ = 'restructuredtext'

# Let users know if they're missing any of our hard dependencies
hard_dependencies = ("Jinja2",)


for dependency in hard_dependencies:
    try:
        __import__(dependency)
    except ImportError as e:
        missing_dependencies.append(dependency)

if missing_dependencies:
    raise ImportError(
        "Missing required dependencies {0}".format(missing_dependencies))
del hard_dependencies, dependency, missing_dependencies


from puml.puml import * 