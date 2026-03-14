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
    """Full user representation (for /me endpoint and user management)."""
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
    professions = fields.Method('get_professions')
    created_at = fields.DateTime(format='iso')

    # Personal information
    date_of_birth = fields.Date()
    nationality = fields.Str()
    label_name = fields.Str()
    receive_emails = fields.Bool()

    # Travel preferences
    preferred_airline = fields.Str()
    seat_preference = fields.Str()
    meal_preference = fields.Str()
    hotel_preferences = fields.Str()

    # Emergency contact
    emergency_contact_name = fields.Str()
    emergency_contact_relation = fields.Str()
    emergency_contact_phone = fields.Str()
    emergency_contact_email = fields.Str()

    # Health / Dietary
    dietary_restrictions = fields.Str()
    allergies = fields.Str()

    # Billing � Contract
    contract_type = fields.Str()
    payment_frequency = fields.Str()

    # Billing � Rates
    show_rate = fields.Decimal(as_string=True)
    daily_rate = fields.Decimal(as_string=True)
    half_day_rate = fields.Decimal(as_string=True)
    hourly_rate = fields.Decimal(as_string=True)
    per_diem = fields.Decimal(as_string=True)
    overtime_rate_25 = fields.Decimal(as_string=True)
    overtime_rate_50 = fields.Decimal(as_string=True)
    weekend_rate = fields.Decimal(as_string=True)
    holiday_rate = fields.Decimal(as_string=True)
    night_rate = fields.Decimal(as_string=True)

    # Billing � Bank details
    iban = fields.Str()
    bic = fields.Str()
    bank_name = fields.Str()
    account_holder = fields.Str()

    # Billing � Tax info
    siret = fields.Str()
    siren = fields.Str()
    vat_number = fields.Str()

    def get_access_level(self, obj):
        return obj.access_level.value if obj.access_level else None

    def get_professions(self, obj):
        if not hasattr(obj, 'user_professions') or not obj.user_professions:
            return []
        return [
            {
                'id': up.profession_id,
                'name_fr': up.profession.name_fr if up.profession else None,
                'category': up.profession.category.value if up.profession and up.profession.category else None,
                'is_primary': up.is_primary,
            }
            for up in obj.user_professions
        ]


# ── Band ────────────────────────────────────────────────────

class BandSchema(BaseSchema):
    """Band representation."""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    genre = fields.Str()
    bio = fields.Str()
    website = fields.Str()
    manager = fields.Nested(UserMinimalSchema, dump_only=True)
    tours_count = fields.Method('get_tours_count')
    created_at = fields.DateTime(format='iso')

    def get_tours_count(self, obj):
        return len(obj.tours) if hasattr(obj, 'tours') and obj.tours else 0


class BandMembershipSchema(BaseSchema):
    """Band membership (flat format for mobile app)."""
    id = fields.Int(dump_only=True)
    user_id = fields.Method('get_user_id')
    first_name = fields.Method('get_first_name')
    last_name = fields.Method('get_last_name')
    instrument = fields.Str()
    role_in_band = fields.Str()
    is_active = fields.Bool()

    def get_user_id(self, obj):
        return obj.user.id if obj.user else None

    def get_first_name(self, obj):
        return obj.user.first_name if obj.user else None

    def get_last_name(self, obj):
        return obj.user.last_name if obj.user else None


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
    latitude = fields.Float()
    longitude = fields.Float()


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
    upcoming_stops_count = fields.Method('get_upcoming_stops_count')
    past_stops_count = fields.Method('get_past_stops_count')
    created_at = fields.DateTime(format='iso')

    def get_status(self, obj):
        return obj.status.value if obj.status else None

    def get_stops_count(self, obj):
        return len(obj.stops) if hasattr(obj, 'stops') and obj.stops else 0

    def get_upcoming_stops_count(self, obj):
        return len(obj.upcoming_stops) if hasattr(obj, 'stops') and obj.stops else 0

    def get_past_stops_count(self, obj):
        return len(obj.past_stops) if hasattr(obj, 'stops') and obj.stops else 0


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
    venue_id = fields.Int(allow_none=True)
    venue = fields.Nested(VenueMinimalSchema, dump_only=True)
    address = fields.Method('get_address')
    city = fields.Method('get_city')
    country = fields.Method('get_country')

    def get_address(self, obj):
        return obj.location_address

    def get_city(self, obj):
        return obj.location_city

    def get_country(self, obj):
        return obj.location_country

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
    profession_id = fields.Int(dump_only=True)
    profession_name = fields.Method('get_profession_name')
    status = fields.Method('get_status')
    call_time = fields.Method('format_call_time')
    notes = fields.Str()
    assigned_at = fields.DateTime(format='iso')
    confirmed_at = fields.DateTime(format='iso')

    def get_status(self, obj):
        return obj.status.value if obj.status else None

    def get_profession_name(self, obj):
        if hasattr(obj, 'profession') and obj.profession:
            return obj.profession.name_fr
        return None

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


