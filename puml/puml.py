import inspect
import jinja2

class Puml():

    def __init__(self,obj, level= None ):

        #self.instance = obj(*args, **kwargs)
        self.inheritance_mapping = {}
        self.method_mapping = {}
        self.__childs_of_obj = []

        self.parent_dict = {}
        self.expanded_parents = {}

        # Little Helper Function
        self.flatten = lambda l: [item for sublist in l for item in sublist]

        # Chain of Initiaton
        self.gen_parent_dict(obj)
        self.expand_parents()
        self.get_all_methods()

        # Jinja Templates
        templateLoader = jinja2.FileSystemLoader(searchpath="./templates")
        templateEnv = jinja2.Environment(loader=templateLoader)

        self.class_template = templateEnv.get_template("puml_class.j2")
        self.relations_template = templateEnv.get_template("puml_relation.j2")
        self.puml_tmpl = templateEnv.get_template("puml.j2")

    def gen_parent_dict(self, obj):
        parents = obj.__bases__
        self.parent_dict[obj] = [*parents]

        if parents[0] == object:
            return self

        else:
            for parent in parents:
                self.gen_parent_dict(parent)

    def expand_parents(self):

        for obj in self.parent_dict.keys():
            self.expanded_parents[obj] = self._expand_parents(obj)

    def _expand_parents(self, obj):
        parents = self.parent_dict[obj]
        ancestores = []
        round = []
        while parents:
            ancestores.extend(parents)
            for parent in parents:
                found_ancestores = self.parent_dict.get(parent)
                if found_ancestores:
                    round.extend(found_ancestores)

            parents, round =round , []
        return ancestores

    def get_all_methods(self):
        for obj in self.parent_dict.keys():
            iterator = [obj] + self.expanded_parents[obj]
            self.method_mapping[obj] = self.flatten([self.get_methods(p) for p in iterator])

    @staticmethod
    def get_methods(obj):
        members = inspect.getmembers(obj)
        mapping_proxy = None

        for member in members:
            if len(member) ==2:
                if member[0] == "__dict__":
                    print(member)
                    mapping_proxy = member[1].items()
                    break
        if mapping_proxy:
            ret =  [func.strip() for func,type_ in mapping_proxy if inspect.isfunction(type_)]
        else:
            ret = []

        return ret

    def clean_name(self,obj):
        return self.clean_namespaces(obj, "name")

    @staticmethod
    def clean_namespaces(obj, return_type):
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
    def save_flatten(obj):
        if obj:
            return [item for sublist in obj if sublist for item in sublist ]
        else :
            return []

    def clean_list_name(self, obj_list, return_type="repr"):
        return [self.clean_namespaces(obj, return_type) for obj in obj_list]

    def draw_class(self, obj):
        own_methods = self.get_methods(obj)
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

        own_methods = {"own_public": own_public,
                       "own_private": own_private,
                       "own_secret": own_secret,
                       "own_dunder": own_dunder
                      }

        parent_methods = self.save_flatten([self.method_mapping.get(parent) for parent in self.expanded_parents.get(obj)])


        inherited_methods = set(own_methods) - set(parent_methods)
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

        inherited_methods = {"inhertied_public": inherited_public,
                             "inhertied_private": inherited_private,
                             "inhertied_secret": inheried_secret,
                             "inhertied_dunder": inheried_dunder
                             }

        return self.class_template.render( **inherited_methods, **own_methods,
                                          class_name=self.clean_namespaces(obj, "repr"))

    def draw_puml(self):


        children = [self.clean_namespaces(obj, "repr") for obj in self.parent_dict.keys()]
        parents = {self.clean_namespaces(child, "repr"): self.clean_list_name(parent)
                   for child, parent in self.parent_dict.items()
                   }
        namespaces = set([self.clean_namespaces(obj, "namespace") for obj in children])

        puml_classes = ''.join([self.draw_class(obj) for obj in self.parent_dict.keys()])
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

    def generate_puml(self, filepath=None):

        puml_content = self.draw_puml()
        print(f"Gonna Write to {filepath}")
        with open(filepath, "w") as file:
            file.write(puml_content)

