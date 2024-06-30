from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Func, Value
from django.db.models.fields.json import JSONField, compile_json_path
from django.db.models.functions import Cast


class JSONSet(Func):
    output_field = JSONField()

    def __init__(self, field_name, **fields):
        if not fields:
            raise TypeError("JSONSet requires fields parameter")
        self.fields = fields
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

        for key, value in self.fields.items():
            key_paths = key.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)
            new_source_expression.extend(
                (
                    Value(key_paths_join),
                    Cast(
                        Value(value, output_field=self.output_field),
                        output_field=self.output_field,
                    ),
                )
            )

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
