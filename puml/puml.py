from typing import Callable, Iterable, Union, Optional, List
import inspect
import jinja2


class Pumlgenerator:

    def __init__(self, objs: List[object] = list()):
        self.objs = objs
        self.clean_name = Puml.clean_namespaces
        self.__absorb_obj()

    def __absorb_obj(self):
        self.clean_dict = {self.clean_name(obj, "name"): Puml(obj) for obj in self.objs}

    def add_obj(self, obj: object):
        self.objs.append(obj)
        self.__absorb_obj()
        return self

    def add_objs(self, objs: List[object]):
        for obj in objs:
            self.add_obj(obj)
        return self

    def draw_pumls(self) -> str:
        master_parents = {}
        master_expanded = {}
        for _, puml in self.clean_dict.items():
            master_parents.update(puml.parent_dict)
            master_expanded.update(puml.expanded_parents)

        master = Puml(object)
        master.parent_dict = master_parents
        master.expanded_parents = master_expanded
        return master.draw_puml()


class Puml:

    def __init__(self, obj: object = None):
        """

        :param obj: Object that a class diagram should be generated
        :type obj: class; uninitiated
        """

        self.inheritance_mapping = {}
        self.method_mapping = {}
        self.__childs_of_obj = []

        self.parent_dict = {}
        self.expanded_parents = {}

        # Little Helper Function
        self.flatten = lambda l: [item for sublist in l for item in sublist]

        # Chain of Initiaton
        if obj is not object:
            self.gen_parent_dict(obj)
        self.expand_parents()
        self.get_all_methods()

        # Jinja Templates
        template_loader = jinja2.FileSystemLoader(searchpath="../templates")
        template_env = jinja2.Environment(loader=template_loader)

        self.class_template = template_env.get_template("puml_class.j2")
        self.relations_template = template_env.get_template("puml_relation.j2")
        self.puml_tmpl = template_env.get_template("puml.j2")

    def gen_parent_dict(self, obj: object) -> "Puml":
        """
        Genearate a dictionary of the relationship  child: parent
        :param obj: Obj for which the dictionary should be build
        :type obj: class; unitiated
        :return:  self; Puml-Object
        :rtype: class
        """
        if obj == object:
            return self
        parents = obj.__bases__
        self.parent_dict[obj] = [*parents]

        if parents[0] == object:
            return self

        else:
            for parent in parents:
                self.gen_parent_dict(parent)

    def expand_parents(self) -> "Puml":
        """
        Builds an extended dictinary of the child -> parent dict  to an child -> parent, parents parent dict
        :return: Dictionary of child->ancestros
        :rtype: dict
        """

        for obj in self.parent_dict.keys():
            self.expanded_parents[obj] = self._expand_parents(obj)
        return self

    def _expand_parents(self, obj) -> list:
        parents = self.parent_dict[obj]
        ancestores = []
        iteration = []
        while parents:
            ancestores.extend(parents)
            for parent in parents:
                found_ancestores = self.parent_dict.get(parent)
                if found_ancestores:
                    iteration.extend(found_ancestores)

            parents, iteration = iteration, []
        return ancestores

    def get_all_methods(self) -> "Puml":
        for obj in self.parent_dict.keys():
            iterator = [obj] + self.expanded_parents[obj]
            self.method_mapping[obj] = self.flatten([self.get_methods(p) for p in iterator])
        return self

    @staticmethod
    def get_methods(obj: object) -> list:
        """
        Generates  a List of Methods for the respectife  Object
        :param obj: Object from which the methods should be extraced
        :type obj: class; uninitiated
        :return: List of Methods
        :rtype: list
        """

        members = inspect.getmembers(obj)
        mapping_proxy = None

        for member in members:
            if len(member) == 2:
                if member[0] == "__dict__":
                    print(member)
                    mapping_proxy = member[1].items()
                    break
        if mapping_proxy:
            ret = [func.strip() for func, type_ in mapping_proxy if inspect.isfunction(type_)]
        else:
            ret = []

        return ret

    def clean_name(self, obj: object) -> str:
        """
        Get a Clean name of the class representation
        :param obj: Object which string representation should be stripped
        :type obj: class; uninitiated
        :return: A Clean Name of the object with only the class Name
        :rtype: str

        Example:
        =========
        str(object) -> '<class object>'
        clean_name(obj) ->  'object'
        """
        return self.clean_namespaces(obj, "name")

    @staticmethod
    def clean_namespaces(obj: object, return_type: str) -> str:
        obj_repr = str(obj)
        clean_repr = (obj_repr.replace("class", "")
                      .replace("<", "")
                      .replace(">", "")
                      .replace("'", "")
                      )
        *obj_namespace, obj_name = clean_repr.split(".")

        if return_type == "name":
            return obj_name

        elif return_type == "namespace":
            return ".".join(obj_namespace)

        elif return_type == "namespace_list":
            return obj_namespace

        elif return_type == "repr":
            return clean_repr

        else:
            raise KeyError(f"""Returntype {return_type} is unkown 
                                please use either name, namespace or repr as input string""")

    @staticmethod
    def save_flatten(obj: list) -> list:
        if obj:
            return [item for sublist in obj if sublist for item in sublist]
        else:
            return []

    def clean_list_name(self, obj_list: list, return_type: str = "repr") -> list:
        return [self.clean_namespaces(obj, return_type) for obj in obj_list]

    def draw_class(self, obj: object) -> str:

        own_methods = self.get_methods(obj)
        parent_methods = self.save_flatten([self.get_methods(parent) for parent in self.expanded_parents.get(obj)])
        own_methods = set(own_methods) - set(parent_methods)

        own_attributes = set(dir(obj)) - own_methods - set(parent_methods)
        parent_attrs = self.save_flatten([dir(parent) for parent in self.expanded_parents.get(obj)])
        inherited_methods = set(parent_methods) - own_methods
        inherited_attributes = set(dir(parent_attrs)) - own_attributes - set(dir(list))

        own_public = [method for method in own_methods if not method.startswith("_")]
        own_private = [method for method in own_methods
                        if not method.startswith("__")
                        and method.startswith("_")]
        own_secret = [method for method in own_methods 
                      if method.startswith("__")
                      and not method.endswith("__")]
        own_dunder = [method for method in own_methods
                      if method.startswith("__")
                      and  method.endswith("__")]

        inherited_public = [method for method in inherited_methods if not method.startswith("_")]

        inherited_private = [method for method in inherited_methods
                        if not method.startswith("__")
                        and method.startswith("_")]
        inheried_secret = [method for method in inherited_methods
                           if method.startswith("__")
                           and not method.endswith("__")]
        inheried_dunder = [method for method in inherited_methods
                           if method.startswith("__")
                           and method.endswith("__")]

        own_methods = {"own_public": own_public,
                       "own_private": own_private,
                       "own_secret": own_secret,
                       "own_dunder": own_dunder,
                       "own_attrs": [att for att in own_attributes if not att.endswith("__")]
                      }

        inherited_methods = {"inherited_public": inherited_public,
                             "inherited_private": inherited_private,
                             "inherited_secret": inheried_secret,
                             "inherited_dunder": inheried_dunder,
                             "inherited_attrs": [att for att in inherited_attributes if not att.endswith("__")]
                             }

        return self.class_template.render( **inherited_methods, **own_methods,
                                          class_name=self.clean_namespaces(obj, "repr"))

    def draw_puml(self) -> str:


        children = [self.clean_namespaces(obj, "repr") for obj in self.parent_dict.keys()]
        parents = {self.clean_namespaces(child, "repr"): self.clean_list_name(parent)
                   for child, parent in self.parent_dict.items()
                   }
        namespaces = set([self.clean_namespaces(obj, "namespace") for obj in children])

        puml_classes = '\n'.join([self.draw_class(obj) for obj in self.parent_dict.keys()])
        relations = self.relations_template.render(children=children,
                                                   parents=parents)
        ns = ""
        for namespace in namespaces:
            if namespace:
                hierachie = namespace.split(".")
                for name in hierachie:
                   ns += "namespace " + str(name) +"{  \n"
                ns += "} \n" * len(hierachie)

        puml_body = ns + relations + puml_classes

        puml = self.puml_tmpl.render(body=puml_body)
        return puml

    def generate_puml(self, filepath=None) -> None:

        puml_content = self.draw_puml()
        print(f"Gonna Write to {filepath}")
        with open(filepath, "w") as file:
            file.write(puml_content)

