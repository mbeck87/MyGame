"""JSON Validierung für Settings und Persistenz-Daten.

Bietet Schema-Validierung ohne externe Dependencies.
Verwendet einfache Typprüfungen und Wertbereiche.
"""
import json
from typing import Any, Callable, Optional


# =============================================================================
# Schema Definitionen
# =============================================================================

# Schema für settings.json
SETTINGS_SCHEMA = {
    'type': 'object',
    'properties': {
        'sfx_volume': {
            'type': 'number',
            'min': 0.0,
            'max': 1.0,
            'default': 0.5
        },
        'resolution': {
            'type': 'string',
            'enum': ['1280x720', '1280x800', '1600x900', '1920x1080', '2560x1440'],
            'default': '1280x800'
        },
        # Zusätzliche Properties werden ignoriert
    },
    'required': [],  # Alle Properties sind optional (Defaults werden verwendet)
    'additional_properties': False  # Unbekannte Properties sind nicht erlaubt
}

# Schema für scores.json
SCORES_SCHEMA = {
    'type': 'object',
    'properties': {
        'scores': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'minLength': 1, 'maxLength': 18},
                    'money': {'type': 'integer', 'minimum': 0}
                },
                'required': ['name', 'money']
            },
            'maxItems': 20
        },
        'last_name': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 18
        }
    },
    'required': []
}


# =============================================================================
# Validierungsfunktionen
# =============================================================================

class ValidationError(Exception):
    """Wird ausgelöst wenn die Validierung fehlschlägt."""
    
    def __init__(self, message: str, path: str = "", value: Any = None):
        self.message = message
        self.path = path
        self.value = value
        super().__init__(f"{path}: {message} (value: {value!r})")


def _validate_type(value: Any, expected_type: str, path: str) -> None:
    """Validiert den Typ eines Wertes."""
    type_map = {
        'string': str,
        'number': (int, float),
        'integer': int,
        'boolean': bool,
        'array': list,
        'object': dict,
        'null': type(None)
    }
    
    expected = type_map.get(expected_type)
    if expected is None:
        raise ValidationError(f"Unbekannter Typ: {expected_type}", path)
    
    if not isinstance(value, expected):
        raise ValidationError(
            f"Erwarteter Typ: {expected_type}, erhalten: {type(value).__name__}",
            path
        )


def _validate_enum(value: Any, enum_values: list, path: str) -> None:
    """Validiert ob ein Wert in einer Aufzählung enthalten ist."""
    if value not in enum_values:
        raise ValidationError(
            f"Wert muss einer von {enum_values} sein",
            path
        )


def _validate_string_constraints(value: Any, schema: dict, path: str) -> None:
    """Validiert String-spezifische Constraints."""
    if 'minLength' in schema and len(value) < schema['minLength']:
        raise ValidationError(
            f"String muss mindestens {schema['minLength']} Zeichen lang sein",
            path
        )
    if 'maxLength' in schema and len(value) > schema['maxLength']:
        raise ValidationError(
            f"String darf maximal {schema['maxLength']} Zeichen lang sein",
            path
        )


def _validate_number_constraints(value: Any, schema: dict, path: str) -> None:
    """Validiert Zahlen-spezifische Constraints."""
    if 'minimum' in schema and value < schema['minimum']:
        raise ValidationError(
            f"Wert muss >= {schema['minimum']} sein",
            path
        )
    if 'maximum' in schema and value > schema['maximum']:
        raise ValidationError(
            f"Wert muss <= {schema['maximum']} sein",
            path
        )
    if 'min' in schema and value < schema['min']:
        raise ValidationError(
            f"Wert muss >= {schema['min']} sein",
            path
        )
    if 'max' in schema and value > schema['max']:
        raise ValidationError(
            f"Wert muss <= {schema['max']} sein",
            path
        )


def _validate_array_constraints(value: Any, schema: dict, path: str) -> None:
    """Validiert Array-spezifische Constraints."""
    if 'maxItems' in schema and len(value) > schema['maxItems']:
        raise ValidationError(
            f"Array darf maximal {schema['maxItems']} Elemente enthalten",
            path
        )
    if 'minItems' in schema and len(value) < schema['minItems']:
        raise ValidationError(
            f"Array muss mindestens {schema['minItems']} Elemente enthalten",
            path
        )
    
    # Validiert jedes Item im Array
    if 'items' in schema:
        for i, item in enumerate(value):
            _validate_object(item, schema['items'], f"{path}[{i}]")


