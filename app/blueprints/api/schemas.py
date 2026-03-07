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


class BandMembershipSchema(BaseSchema):
    """Band membership (member info)."""
    id = fields.Int(dump_only=True)
    user = fields.Nested(UserMinimalSchema, dump_only=True)
    instrument = fields.Str()
    role_in_band = fields.Str()
    is_active = fields.Bool()
    joined_at = fields.DateTime(format='iso')


class BandDetailSchema(BandSchema):
    """Band with members and social links (for detail view)."""
    social_links = fields.Dict()
    logo_url = fields.Str()
    members = fields.Method('get_members')

    def get_members(self, obj):
        schema = BandMembershipSchema()
        return schema.dump(obj.memberships, many=True)


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


class VenueContactSchema(BaseSchema):
    """Venue contact person."""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    role = fields.Str()
    email = fields.Str()
    phone = fields.Str()
    is_primary = fields.Bool()
    notes = fields.Str()


class VenueDetailSchema(VenueSchema):
    """Venue with contacts and technical specs (for detail view)."""
    website = fields.Str()
    phone = fields.Str()
    email = fields.Str()
    notes = fields.Str()
    timezone = fields.Str()
    technical_specs = fields.Str()
    stage_dimensions = fields.Str()
    load_in_info = fields.Str()
    parking_info = fields.Str()
    backline_available = fields.Bool()
    backline_details = fields.Str()
    contacts = fields.Nested(VenueContactSchema, many=True, dump_only=True)


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


# ── Logistics ──────────────────────────────────────────────

class LogisticsInfoSchema(BaseSchema):
    """Logistics item representation."""
    id = fields.Int(dump_only=True)
    logistics_type = fields.Method('get_logistics_type')
    provider = fields.Str()
    confirmation_number = fields.Str()
    start_datetime = fields.DateTime(format='iso')
    end_datetime = fields.DateTime(format='iso')
    status = fields.Method('get_status')
    address = fields.Str()
    city = fields.Str()
    country = fields.Str()
    latitude = fields.Float()
    longitude = fields.Float()
    cost = fields.Float()
    currency = fields.Str()
    is_paid = fields.Bool()
    paid_by = fields.Str()
    # Flight specific
    flight_number = fields.Str()
    departure_airport = fields.Str()
    arrival_airport = fields.Str()
    departure_terminal = fields.Str()
    arrival_terminal = fields.Str()
    # Hotel specific
    room_type = fields.Str()
    number_of_rooms = fields.Int()
    breakfast_included = fields.Bool()
    check_in_time = fields.Method('format_checkin')
    check_out_time = fields.Method('format_checkout')
    # Ground transport
    pickup_location = fields.Str()
    dropoff_location = fields.Str()
    vehicle_type = fields.Str()
    driver_name = fields.Str()
    driver_phone = fields.Str()
    # Contact
    contact_name = fields.Str()
    contact_phone = fields.Str()
    contact_email = fields.Str()
    notes = fields.Str()
    created_at = fields.DateTime(format='iso')

    def get_logistics_type(self, obj):
        return obj.logistics_type.value if obj.logistics_type else None

    def get_status(self, obj):
        return obj.status.value if obj.status else None

    def format_checkin(self, obj):
        return obj.check_in_time.strftime('%H:%M') if obj.check_in_time else None

    def format_checkout(self, obj):
        return obj.check_out_time.strftime('%H:%M') if obj.check_out_time else None


# ── Advancing ─────────────────────────────────────────────

class AdvancingChecklistItemSchema(BaseSchema):
    """Advancing checklist item representation."""
    id = fields.Int(dump_only=True)
    tour_stop_id = fields.Int(dump_only=True)
    category = fields.Method('get_category')
    label = fields.Str()
    is_completed = fields.Bool()
    completed_by_id = fields.Int()
    completed_at = fields.DateTime(format='iso')
    notes = fields.Str()
    due_date = fields.Date(format='iso')
    sort_order = fields.Int()

    def get_category(self, obj):
        return obj.category.value if obj.category else None


class RiderRequirementSchema(BaseSchema):
    """Rider technical requirement representation."""
    id = fields.Int(dump_only=True)
    tour_stop_id = fields.Int(dump_only=True)
    category = fields.Method('get_category')
    requirement = fields.Str()
    quantity = fields.Int()
    is_mandatory = fields.Bool()
    is_confirmed = fields.Bool()
    venue_response = fields.Str()
    notes = fields.Str()
    sort_order = fields.Int()

    def get_category(self, obj):
        return obj.category.value if obj.category else None


class AdvancingContactSchema(BaseSchema):
    """Advancing contact representation."""
    id = fields.Int(dump_only=True)
    tour_stop_id = fields.Int(dump_only=True)
    name = fields.Str()
    role = fields.Str()
    email = fields.Str()
    phone = fields.Str()
    is_primary = fields.Bool()
    notes = fields.Str()


# ── Lineup ─────────────────────────────────────────────────

