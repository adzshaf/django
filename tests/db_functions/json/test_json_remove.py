from django.db.models.functions.json import JSONRemove
from django.test import TestCase
from ..models import UserPreference


class JSONRemoveTests(TestCase):
    def test_single_remove(self):
        UserPreference.objects.create(settings={"theme": "dark", "font": "Arial"})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONRemove("settings", "theme")
        ).first()
        self.assertEqual(obj.settings_updated, {"font": "Arial"})

    def test_single_remove_to_empty_properties(self):
        UserPreference.objects.create(settings={"theme": "dark"})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONRemove("settings", "theme")
        ).first()
        self.assertEqual(obj.settings_updated, {})

    def test_nested_remove(self):
        UserPreference.objects.create(settings={"font": {"size": 20, "color": "red"}})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONRemove("settings", "font__color")
        ).first()
        self.assertEqual(obj.settings_updated, {"font": {"size": 20}})

    def test_using_tuple_params(self):
        UserPreference.objects.create(settings={"theme": "dark", "font": "Arial"})
        obj = UserPreference.objects.annotate(
            settings_updated=JSONRemove("settings", *("theme",))
        ).first()
        self.assertEqual(obj.settings_updated, {"font": "Arial"})

    def test_multiple_remove(self):
        UserPreference.objects.create(
            settings={"font": {"size": 20, "color": "red"}, "theme": "dark"}
        )
        obj = UserPreference.objects.annotate(
            settings_updated=JSONRemove("settings", "font__color", "theme")
        ).first()
        self.assertEqual(obj.settings_updated, {"font": {"size": 20}})

    def test_nested_multiple_remove(self):
        UserPreference.objects.create(
            settings={"font": {"size": 20, "color": "red"}, "theme": "dark"}
        )
        obj = UserPreference.objects.annotate(
            settings_updated=JSONRemove(JSONRemove("settings", "font__color"), "theme")
        ).first()
        self.assertEqual(obj.settings_updated, {"font": {"size": 20}})
