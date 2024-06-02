import json

from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Func, Value
from django.db.models.fields.json import JSONField, compile_json_path
from django.db.models.functions import JSONObject


def wrap_values(data):
    """
    Recursively transform all values in the dictionary to be wrapped in Value().
    If a value is a dictionary, recursively apply the transformation to its keys and values.
    """
    wrapped = {}
    for key, value in data.items():
        if isinstance(value, dict):
            wrapped[key] = JSONObject(**wrap_values(value))
        else:
            wrapped[key] = Value(value)

    return wrapped


class JSONSet(Func):
    output_field = JSONField()

    def __init__(self, field_name, **fields):
        """
        expressions = [field_name]
        self.field_name = field_name
        self.fields = fields

        # fields = {"font__size": 10, ....}
        for key, value in fields.items():
            #key_paths = key.split(LOOKUP_SEP)
            #key_paths_join = compile_json_path(key_paths)
            expressions.extend((Value(key), Value(value)))

        print(expressions)

        # super().__init__(*expressions, **fields)
        super().__init__(*expressions)
        """
        self.fields = fields
        super().__init__(field_name)

    """
    def as_sqlite(self, compiler, connection, **extra_context):
        copy = self.copy()
        new_source_expression = []
        for index, expression in enumerate(copy.get_source_expressions()):
            if not isinstance(expression, Value):
                new_source_expression.append(expression)
            else:
                if index % 2 == 1:
                    key_paths = expression.value.split(LOOKUP_SEP)
                    key_paths_join = compile_json_path(key_paths)
                    new_source_expression.append(key_paths_join)
                else:
                    new_source_expression.append(Value(json.dumps(expression.value)))

        copy.set_source_expressions(new_source_expression)

        return copy.as_sql(compiler,
                           connection,
                           **extra_context)
    """

    def as_sql(
        self,
        compiler,
        connection,
        function=None,
        template=None,
        arg_joiner=None,
        **extra_context,
    ):
        copy = self.copy()
        new_source_expression = copy.get_source_expressions()
        for key, value in self.fields.items():
            key_paths = key.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)
            if isinstance(value, dict):
                value_json = wrap_values(value)
                new_source_expression.extend(
                    (Value(key_paths_join), JSONObject(**value_json)))
            else:
                new_source_expression.extend((Value(key_paths_join), Value(value)))

        copy.set_source_expressions(new_source_expression)

        x = super(JSONSet, copy).as_sql(compiler, connection, function="JSON_SET",
                                        **extra_context)
        print(x)
        return x

    def as_postgresql(self, compiler, connection, **extra_context):
        copy = self.copy()

        all_items = list(self.fields.items())
        key, value = all_items[0]
        rest = all_items[1:]

        if rest:
            copy.fields = {key: value}
            return JSONSet(copy, **dict(rest)).as_postgresql(compiler, connection,
                                                             **extra_context)
        else:
            new_source_expression = copy.get_source_expressions()
            key_paths = key.split(LOOKUP_SEP)
            key_paths_join = ",".join(key_paths)
            new_source_expression.extend((Value(f"{{{key_paths_join}}}"),
                                          Value(value, output_field=JSONField())))
            copy.set_source_expressions(new_source_expression)

        """
        JSONSet(JSONSet('settings', font__size=20), font__name='Comic Sans')
        JSONSet(copy, font__name='Comic Sans')
        inner JSONSet('settings', font__size=20)

        super().__init__(inner JSONSet)
        """
        return super(JSONSet, copy).as_sql(compiler,
                                           connection,
                                           function="JSONB_SET",
                                           **extra_context)

    def as_oracle(self, compiler, connection, **extra_context):
        copy = self.copy()

        all_items = list(self.fields.items())
        key, value = all_items[0]
        rest = all_items[1:]

        if rest:
            copy.fields = {key: value}
            return JSONSet(copy, **dict(rest)).as_oracle(compiler, connection,
                                                         **extra_context)
        else:
            new_source_expression = copy.get_source_expressions()
            key_paths = key.split(LOOKUP_SEP)
            key_paths_join = ",".join(key_paths)
            new_source_expression.extend((Value(f"{{{key_paths_join}}}"),
                                          Value(value, output_field=JSONField())))
            copy.set_source_expressions(new_source_expression)

        return super(JSONSet, copy).as_sql(compiler,
                                           connection,
                                           function="JSON_TRANSFORM",
                                           **extra_context)
