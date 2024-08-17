from django.db import NotSupportedError
from django.db.models.functions.json import JSONRemove
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from ..models import UserPreference


@skipUnlessDBFeature("supports_json_field")
class JSONRemoveTests(TestCase):
    @skipUnlessDBFeature("supports_partial_json_update")
    def test_remove_single_key(self):
        user_preference = UserPreference.objects.create(
            settings={"theme": "dark", "font": "Arial"}
        )
        UserPreference.objects.update(settings=JSONRemove("settings", "theme"))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"font": "Arial"})

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_remove_single_key_to_empty_property(self):
        user_preference = UserPreference.objects.create(settings={"theme": "dark"})
        UserPreference.objects.update(settings=JSONRemove("settings", "theme"))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {})

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_remove_nested_key(self):
        user_preference = UserPreference.objects.create(
            settings={"font": {"size": 20, "color": "red"}}
        )
        UserPreference.objects.update(settings=JSONRemove("settings", "font__color"))
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"font": {"size": 20}})

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_remove_multiple_keys(self):
        user_preference = UserPreference.objects.create(
            settings={"font": {"size": 20, "color": "red"}, "theme": "dark"}
        )
        UserPreference.objects.update(
            settings=JSONRemove("settings", "font__color", "theme")
        )
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"font": {"size": 20}})

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_remove_keys_with_recursive_call(self):
        user_preference = UserPreference.objects.create(
            settings={"font": {"size": 20, "color": "red"}, "theme": "dark"}
        )
        UserPreference.objects.update(
            settings=JSONRemove(JSONRemove("settings", "font__color"), "theme")
        )
        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"font": {"size": 20}})

    @skipUnlessDBFeature("supports_partial_json_update")
    def test_remove_using_instance(self):
        user_preference = UserPreference.objects.create(
            settings={"theme": "dark", "font": "Arial"}
        )
        user_preference.settings = JSONRemove("settings", "theme")
        user_preference.save()

        user_preference = UserPreference.objects.get(pk=user_preference.pk)
        self.assertEqual(user_preference.settings, {"font": "Arial"})

    def test_remove_missing_path_to_be_removed_error(self):
        with self.assertRaisesMessage(
            TypeError, "JSONRemove requires at least one path to remove"
        ):
            UserPreference.objects.create(
                settings={"theme": "dark", "notifications": True}
            )
            UserPreference.objects.update(settings=JSONRemove("settings"))

    @skipIfDBFeature("supports_partial_json_update")
    def test_remove_not_supported(self):
        with self.assertRaisesMessage(
            NotSupportedError, "JSONRemove() is not supported on this database backend."
        ):
            UserPreference.objects.create(settings={"theme": "dark", "font": "Arial"})
            UserPreference.objects.update(settings=JSONRemove("settings", "theme"))
