"""Tests für das JSON-Validierungsmodul."""
import unittest

from game2d.systems.validation import (
    validate,
    validate_and_fix,
    validate_settings,
    validate_scores,
    ValidationError,
    SETTINGS_SCHEMA,
    SCORES_SCHEMA,
)


class TestValidationHelpers(unittest.TestCase):
    """Testet die grundlegenden Validierungsfunktionen."""

    def test_validate_type_string(self):
        """Testet String-Typvalidierung."""
        schema = {'type': 'string'}
        errors = validate("hello", schema)
        self.assertEqual(len(errors), 0)
        
        errors = validate(123, schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("Erwarteter Typ: string", str(errors[0]))

    def test_validate_type_number(self):
        """Testet Number-Typvalidierung."""
        schema = {'type': 'number'}
        errors = validate(123, schema)
        self.assertEqual(len(errors), 0)
        
        errors = validate(123.5, schema)
        self.assertEqual(len(errors), 0)
        
        errors = validate("123", schema)
        self.assertEqual(len(errors), 1)

    def test_validate_type_integer(self):
        """Testet Integer-Typvalidierung."""
        schema = {'type': 'integer'}
        errors = validate(123, schema)
        self.assertEqual(len(errors), 0)
        
        errors = validate(123.5, schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("Erwarteter Typ: integer", str(errors[0]))

    def test_validate_type_object(self):
        """Testet Object-Typvalidierung."""
        schema = {'type': 'object'}
        errors = validate({}, schema)
        self.assertEqual(len(errors), 0)
        
        errors = validate({'key': 'value'}, schema)
        self.assertEqual(len(errors), 0)
        
        errors = validate([], schema)
        self.assertEqual(len(errors), 1)

    def test_validate_type_array(self):
        """Testet Array-Typvalidierung."""
        schema = {'type': 'array'}
        errors = validate([], schema)
        self.assertEqual(len(errors), 0)
        
        errors = validate([1, 2, 3], schema)
        self.assertEqual(len(errors), 0)
        
        errors = validate({}, schema)
        self.assertEqual(len(errors), 1)


class TestStringConstraints(unittest.TestCase):
    """Testet String-spezifische Constraints."""

    def test_min_length(self):
        """Testet minLength-Constraint."""
        schema = {'type': 'string', 'minLength': 3}
        errors = validate("ab", schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("mindestens 3", str(errors[0]))
        
        errors = validate("abc", schema)
        self.assertEqual(len(errors), 0)

    def test_max_length(self):
        """Testet maxLength-Constraint."""
        schema = {'type': 'string', 'maxLength': 3}
        errors = validate("abcd", schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("maximal 3", str(errors[0]))
        
        errors = validate("abc", schema)
        self.assertEqual(len(errors), 0)


class TestNumberConstraints(unittest.TestCase):
    """Testet Zahlen-spezifische Constraints."""

    def test_minimum(self):
        """Testet minimum-Constraint."""
        schema = {'type': 'number', 'minimum': 0}
        errors = validate(-1, schema)
        self.assertEqual(len(errors), 1)
        self.assertIn(">= 0", str(errors[0]))
        
        errors = validate(0, schema)
        self.assertEqual(len(errors), 0)

    def test_maximum(self):
        """Testet maximum-Constraint."""
        schema = {'type': 'number', 'maximum': 100}
        errors = validate(101, schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("<= 100", str(errors[0]))
        
        errors = validate(100, schema)
        self.assertEqual(len(errors), 0)

    def test_min_max(self):
        """Testet min/max-Constraints (alternative Syntax)."""
        schema = {'type': 'number', 'min': 0, 'max': 1.0}
        errors = validate(-0.1, schema)
        self.assertEqual(len(errors), 1)
        
        errors = validate(1.1, schema)
        self.assertEqual(len(errors), 1)
        
        errors = validate(0.5, schema)
        self.assertEqual(len(errors), 0)


class TestEnumValidation(unittest.TestCase):
    """Testet Enum-Validierung."""

    def test_enum_valid(self):
        """Testet gültige Enum-Werte."""
        schema = {'type': 'string', 'enum': ['a', 'b', 'c']}
        errors = validate('a', schema)
        self.assertEqual(len(errors), 0)

    def test_enum_invalid(self):
        """Testet ungültige Enum-Werte."""
        schema = {'type': 'string', 'enum': ['a', 'b', 'c']}
        errors = validate('d', schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("muss einer von", str(errors[0]))


class TestObjectValidation(unittest.TestCase):
    """Testet Objekt-Validierung."""

    def test_required_properties(self):
        """Testet Required-Properties."""
        schema = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'age': {'type': 'integer'}
            },
            'required': ['name']
        }
        errors = validate({}, schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("Fehlende Property: name", str(errors[0]))

    def test_required_properties_present(self):
        """Testet dass Required-Properties vorhanden sind."""
        schema = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'}
            },
            'required': ['name']
        }
        errors = validate({'name': 'test'}, schema)
        self.assertEqual(len(errors), 0)

    def test_additional_properties_false(self):
        """Testet dass zusätzliche Properties verboten sind."""
        schema = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'}
            },
            'additional_properties': False
        }
        errors = validate({'name': 'test', 'extra': 'value'}, schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("Unbekannte Properties", str(errors[0]))

    def test_additional_properties_allowed(self):
        """Testet dass zusätzliche Properties erlaubt sind (Default)."""
        schema = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'}
            }
        }
        errors = validate({'name': 'test', 'extra': 'value'}, schema)
        self.assertEqual(len(errors), 0)