# ── Profession ─────────────────────────────────────────────

class ProfessionSchema(BaseSchema):
    """Profession representation (for settings / profession management)."""
    id = fields.Int(dump_only=True)
    code = fields.Str()
    name_fr = fields.Str()
    name_en = fields.Str()
    category = fields.Method('get_category')
    category_label = fields.Str(dump_only=True)
    category_color = fields.Str(dump_only=True)
    description = fields.Str()
    default_access_level = fields.Str()
    sort_order = fields.Int()
    is_active = fields.Bool()
    show_rate = fields.Method('get_show_rate')
    daily_rate = fields.Method('get_daily_rate')
    weekly_rate = fields.Method('get_weekly_rate')
    per_diem = fields.Method('get_per_diem')
    default_frequency = fields.Str()

    def get_category(self, obj):
        return obj.category.value if obj.category else None

    def get_show_rate(self, obj):
        return float(obj.show_rate) if obj.show_rate else None

    def get_daily_rate(self, obj):
        return float(obj.daily_rate) if obj.daily_rate else None

    def get_weekly_rate(self, obj):
        return float(obj.weekly_rate) if obj.weekly_rate else None

    def get_per_diem(self, obj):
        return float(obj.per_diem) if obj.per_diem else None


class ProfessionMinimalSchema(BaseSchema):
    """Minimal profession reference (for dropdowns, assignment display)."""
    id = fields.Int(dump_only=True)
    code = fields.Str()
    name_fr = fields.Str()
    category = fields.Method('get_category')

    def get_category(self, obj):
        return obj.category.value if obj.category else None


class UserProfessionSchema(BaseSchema):
    """User-profession association."""
    id = fields.Int(dump_only=True)
    profession_id = fields.Int()
    name_fr = fields.Method('get_name_fr')
    category = fields.Method('get_category')
    is_primary = fields.Bool()
    notes = fields.Str()

    def get_name_fr(self, obj):
        return obj.profession.name_fr if obj.profession else None

    def get_category(self, obj):
        return obj.profession.category.value if obj.profession and obj.profession.category else None


# ── Planning Slot ─────────────────────────────────────────

class PlanningSlotSchema(BaseSchema):
    """Planning slot for daily concert staff scheduling."""
    id = fields.Int(dump_only=True)
    tour_stop_id = fields.Int(dump_only=True)
    role_name = fields.Str()
    category = fields.Str()
    category_color = fields.Str(dump_only=True)
    start_time = fields.Method('format_start_time')
    end_time = fields.Method('format_end_time')
    time_range = fields.Str(dump_only=True)
    task_description = fields.Str()
    user_id = fields.Int(allow_none=True)
    user_name = fields.Method('get_user_name')
    created_at = fields.DateTime(format='iso')

    def format_start_time(self, obj):
        return obj.start_time.strftime('%H:%M') if obj.start_time else None

    def format_end_time(self, obj):
        return obj.end_time.strftime('%H:%M') if obj.end_time else None

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else None
