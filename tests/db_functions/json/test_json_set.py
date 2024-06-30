from django.db.models.functions.json import JSONSet
from django.test import TestCase

from ..models import UserPreference


class JSONSetTests(TestCase):
    def test_single_set(self):
        UserPreference.objects.create(settings={"theme": "dark"})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet("settings", theme="light")
        ).first()
        self.assertEqual(obj.settings_updated, {"theme": "light"})

    def test_multiple_set(self):
        UserPreference.objects.create(settings={"theme": "dark", "font": "Arial"})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet("settings", theme="light", font="Comic Sans")
        ).first()
        self.assertEqual(obj.settings_updated, {"theme": "light", "font": "Comic Sans"})

    def test_multiple_more_than_two_set(self):
        UserPreference.objects.create(
            settings={"theme": "dark", "font": "Arial", "type": 1}
        )
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet(
                "settings", theme="light", font="Comic Sans", type=2
            )
        ).first()
        self.assertEqual(
            obj.settings_updated, {"theme": "light", "font": "Comic Sans", "type": 2}
        )

    def test_nested_set(self):
        UserPreference.objects.create(settings={"font": {"size": 20}})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet("settings", font__size=10)
        ).first()
        self.assertEqual(obj.settings_updated, {"font": {"size": 10}})

    def test_set_escape_dot(self):
        # escape bro
        UserPreference.objects.create(settings={"font.size": 20})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet("settings", **{"font.size": 10})
        ).first()
        self.assertEqual(obj.settings_updated, {"font.size": 10})

    def test_nested_multiple_set(self):
        UserPreference.objects.create(settings={"font": {"size": 20, "name": "Arial"}})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet(
                JSONSet("settings", font__size=10), font__name="Comic Sans"
            )
        ).first()
        self.assertEqual(
            obj.settings_updated, {"font": {"size": 10, "name": "Comic Sans"}}
        )

    def test_single_set_json(self):
        UserPreference.objects.create(settings={"theme": "dark"})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet(
                "settings", theme={"type": "dark", "background_color": "black"}
            )
        ).first()
        self.assertEqual(
            obj.settings_updated,
            {"theme": {"type": "dark", "background_color": "black"}},
        )

    def test_single_set_json_double_annotate(self):
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

    def test_single_set_nested_json(self):
        UserPreference.objects.create(settings={"theme": "dark"})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet(
                "settings",
                theme={
                    "type": "dark",
                    "background": {
                        "color": {"gradient-1": "black", "gradient-2": "grey"},
                        "opacity": 0.5,
                    },
                },
            )
        ).first()
        self.assertEqual(
            obj.settings_updated,
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

    def test_single_set_list(self):
        UserPreference.objects.create(settings={"rgb": [255, 255, 255]})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet("settings", rgb=[0, 0, 0])
        ).first()
        self.assertEqual(obj.settings_updated, {"rgb": [0, 0, 0]})

    def test_single_set_json_null(self):
        UserPreference.objects.create(settings={"theme": "dark"})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet("settings", theme=None)
        ).first()
        self.assertEqual(obj.settings_updated, {"theme": None})

    def test_single_set_nested_json_null(self):
        UserPreference.objects.create(settings={"font": {"size": 20}})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONSet("settings", font__size=None)
        ).first()
        self.assertEqual(obj.settings_updated, {"font": {"size": None}})