class TestArrayValidation(unittest.TestCase):
    """Testet Array-Validierung."""

    def test_max_items(self):
        """Testet maxItems-Constraint."""
        schema = {'type': 'array', 'maxItems': 3}
        errors = validate([1, 2, 3, 4], schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("maximal 3 Elemente", str(errors[0]))
        
        errors = validate([1, 2, 3], schema)
        self.assertEqual(len(errors), 0)

    def test_min_items(self):
        """Testet minItems-Constraint."""
        schema = {'type': 'array', 'minItems': 2}
        errors = validate([1], schema)
        self.assertEqual(len(errors), 1)
        self.assertIn("mindestens 2", str(errors[0]))
        
        errors = validate([1, 2], schema)
        self.assertEqual(len(errors), 0)

    def test_items_validation(self):
        """Testet Items-Validierung."""
        schema = {
            'type': 'array',
            'items': {'type': 'integer'}
        }
        errors = validate([1, 2, 3], schema)
        self.assertEqual(len(errors), 0)
        
        errors = validate([1, 'a', 3], schema)
        self.assertEqual(len(errors), 1)


class TestValidateAndFix(unittest.TestCase):
    """Testet die validate_and_fix Funktion."""

    def test_apply_defaults(self):
        """Testet dass Defaults angewendet werden."""
        schema = {
            'type': 'object',
            'properties': {
                'volume': {'type': 'number', 'default': 0.5}
            }
        }
        data = {}
        result, errors = validate_and_fix(data, schema)
        self.assertEqual(result['volume'], 0.5)

    def test_remove_unknown_properties(self):
        """Testet dass unbekannte Properties entfernt werden."""
        schema = {
            'type': 'object',
            'properties': {
                'volume': {'type': 'number'}
            },
            'additional_properties': False
        }
        data = {'volume': 0.5, 'unknown': 'test'}
        result, errors = validate_and_fix(data, schema)
        self.assertNotIn('unknown', result)
        self.assertEqual(len(errors), 1)


class TestSettingsValidation(unittest.TestCase):
    """Testet die Settings-Validierung."""

    def test_valid_settings(self):
        """Testet gültige Settings."""
        settings = {
            'sfx_volume': 0.5,
            'resolution': '1280x800'
        }
        validated, errors = validate_settings(settings)
        self.assertEqual(len(errors), 0)
        self.assertEqual(validated['sfx_volume'], 0.5)
        self.assertEqual(validated['resolution'], '1280x800')

    def test_sfx_volume_out_of_range(self):
        """Testet sfx_volume außerhalb des gültigen Bereichs."""
        settings = {'sfx_volume': 1.5}
        validated, errors = validate_settings(settings)
        self.assertEqual(len(errors), 1)

    def test_invalid_resolution(self):
        """Testet ungültige Auflösung."""
        settings = {'resolution': '800x600'}
        validated, errors = validate_settings(settings)
        self.assertEqual(len(errors), 1)

    def test_unknown_property(self):
        """Testet unbekannte Property."""
        settings = {'sfx_volume': 0.5, 'unknown_setting': 'test'}
        validated, errors = validate_settings(settings)
        self.assertNotIn('unknown_setting', validated)

    def test_missing_properties_use_defaults(self):
        """Testet dass fehlende Properties mit Defaults gefüllt werden."""
        settings = {}
        validated, errors = validate_settings(settings)
        self.assertEqual(validated['sfx_volume'], 0.5)
        self.assertEqual(validated['resolution'], '1280x800')


class TestScoresValidation(unittest.TestCase):
    """Testet die Scores-Validierung."""

    def test_valid_scores(self):
        """Testet gültige Scores."""
        data = {
            'scores': [
                {'name': 'Player1', 'money': 1000},
                {'name': 'Player2', 'money': 500}
            ],
            'last_name': 'Player1'
        }
        validated, errors = validate_scores(data)
        self.assertEqual(len(errors), 0)

    def test_score_missing_required_fields(self):
        """Testet Score-Entry ohne Required-Fields."""
        data = {
            'scores': [{'name': 'Player1'}],
            'last_name': 'Player1'
        }
        # Dies sollte einen Fehler verursachen da 'money' fehlt
        validated, errors = validate_scores(data)
        # Der Entry wird nicht validiert sein
        self.assertGreater(len(errors), 0)

    def test_too_many_scores(self):
        """Testet zu viele Score-Entries."""
        scores = [{'name': f'Player{i}', 'money': i * 100} for i in range(25)]
        data = {'scores': scores, 'last_name': 'Test'}
        validated, errors = validate_scores(data)
        self.assertEqual(len(errors), 1)
        self.assertIn("maximal 20", str(errors[0]))

    def test_last_name_too_long(self):
        """Testet zu langer last_name."""
        data = {
            'scores': [],
            'last_name': 'A' * 20
        }
        validated, errors = validate_scores(data)
        self.assertEqual(len(errors), 1)
        self.assertIn("maximal 18", str(errors[0]))


if __name__ == '__main__':
    unittest.main()
