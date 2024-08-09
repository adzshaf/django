from django.db.models.functions.json import JSONSet
from django.test import TestCase, skipUnlessDBFeature

from ..models import UserPreference


@skipUnlessDBFeature("supports_json_field")
class JSONSetTests(TestCase):
    def test_set_single_key(self):
        user_preference = UserPreference.objects.create(
            settings={"theme": "dark", "notifications": True}
        )
        UserPreference.objects.update(settings=JSONSet("settings", theme="light"))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"theme": "light", "notifications": True}
        )

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

    def test_set_single_key_in_nested_json_object(self):
        user_preference = UserPreference.objects.create(
            settings={"font": {"size": 20}, "theme": "dark"}
        )
        UserPreference.objects.update(settings=JSONSet("settings", font__size=10))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"font": {"size": 10}, "theme": "dark"}
        )

    def test_set_key_with_dot_character(self):
        user_preference = UserPreference.objects.create(settings={"font.size": 20})
        UserPreference.objects.update(settings=JSONSet("settings", **{"font.size": 10}))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"font.size": 10})

    def test_set_multiple_keys_in_nested_json_object_with_nested_calls(self):
        user_preference = UserPreference.objects.create(
            settings={"font": {"size": 20, "name": "Arial"}}
        )
        UserPreference.objects.update(
            settings=JSONSet(
                JSONSet("settings", font__size=10), font__name="Comic Sans"
            )
        )

        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings, {"font": {"size": 10, "name": "Comic Sans"}}
        )

    def test_set_single_key_with_json_object(self):
        user_preference = UserPreference.objects.create(settings={"theme": "dark"})
        UserPreference.objects.update(
            settings=JSONSet(
                "settings", theme={"type": "dark", "background_color": "black"}
            )
        )
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(
            user_preference.settings,
            {"theme": {"type": "dark", "background_color": "black"}},
        )

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

    def test_set_single_key_with_list(self):
        user_preference = UserPreference.objects.create(
            settings={"rgb": [255, 255, 255]}
        )
        UserPreference.objects.update(settings=JSONSet("settings", rgb=[0, 0, 0]))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"rgb": [0, 0, 0]})

    def test_set_single_key_with_json_null(self):
        user_preference = UserPreference.objects.create(settings={"theme": "dark"})
        UserPreference.objects.update(settings=JSONSet("settings", theme=None))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"theme": None})

    def test_set_single_key_with_nested_json_null(self):
        user_preference = UserPreference.objects.create(settings={"font": {"size": 20}})
        UserPreference.objects.update(settings=JSONSet("settings", font__size=None))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"font": {"size": None}})

    def test_set_using_instance(self):
        user_preference = UserPreference.objects.create(settings={"font": {"size": 20}})
        user_preference.settings = JSONSet("settings", font__size=None)
        user_preference.save()

        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"font": {"size": None}})

    def test_set_missing_key_value_returns_error(self):
        with self.assertRaisesMessage(
            TypeError, "JSONSet requires at least one key-value pair to be set"
        ):
            UserPreference.objects.create(
                settings={"theme": "dark", "notifications": True}
            )
            UserPreference.objects.update(settings=JSONSet("settings"))
