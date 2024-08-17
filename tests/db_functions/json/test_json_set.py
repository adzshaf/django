import decimal
import json

from django.db import NotSupportedError
from django.db.models import JSONField
from django.db.models.functions.json import JSONSet
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from ..models import UserPreference


@skipUnlessDBFeature("supports_json_field")
class JSONSetTests(TestCase):
    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key(self):
        user_preference = UserPreference.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreference.objects.update(settings=JSONSet("settings", theme="light"))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"theme": "light", "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_multiple_keys(self):
        user_preference = UserPreference.objects.create(
            settings={"theme": "dark", "font": "Arial", "notifications": True}
        )
        UserPreference.objects.update(
            settings=JSONSet(
                "settings", theme="light", font="Comic Sans", notifications=False
            )
        )
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings,
            {"theme": "light", "font": "Comic Sans", "notifications": False},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_in_nested_json_object(self):
        user_preference = UserPreference.objects.create(
            settings={"font": {"size": 20, "name": "Arial"}, "theme": "dark"}
        )
        UserPreference.objects.update(settings=JSONSet("settings", font__size=10))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings,
            {"font": {"size": 10, "name": "Arial"}, "theme": "dark"},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_key_with_dot_character(self):
        user_preference = UserPreference.objects.create(
            settings={"font.size": 20, "notifications": True}
        )
        UserPreference.objects.update(settings=JSONSet("settings", **{"font.size": 10}))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"font.size": 10, "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_multiple_keys_in_nested_json_object_with_nested_calls(self):
        user_preference = UserPreference.objects.create(
            settings={
                "font": {"size": 20, "name": "Arial"},
                "notifications": True,
            }
        )
        UserPreference.objects.update(
            settings=JSONSet(
                JSONSet("settings", font__size=10), font__name="Comic Sans"
            )
        )

        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings,
            {"font": {"size": 10, "name": "Comic Sans"}, "notifications": True},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_json_object(self):
        user_preference = UserPreference.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreference.objects.update(
            settings=JSONSet(
                "settings", theme={"type": "dark", "background_color": "black"}
            )
        )
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings,
            {
                "theme": {"type": "dark", "background_color": "black"},
                "notifications": True,
            },
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_multiple_call_set_single_key_with_json_object(self):
        UserPreference.objects.create(settings={"theme": "dark", "font_size": 20})
        obj = (
            UserPreference.objects.annotate(
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
            obj.settings_updated_again,
            {"theme": {"type": "dark", "background_color": "red"}, "font_size": 20},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_nested_json(self):
        user_preference = UserPreference.objects.create(settings={"theme": "dark"})
        UserPreference.objects.update(
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
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings,
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
        user_preference = UserPreference.objects.create(
            settings={"rgb": [255, 255, 255], "notifications": True}
        )
        UserPreference.objects.update(settings=JSONSet("settings", rgb=[0, 0, 0]))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"rgb": [0, 0, 0], "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_list_using_index(self):
        user_preference = UserPreference.objects.create(
            settings={"rgb": [255, 255, 255], "notifications": True}
        )
        UserPreference.objects.update(settings=JSONSet("settings", rgb__1=0))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"rgb": [255, 0, 255], "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_json_null(self):
        user_preference = UserPreference.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreference.objects.update(settings=JSONSet("settings", theme=None))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"theme": None, "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_single_key_with_nested_json_null(self):
        user_preference = UserPreference.objects.create(
            settings={"font": {"size": 20}, "notifications": True}
        )
        UserPreference.objects.update(settings=JSONSet("settings", font__size=None))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"font": {"size": None}, "notifications": True}
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_using_instance(self):
        user_preference = UserPreference.objects.create(
            settings={"font": {"size": 20}, "notifications": True}
        )
        user_preference.settings = JSONSet("settings", font__size=None)
        user_preference.save()

        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"font": {"size": None}, "notifications": True}
        )

    def test_set_missing_key_value_returns_error(self):
        with self.assertRaisesMessage(
            TypeError, "JSONSet requires at least one key-value pair to be set"
        ):
            UserPreference.objects.create(
                settings={"theme": "dark", "notifications": True}
            )
            UserPreference.objects.update(settings=JSONSet("settings"))

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_insert_new_key(self):
        user_preference = UserPreference.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreference.objects.update(settings=JSONSet("settings", font="Arial"))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings,
            {"theme": "dark", "notifications": True, "font": "Arial"},
        )

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_set_using_custom_encoder(self):
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, decimal.Decimal):
                    return str(o)
                return super().default(o)

        user_preference = UserPreference.objects.create(
            settings={
                "theme": {"type": "dark", "opacity": decimal.Decimal(100.0)},
                "notifications": True,
            }
        )
        UserPreference.objects.update(
            settings=JSONSet(
                "settings",
                output_field=JSONField(encoder=CustomJSONEncoder),
                theme__opacity=decimal.Decimal(50.0),
            )
        )
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings,
            {"theme": {"type": "dark", "opacity": "50"}, "notifications": True},
        )

    @skipIfDBFeature("supports_partial_json_update")
    def test_set_not_supported(self):
        with self.assertRaises(NotSupportedError):
            user_preference = UserPreference.objects.create(
                settings={"theme": "dark", "notifications": True}
            )
            UserPreference.objects.update(
                settings=JSONSet("settings", theme="light"))