class LineupSlotSchema(BaseSchema):
    """Lineup slot representation."""
    id = fields.Int(dump_only=True)
    tour_stop_id = fields.Int(dump_only=True)
    performer_name = fields.Str()
    performer_type = fields.Method('get_performer_type')
    start_time = fields.Method('format_start_time')
    end_time = fields.Method('format_end_time')
    set_length_minutes = fields.Int()
    order = fields.Int()
    notes = fields.Str()
    is_confirmed = fields.Bool()

    def get_performer_type(self, obj):
        return obj.performer_type.value if obj.performer_type else None

    def format_start_time(self, obj):
        return obj.start_time.strftime('%H:%M') if obj.start_time else None

    def format_end_time(self, obj):
        return obj.end_time.strftime('%H:%M') if obj.end_time else None


# ── Crew ───────────────────────────────────────────────────

class CrewAssignmentSchema(BaseSchema):
    """Crew assignment representation."""
    id = fields.Int(dump_only=True)
    slot_id = fields.Int(dump_only=True)
    person_name = fields.Str(dump_only=True)
    person_email = fields.Str(dump_only=True)
    is_external = fields.Bool(dump_only=True)
    status = fields.Method('get_status')
    call_time = fields.Method('format_call_time')
    notes = fields.Str()
    assigned_at = fields.DateTime(format='iso')
    confirmed_at = fields.DateTime(format='iso')

    def get_status(self, obj):
        return obj.status.value if obj.status else None

    def format_call_time(self, obj):
        return obj.call_time.strftime('%H:%M') if obj.call_time else None


class CrewScheduleSlotSchema(BaseSchema):
    """Crew schedule slot representation."""
    id = fields.Int(dump_only=True)
    tour_stop_id = fields.Int(dump_only=True)
    start_time = fields.Method('format_start_time')
    end_time = fields.Method('format_end_time')
    task_name = fields.Str()
    task_description = fields.Str()
    profession_category = fields.Method('get_profession_category')
    color = fields.Str()
    order = fields.Int()
    assignments = fields.Nested(CrewAssignmentSchema, many=True, dump_only=True)

    def get_profession_category(self, obj):
        return obj.profession_category.value if obj.profession_category else None

    def format_start_time(self, obj):
        return obj.start_time.strftime('%H:%M') if obj.start_time else None

    def format_end_time(self, obj):
        return obj.end_time.strftime('%H:%M') if obj.end_time else None


# ── Document ───────────────────────────────────────────────

class DocumentSchema(BaseSchema):
    """Document representation."""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    document_type = fields.Method('get_document_type')
    description = fields.Str()
    original_filename = fields.Str(dump_only=True)
    file_size = fields.Int(dump_only=True)
    mime_type = fields.Str(dump_only=True)
    owner_type = fields.Str(dump_only=True)
    expiry_date = fields.Date(format='iso')
    issue_date = fields.Date(format='iso')
    document_number = fields.Str()
    issuing_country = fields.Str()
    expiry_status = fields.Str(dump_only=True)
    uploaded_by = fields.Nested(UserMinimalSchema, dump_only=True)
    created_at = fields.DateTime(format='iso')

    def get_document_type(self, obj):
        return obj.document_type.value if obj.document_type else None


# ── Invoice ────────────────────────────────────────────────

class InvoiceLineSchema(BaseSchema):
    """Invoice line representation."""
    id = fields.Int(dump_only=True)
    line_number = fields.Int()
    description = fields.Str()
    detail = fields.Str()
    reference = fields.Str()
    quantity = fields.Float()
    unit = fields.Str()
    unit_price_ht = fields.Float()
    discount_percent = fields.Float()
    vat_rate = fields.Float()
    vat_amount = fields.Float(dump_only=True)
    total_ht = fields.Float(dump_only=True)
    total_ttc = fields.Float(dump_only=True)


class InvoiceSchema(BaseSchema):
    """Invoice representation."""
    id = fields.Int(dump_only=True)
    number = fields.Str(dump_only=True)
    type = fields.Method('get_type')
    status = fields.Method('get_status')
    issuer_name = fields.Str()
    issuer_siret = fields.Str()
    recipient_name = fields.Str()
    recipient_email = fields.Str()
    subtotal_ht = fields.Float()
    vat_amount = fields.Float()
    total_ttc = fields.Float()
    amount_paid = fields.Float()
    amount_due = fields.Float()
    currency = fields.Str()
    issue_date = fields.Date(format='iso')
    due_date = fields.Date(format='iso')
    paid_date = fields.Date(format='iso')
    sent_date = fields.Date(format='iso')
    tour = fields.Nested(TourMinimalSchema, dump_only=True)
    payment_terms = fields.Str()
    lines = fields.Nested(InvoiceLineSchema, many=True, dump_only=True)
    created_at = fields.DateTime(format='iso')

    def get_type(self, obj):
        return obj.type.value if obj.type else None

    def get_status(self, obj):
        return obj.status.value if obj.status else None


class InvoiceMinimalSchema(BaseSchema):
    """Minimal invoice reference."""
    id = fields.Int(dump_only=True)
    number = fields.Str()
    status = fields.Method('get_status')
    total_ttc = fields.Float()
    currency = fields.Str()

    def get_status(self, obj):
        return obj.status.value if obj.status else None
