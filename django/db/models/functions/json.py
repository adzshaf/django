import json

from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Func, Value
from django.db.models.fields.json import JSONField, compile_json_path
from django.db.models.functions import JSONObject, Cast


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
        if not fields:
            raise TypeError("JSONSet requires fields parameter")
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

            """
            if isinstance(value, dict):
                value_json = wrap_values(value)
                # check whether database support JSON(), explore using Cast
                new_source_expression.extend(
                    (Value(key_paths_join), JSONObject(**value_json))
                )
            """
            # if isinstance(value, dict) or isinstance(value, list):
            # value_json = json.dumps(value)
            new_source_expression.extend(
                (
                    Value(key_paths_join),
                    Cast(
                        # TODO custom encoder not used here
                        Value(value, output_field=self.output_field),
                        output_field=self.output_field,
                    ),
                )
            )
            # else:
            #     new_source_expression.extend(
            #         (Value(key_paths_join), Value(value, output_field=JSONField()))
            #     )

        copy.set_source_expressions(new_source_expression)

        return super(JSONSet, copy).as_sql(
            compiler,
            connection,
            function="JSON_SET",
            **extra_context,
        )

    def as_postgresql(self, compiler, connection, **extra_context):
        copy = self.copy()

        all_items = list(self.fields.items())
        key, value = all_items[0]
        rest = all_items[1:]

        if rest:
            copy.fields = {key: value}
            return JSONSet(copy, **dict(rest)).as_postgresql(
                compiler, connection, **extra_context
            )
        else:
            new_source_expression = copy.get_source_expressions()
            key_paths = key.split(LOOKUP_SEP)
            key_paths_join = ",".join(key_paths)
            new_source_expression.extend(
                (
                    Value(f"{{{key_paths_join}}}"),
                    Value(value, output_field=self.output_field),
                )
            )
            copy.set_source_expressions(new_source_expression)

        """
        JSONSet(JSONSet('settings', font__size=20), font__name='Comic Sans')
        JSONSet(copy, font__name='Comic Sans')
        inner JSONSet('settings', font__size=20)

        super().__init__(inner JSONSet)
        """
        return super(JSONSet, copy).as_sql(
            compiler, connection, function="JSONB_SET", **extra_context
        )

    def as_oracle(self, compiler, connection, **extra_context):
        copy = self.copy()

        all_items = list(self.fields.items())
        key, value = all_items[0]
        rest = all_items[1:]

        if rest:
            copy.fields = {key: value}
            return JSONSet(copy, **dict(rest)).as_oracle(
                compiler, connection, **extra_context
            )
        else:
            new_source_expression = copy.get_source_expressions()
            key_paths = key.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)
            # if isinstance(value, dict) or isinstance(value, list):
            #     value_json = json.dumps(value)
            #     new_source_expression.extend(
            #         (Cast(Value(value, output_field=JSONField()), output_field=JSONField()),)
            #     )
            new_source_expression.extend(
                (Value(value, output_field=self.output_field),)
            )
            copy.set_source_expressions(new_source_expression)

        class ArgJoiner:
            def join(self, args):
                if len(args) < 2:
                    return ", ".join(args)
                else:
                    return f"{args[0]}, SET '{key_paths_join}' = {args[-1]} FORMAT JSON"

        return super(JSONSet, copy).as_sql(
            compiler,
            connection,
            function="JSON_TRANSFORM",
            arg_joiner=ArgJoiner(),
            **extra_context,
        )


class JSONRemove(Func):
    """
    def __init__(self, field_name, *paths):
        expressions = [field_name]

        for path in paths:
            key_paths = path.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)
            expressions.append(Value(key_paths_join))

        super().__init__(*expressions)
    """

    def __init__(self, field_name, *paths):
        if not paths:
            raise TypeError("JSONRemove requires paths parameter")
        self.paths = paths
        super().__init__(field_name)

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

        for path in self.paths:
            key_paths = path.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)
            new_source_expression.append(Value(key_paths_join))

        copy.set_source_expressions(new_source_expression)

        return super(JSONRemove, copy).as_sql(
            compiler,
            connection,
            function="JSON_REMOVE",
            **extra_context,
        )

    def as_postgresql(self, compiler, connection, **extra_context):
        copy = self.copy()
        path, *rest = self.paths

        if rest:
            copy.paths = (path,)
            return JSONRemove(copy, *rest).as_postgresql(
                compiler, connection, **extra_context
            )
        else:
            new_source_expression = copy.get_source_expressions()
            key_paths = path.split(LOOKUP_SEP)
            key_paths_join = ",".join(key_paths)
            new_source_expression.append(Value(f"{{{key_paths_join}}}"))
            copy.set_source_expressions(new_source_expression)

        return super(JSONRemove, copy).as_sql(
            compiler,
            connection,
            template="%(expressions)s",
            arg_joiner="#- ",
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        copy = self.copy()

        all_items = self.paths
        path, *rest = all_items

        if rest:
            copy.paths = (path,)
            return JSONRemove(copy, *rest).as_oracle(
                compiler, connection, **extra_context
            )
        else:
            key_paths = path.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)

        class ArgJoiner:
            def join(self, args):
                return f"{args[0]}, REMOVE '{key_paths_join}'"

        return super(JSONRemove, copy).as_sql(
            compiler,
            connection,
            function="JSON_TRANSFORM",
            arg_joiner=ArgJoiner(),
            **extra_context,
        )