def _validate_object(value: Any, schema: dict, path: str = "root") -> None:
    """Rekursiv: Validiert ein Objekt gegen ein Schema."""
    # Typ prüfen
    if 'type' in schema:
        if schema['type'] == 'array':
            _validate_type(value, 'array', path)
            _validate_array_constraints(value, schema, path)
            return
        _validate_type(value, schema['type'], path)
    
    # String Constraints
    if schema.get('type') == 'string':
        _validate_string_constraints(value, schema, path)
    
    # Number Constraints
    if schema.get('type') in ('number', 'integer'):
        _validate_number_constraints(value, schema, path)
    
    # Enum prüfen
    if 'enum' in schema:
        _validate_enum(value, schema['enum'], path)
    
    # Für Objekte: Properties validieren
    if schema.get('type') == 'object' or isinstance(value, dict):
        # Required Properties prüfen
        for prop in schema.get('required', []):
            if prop not in value:
                raise ValidationError(f"Fehlende Property: {prop}", path)
        
        # Properties validieren
        if 'properties' in schema:
            for prop, prop_schema in schema['properties'].items():
                if prop in value:
                    _validate_object(value[prop], prop_schema, f"{path}.{prop}")
        
        # Additional Properties prüfen
        if schema.get('additional_properties') is False:
            allowed_props = set(schema.get('properties', {}).keys())
            actual_props = set(value.keys())
            extra = actual_props - allowed_props
            if extra:
                raise ValidationError(
                    f"Unbekannte Properties: {extra}",
                    path
                )


def validate(data: Any, schema: dict) -> list:
    """Validiert Daten gegen ein Schema.
    
    Args:
        data: Die zu validierenden Daten
        schema: Das JSON-Schema
        
    Returns:
        Liste von ValidationError-Objekten (leer wenn gültig)
    """
    errors = []
    try:
        _validate_object(data, schema, "root")
    except ValidationError as e:
        errors.append(e)
    return errors


def validate_and_fix(data: Any, schema: dict) -> tuple[Any, list]:
    """Validiert Daten gegen ein Schema und wendet Defaults an.
    
    Args:
        data: Die zu validierenden Daten
        schema: Das JSON-Schema
        
    Returns:
        (korrigierte_daten, liste_der_fehler)
    """
    errors = []
    
    # Typ prüfen
    if 'type' in schema:
        if schema['type'] == 'object' and not isinstance(data, dict):
            data = {}
        elif schema['type'] == 'array' and not isinstance(data, list):
            data = []
    
    if isinstance(data, dict) and schema.get('type') == 'object':
        result = dict(data)
        
        # Defaults für fehlende Required Properties
        for prop in schema.get('required', []):
            if prop not in result and 'default' in schema.get('properties', {}).get(prop, {}):
                result[prop] = schema['properties'][prop]['default']
        
        # Defaults für alle Properties mit Defaults
        if 'properties' in schema:
            for prop, prop_schema in schema['properties'].items():
                if prop not in result and 'default' in prop_schema:
                    result[prop] = prop_schema['default']
        
        # Unknown Properties entfernen wenn additional_properties=False
        if schema.get('additional_properties') is False:
            allowed = set(schema.get('properties', {}).keys())
            to_remove = set(result.keys()) - allowed
            for prop in to_remove:
                errors.append(ValidationError(
                    f"Unbekannte Property entfernt: {prop}",
                    f"root.{prop}"
                ))
                del result[prop]
        
        # Properties rekursiv validieren
        if 'properties' in schema:
            for prop, prop_schema in schema['properties'].items():
                if prop in result:
                    sub_errors = []
                    try:
                        _validate_object(result[prop], prop_schema, f"root.{prop}")
                    except ValidationError as e:
                        sub_errors.append(e)
                    errors.extend(sub_errors)
        
        data = result
    
    return data, errors


def validate_settings(settings: dict) -> tuple[dict, list]:
    """Validiert Settings-Daten gegen das Settings-Schema.
    
    Args:
        settings: Die Settings-Daten
        
    Returns:
        (korrigierte_settings, liste_der_fehler)
    """
    return validate_and_fix(settings, SETTINGS_SCHEMA)


def validate_scores(data: dict) -> tuple[dict, list]:
    """Validiert Scores-Daten gegen das Scores-Schema.
    
    Args:
        data: Die Scores-Daten
        
    Returns:
        (korrigierte_daten, liste_der_fehler)
    """
    return validate_and_fix(data, SCORES_SCHEMA)
