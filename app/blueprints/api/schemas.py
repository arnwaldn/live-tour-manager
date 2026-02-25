"""
Marshmallow schemas for API serialization.
Converts SQLAlchemy models to JSON-safe dictionaries.
"""
from marshmallow import Schema, fields, post_dump


# ── Shared helpers ──────────────────────────────────────────

class BaseSchema(Schema):
    """Base schema with common config."""
    class Meta:
        ordered = True


# ── User ────────────────────────────────────────────────────

class UserMinimalSchema(BaseSchema):
    """Minimal user representation (for nested references)."""
    id = fields.Int(dump_only=True)
    first_name = fields.Str()
    last_name = fields.Str()
    full_name = fields.Str(dump_only=True)


class UserSchema(BaseSchema):
    """Full user representation (for /me endpoint)."""
    id = fields.Int(dump_only=True)
    email = fields.Email()
    first_name = fields.Str()
    last_name = fields.Str()
    full_name = fields.Str(dump_only=True)
    phone = fields.Str()
    access_level = fields.Method('get_access_level')
    access_level_label = fields.Str(dump_only=True)
    is_active = fields.Bool()
    email_verified = fields.Bool()
    created_at = fields.DateTime(format='iso')

    def get_access_level(self, obj):
        return obj.access_level.value if obj.access_level else None


# ── Band ────────────────────────────────────────────────────

class BandSchema(BaseSchema):
    """Band representation."""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    genre = fields.Str()
    bio = fields.Str()
    website = fields.Str()
    manager = fields.Nested(UserMinimalSchema, dump_only=True)
    created_at = fields.DateTime(format='iso')


class BandMinimalSchema(BaseSchema):
    """Minimal band reference."""
    id = fields.Int(dump_only=True)
    name = fields.Str()


# ── Venue ───────────────────────────────────────────────────

class VenueSchema(BaseSchema):
    """Venue representation."""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    address = fields.Str()
    city = fields.Str()
    state = fields.Str()
    country = fields.Str()
    postal_code = fields.Str()
    capacity = fields.Int()
    venue_type = fields.Str()
    latitude = fields.Float()
    longitude = fields.Float()
    created_at = fields.DateTime(format='iso')


class VenueMinimalSchema(BaseSchema):
    """Minimal venue reference."""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    city = fields.Str()
    country = fields.Str()


# ── Tour ────────────────────────────────────────────────────

class TourSchema(BaseSchema):
    """Tour representation."""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    description = fields.Str()
    start_date = fields.Date(format='iso')
    end_date = fields.Date(format='iso')
    status = fields.Method('get_status')
    budget = fields.Float()
    currency = fields.Str()
    notes = fields.Str()
    band = fields.Nested(BandMinimalSchema, dump_only=True)
    stops_count = fields.Method('get_stops_count')
    created_at = fields.DateTime(format='iso')

    def get_status(self, obj):
        return obj.status.value if obj.status else None

    def get_stops_count(self, obj):
        return len(obj.stops) if hasattr(obj, 'stops') and obj.stops else 0


class TourMinimalSchema(BaseSchema):
    """Minimal tour reference."""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    status = fields.Method('get_status')

    def get_status(self, obj):
        return obj.status.value if obj.status else None


# ── TourStop ────────────────────────────────────────────────

class TourStopSchema(BaseSchema):
    """Tour stop (date/event) representation."""
    id = fields.Int(dump_only=True)
    date = fields.Date(format='iso')
    status = fields.Method('get_status')
    event_type = fields.Method('get_event_type')

    # Location
    venue = fields.Nested(VenueMinimalSchema, dump_only=True)
    address = fields.Str()
    city = fields.Str()
    country = fields.Str()

    # Schedule
    doors_time = fields.Method('format_time', dump_only=True)
    soundcheck_time = fields.Method('format_time_soundcheck', dump_only=True)
    set_time = fields.Method('format_time_set', dump_only=True)
    load_in_time = fields.Method('format_time_loadin', dump_only=True)
    curfew_time = fields.Method('format_time_curfew', dump_only=True)

    # Financial
    guarantee = fields.Float()
    ticket_price = fields.Float()
    sold_tickets = fields.Int()
    currency = fields.Str()

    # Tour reference
    tour = fields.Nested(TourMinimalSchema, dump_only=True)
    band = fields.Nested(BandMinimalSchema, dump_only=True)

    created_at = fields.DateTime(format='iso')

    def get_status(self, obj):
        return obj.status.value if obj.status else None

    def get_event_type(self, obj):
        return obj.event_type.value if obj.event_type else None

    def format_time(self, obj):
        return obj.doors_time.strftime('%H:%M') if obj.doors_time else None

    def format_time_soundcheck(self, obj):
        return obj.soundcheck_time.strftime('%H:%M') if obj.soundcheck_time else None

    def format_time_set(self, obj):
        return obj.set_time.strftime('%H:%M') if obj.set_time else None

    def format_time_loadin(self, obj):
        return obj.load_in_time.strftime('%H:%M') if obj.load_in_time else None

    def format_time_curfew(self, obj):
        return obj.curfew_time.strftime('%H:%M') if obj.curfew_time else None


class TourStopMinimalSchema(BaseSchema):
    """Minimal stop reference."""
    id = fields.Int(dump_only=True)
    date = fields.Date(format='iso')
    city = fields.Str()
    status = fields.Method('get_status')

    def get_status(self, obj):
        return obj.status.value if obj.status else None


# ── Guestlist ───────────────────────────────────────────────

class GuestlistEntrySchema(BaseSchema):
    """Guestlist entry representation."""
    id = fields.Int(dump_only=True)
    guest_name = fields.Str()
    guest_email = fields.Str()
    guest_phone = fields.Str()
    company = fields.Str()
    entry_type = fields.Method('get_entry_type')
    plus_ones = fields.Int()
    status = fields.Method('get_status')
    requested_by = fields.Nested(UserMinimalSchema, dump_only=True)
    notes = fields.Str()
    checked_in_at = fields.DateTime(format='iso')
    created_at = fields.DateTime(format='iso')

    def get_entry_type(self, obj):
        return obj.entry_type.value if obj.entry_type else None

    def get_status(self, obj):
        return obj.status.value if obj.status else None


# ── Notification ────────────────────────────────────────────

class NotificationSchema(BaseSchema):
    """Notification representation."""
    id = fields.Int(dump_only=True)
    title = fields.Str()
    message = fields.Str()
    type = fields.Method('get_type')
    is_read = fields.Bool()
    link = fields.Str()
    created_at = fields.DateTime(format='iso')

    def get_type(self, obj):
        return obj.type.value if hasattr(obj.type, 'value') else obj.type


# ── Payment ─────────────────────────────────────────────────

class PaymentSchema(BaseSchema):
    """Payment representation."""
    id = fields.Int(dump_only=True)
    amount = fields.Float()
    currency = fields.Str()
    status = fields.Method('get_status')
    payment_type = fields.Method('get_payment_type')
    description = fields.Str()
    tour_stop = fields.Nested(TourStopMinimalSchema, dump_only=True)
    user = fields.Nested(UserMinimalSchema, dump_only=True)
    paid_at = fields.DateTime(format='iso')
    created_at = fields.DateTime(format='iso')

    def get_status(self, obj):
        return obj.status.value if hasattr(obj.status, 'value') else obj.status

    def get_payment_type(self, obj):
        return obj.payment_type.value if hasattr(obj.payment_type, 'value') else obj.payment_type
