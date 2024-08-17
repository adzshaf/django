import decimal
import json

from django.db import NotSupportedError
from django.db.models import JSONField
from django.db.models.functions.json import JSONSet
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from ..models import UserPreferences


@skipUnlessDBFeature("supports_json_field")
class JSONSetTests(TestCase):
    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", theme="light"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings, {"theme": "light", "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_multiple_keys(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "font": "Arial", "notifications": True}
        )
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings", theme="light", font="Comic Sans", notifications=False
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"theme": "light", "font": "Comic Sans", "notifications": False},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_in_nested_json_object(self):
        user_preferences = UserPreferences.objects.create(
            settings={"font": {"size": 20, "name": "Arial"}, "theme": "dark"}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", font__size=10))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"font": {"size": 10, "name": "Arial"}, "theme": "dark"},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_key_with_dot_character(self):
        """
        Most databases use a dot-notation for the JSON path.
        Ensure that using a key that contains a dot is escaped properly.
        """
        user_preferences = UserPreferences.objects.create(
            settings={"font.size": 20, "notifications": True}
        )
        UserPreferences.objects.update(
            settings=JSONSet("settings", **{"font.size": 10})
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings, {"font.size": 10, "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_multiple_keys_in_nested_json_object_with_nested_calls(self):
        user_preferences = UserPreferences.objects.create(
            settings={
                "font": {"size": 20, "name": "Arial"},
                "notifications": True,
            }
        )
        UserPreferences.objects.update(
            settings=JSONSet(
                JSONSet("settings", font__size=10), font__name="Comic Sans"
            )
        )

        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"font": {"size": 10, "name": "Comic Sans"}, "notifications": True},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_json_object(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings", theme={"type": "dark", "background_color": "black"}
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {
                "theme": {"type": "dark", "background_color": "black"},
                "notifications": True,
            },
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_multiple_call_set_single_key_with_json_object(self):
        UserPreferences.objects.create(settings={"theme": "dark", "font_size": 20})
        obj = (
            UserPreferences.objects.annotate(
                settings_updated=JSONSet(
                    "settings", theme={"type": "dark", "background_color": "black"}
                )
            )
            .annotate(
                settings_updated_again=JSONSet(
                    "settings_updated",
                    theme={"type": "dark", "background_color": "red"},
                )
            )
            .first()
        )
        self.assertEqual(
            obj.settings_updated,
            {"theme": {"type": "dark", "background_color": "black"}, "font_size": 20},
        )
        self.assertEqual(
            obj.settings_updated_again,
            {"theme": {"type": "dark", "background_color": "red"}, "font_size": 20},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_nested_json(self):
        user_preferences = UserPreferences.objects.create(settings={"theme": "dark"})
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings",
                theme={
                    "type": "dark",
                    "background": {
                        "color": {"gradient-1": "black", "gradient-2": "grey"},
                        "opacity": 0.5,
                    },
                },
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {
                "theme": {
                    "type": "dark",
                    "background": {
                        "color": {"gradient-1": "black", "gradient-2": "grey"},
                        "opacity": 0.5,
                    },
                }
            },
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_list(self):
        user_preferences = UserPreferences.objects.create(
            settings={"rgb": [255, 255, 255], "notifications": True}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", rgb=[0, 0, 0]))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings, {"rgb": [0, 0, 0], "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_list_using_index(self):
        user_preferences = UserPreferences.objects.create(
            settings={"rgb": [255, 255, 255], "notifications": True}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", rgb__1=0))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings, {"rgb": [255, 0, 255], "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_json_null(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", theme=None))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings, {"theme": None, "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_nested_json_null(self):
        user_preferences = UserPreferences.objects.create(
            settings={"font": {"size": 20}, "notifications": True}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", font__size=None))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings, {"font": {"size": None}, "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_using_instance(self):
        user_preferences = UserPreferences.objects.create(
            settings={"font": {"size": 20}, "notifications": True}
        )
        user_preferences.settings = JSONSet("settings", font__size=None)
        user_preferences.save()

        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings, {"font": {"size": None}, "notifications": True}
        )

    def test_set_missing_key_value_returns_error(self):
        with self.assertRaisesMessage(
            TypeError, "JSONSet requires at least one key-value pair to be set"
        ):
            UserPreferences.objects.create(
                settings={"theme": "dark", "notifications": True}
            )
            UserPreferences.objects.update(settings=JSONSet("settings"))

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_insert_new_key(self):
        user_preferences = UserPreferences.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreferences.objects.update(settings=JSONSet("settings", font="Arial"))
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"theme": "dark", "notifications": True, "font": "Arial"},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_using_custom_encoder(self):
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, decimal.Decimal):
                    return str(o)
                return super().default(o)

        user_preferences = UserPreferences.objects.create(
            settings={
                "theme": {"type": "dark", "opacity": decimal.Decimal(100.0)},
                "notifications": True,
            }
        )
        UserPreferences.objects.update(
            settings=JSONSet(
                "settings",
                output_field=JSONField(encoder=CustomJSONEncoder),
                theme__opacity=decimal.Decimal(50.0),
            )
        )
        user_preferences = UserPreferences.objects.get(pk=user_preferences.pk)
        self.assertEqual(
            user_preferences.settings,
            {"theme": {"type": "dark", "opacity": "50"}, "notifications": True},
        )

    @skipIfDBFeature("supports_partial_json_update")
    def test_set_not_supported(self):
        with self.assertRaisesMessage(
            NotSupportedError, "JSONSet() is not supported on this database backend."
        ):
            UserPreferences.objects.create(
                settings={"theme": "dark", "notifications": True}
            )
            UserPreferences.objects.update(settings=JSONSet("settings", theme="light"))
