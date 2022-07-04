from io import StringIO

import ruamel.yaml


class YamlParser:
    def __init__(self):
        self.yaml = ruamel.yaml.YAML()
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.allow_duplicate_keys = True
        self.yaml.explicit_start = False
        self.yaml.preserve_quotes = True

    def object_to_yaml_str(self, obj, options={}):
        string_stream = StringIO()
        self.yaml.dump(obj, string_stream, **options)
        output_str = string_stream.getvalue()
        string_stream.close()

        return output_str

    def yaml_string_to_object(self, string, options={}):
        return self.yaml.load(string, **options)
