from django.db import NotSupportedError
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Func, Value
from django.db.models.fields.json import compile_json_path
from django.db.models.functions import Cast


class JSONSet(Func):
    def __init__(self, expression, output_field=None, **fields):
        if not fields:
            raise TypeError("JSONSet requires at least one key-value pair to be set.")
        self.fields = fields
        super().__init__(expression, output_field=output_field)

    def _get_repr_options(self):
        return {**super().get_repr_options(), **self.fields}

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        c = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        # Resolve expressions in the JSON update values.
        c.fields = {
            key: (
                value.resolve_expression(query, allow_joins, reuse, summarize, for_save)
                if hasattr(value, "resolve_expression")
                else value
            )
            for key, value in self.fields.items()
        }

        if for_save == "create":
            # In the "create" case of an update_or_create(), we set the first
            # source expression to an empty dictionary, since there is no
            # existing JSON column to update.
            source_expressions = c.get_source_expressions()
            source_expressions[0] = Value({}, output_field=c.output_field)
            c.set_source_expressions(source_expressions)
        return c

    def as_sql(
        self,
        compiler,
        connection,
        function=None,
        template=None,
        arg_joiner=None,
        **extra_context,
    ):
        if not connection.features.supports_partial_json_update:
            raise NotSupportedError(
                "JSONSet() is not supported on this database backend."
            )
        copy = self.copy()
        new_source_expressions = copy.get_source_expressions()

        for key, value in self.fields.items():
            key_paths = key.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)
            new_source_expressions.append(Value(key_paths_join))

            if not hasattr(value, "resolve_expression"):
                # Use Value to serialize the data to string,
                # then use Cast to ensure the string is treated as JSON.
                value = Cast(
                    Value(value, output_field=self.output_field),
                    output_field=self.output_field,
                )

            new_source_expressions.append(value)

        copy.set_source_expressions(new_source_expressions)

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

        # JSONB_SET does not support arbitrary number of arguments,
        # so convert multiple updates into recursive calls.
        if rest:
            copy.fields = {key: value}
            return JSONSet(copy, **dict(rest)).as_postgresql(
                compiler, connection, **extra_context
            )

        new_source_expressions = copy.get_source_expressions()

        key_paths = key.split(LOOKUP_SEP)
        key_paths_join = ",".join(key_paths)
        new_source_expressions.append(Value(f"{{{key_paths_join}}}"))

        if not hasattr(value, "resolve_expression"):
            # We do not need Cast() because psycopg will automatically adapt the
            # value to JSONB.
            value = Value(value, output_field=self.output_field)
        else:
            # Database expressions may return any type. We cannot use Cast() here
            # because ::jsonb only works with JSON-formatted strings, not with
            # other types like integers. The TO_JSONB function is available for
            # this purpose, i.e. to convert any SQL type to JSONB.

            class ToJSONB(Func):
                function = "TO_JSONB"

            value = ToJSONB(value, output_field=self.output_field)

        new_source_expressions.append(value)
        copy.set_source_expressions(new_source_expressions)
        return super(JSONSet, copy).as_sql(
            compiler, connection, function="JSONB_SET", **extra_context
        )

    def as_oracle(self, compiler, connection, **extra_context):
        if not connection.features.supports_partial_json_update:
            raise NotSupportedError(
                "JSONSet() is not supported on this database backend."
            )
        copy = self.copy()

        all_items = list(self.fields.items())
        key, value = all_items[0]
        rest = all_items[1:]

        # JSON_TRANSFORM does not support arbitrary number of arguments,
        # so convert multiple updates into recursive calls.
        if rest:
            copy.fields = {key: value}
            return JSONSet(copy, **dict(rest)).as_oracle(
                compiler, connection, **extra_context
            )

        new_source_expressions = copy.get_source_expressions()

        key_paths = key.split(LOOKUP_SEP)
        key_paths_join = compile_json_path(key_paths)

        if not hasattr(value, "resolve_expression"):
            # We do not need Cast() because Oracle has the FORMAT JSON clause
            # in JSON_TRANSFORM that will automatically treat the value as JSON.
            value = Value(value, output_field=self.output_field)

            class ArgJoiner:
                def join(self, args):
                    return f"{args[0]}, SET '{key_paths_join}' = {args[-1]} FORMAT JSON"

        else:

            class ArgJoiner:
                def join(self, args):
                    return f"{args[0]}, SET '{key_paths_join}' = {args[-1]}"

        new_source_expressions.append(value)
        copy.set_source_expressions(new_source_expressions)

        return super(JSONSet, copy).as_sql(
            compiler,
            connection,
            function="JSON_TRANSFORM",
            arg_joiner=ArgJoiner(),
            **extra_context,
        )


class JSONRemove(Func):
    def __init__(self, expression, *paths):
        if not paths:
            raise TypeError("JSONRemove requires at least one path to remove")
        self.paths = paths
        super().__init__(expression)

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        c = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)

        if for_save == "create":
            # In the "create" case of an update_or_create(), we set the first
            # source expression to an empty dictionary, since there is no
            # existing JSON column to update.
            source_expressions = c.get_source_expressions()
            source_expressions[0] = Value({}, output_field=c.output_field)
            c.set_source_expressions(source_expressions)
        return c

    def as_sql(
        self,
        compiler,
        connection,
        function=None,
        template=None,
        arg_joiner=None,
        **extra_context,
    ):
        if not connection.features.supports_partial_json_update:
            raise NotSupportedError(
                "JSONRemove() is not supported on this database backend."
            )

        copy = self.copy()
        new_source_expressions = copy.get_source_expressions()

        for path in self.paths:
            key_paths = path.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)
            new_source_expressions.append(Value(key_paths_join))

        copy.set_source_expressions(new_source_expressions)

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

        new_source_expressions = copy.get_source_expressions()
        key_paths = path.split(LOOKUP_SEP)
        key_paths_join = ",".join(key_paths)
        new_source_expressions.append(Value(f"{{{key_paths_join}}}"))
        copy.set_source_expressions(new_source_expressions)

        return super(JSONRemove, copy).as_sql(
            compiler,
            connection,
            template="%(expressions)s",
            arg_joiner="#- ",
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        if not connection.features.supports_partial_json_update:
            raise NotSupportedError(
                "JSONRemove() is not supported on this database backend."
            )

        copy = self.copy()

        all_items = self.paths
        path, *rest = all_items

        if rest:
            copy.paths = (path,)
            return JSONRemove(copy, *rest).as_oracle(
                compiler, connection, **extra_context
            )

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