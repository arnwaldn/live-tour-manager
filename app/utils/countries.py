"""
ISO 3166-1 alpha-2 country codes for form dropdowns.
Focused on European touring markets + major international destinations.
"""

COUNTRY_CHOICES = [
    ('', '-- Pays --'),
    ('FR', 'France'),
    ('BE', 'Belgique'),
    ('CH', 'Suisse'),
    ('DE', 'Allemagne'),
    ('NL', 'Pays-Bas'),
    ('LU', 'Luxembourg'),
    ('GB', 'Royaume-Uni'),
    ('ES', 'Espagne'),
    ('IT', 'Italie'),
    ('PT', 'Portugal'),
    ('AT', 'Autriche'),
    ('IE', 'Irlande'),
    ('DK', 'Danemark'),
    ('SE', 'Suede'),
    ('NO', 'Norvege'),
    ('FI', 'Finlande'),
    ('PL', 'Pologne'),
    ('CZ', 'Republique tcheque'),
    ('GR', 'Grece'),
    ('HR', 'Croatie'),
    ('RO', 'Roumanie'),
    ('HU', 'Hongrie'),
    ('US', 'Etats-Unis'),
    ('CA', 'Canada'),
    ('JP', 'Japon'),
    ('AU', 'Australie'),
    ('BR', 'Bresil'),
    ('MA', 'Maroc'),
    ('TN', 'Tunisie'),
    ('SN', 'Senegal'),
]

# Full-name choices for forms that store country names (venues, tours, logistics, documents).
# Value = display name (backward-compatible with existing DB data).
COUNTRY_CHOICES_FULL = [
    ('', '-- Pays --'),
] + [(name, name) for _code, name in COUNTRY_CHOICES if _code]
