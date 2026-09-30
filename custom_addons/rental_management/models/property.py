# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api,exceptions
from odoo.exceptions import ValidationError


class PropertyDetails(models.Model):
    _name = 'property.details'
    _description = 'Property Details and for registration new Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Parent Property Field
    is_parent_property = fields.Boolean(string='Parent Property')
    parent_property_id = fields.Many2one('parent.property', string='Property ')
    parent_amenities_ids = fields.Many2many(related='parent_property_id.amenities_ids')
    parent_specification_ids = fields.Many2many(related='parent_property_id.property_specification_ids')
    parent_landlord_id = fields.Many2one(related='parent_property_id.landlord_id', string='Landlord')
    # Parent Amenities
    parent_airport = fields.Char(related='parent_property_id.airport', string='Airport ')
    parent_national_highway = fields.Char(related='parent_property_id.national_highway', string='National Highway')
    parent_metro_station = fields.Char(related='parent_property_id.metro_station', string='Metro Station ')
    parent_metro_city = fields.Char(related='parent_property_id.metro_city', string='Metro City ')
    parent_school = fields.Char(related="parent_property_id.school", string="School ")
    parent_hospital = fields.Char(related="parent_property_id.hospital", string="Hospital ")
    parent_shopping_mall = fields.Char(related="parent_property_id.shopping_mall", string="Mall ")
    parent_park = fields.Char(related="parent_property_id.park", string="Park ")
    # Address
    parent_zip = fields.Char(related='parent_property_id.zip', string='Pin Code ')
    parent_street = fields.Char(related='parent_property_id.street', string='Street1 ')
    parent_street2 = fields.Char(related='parent_property_id.street2', string='Street2 ')
    parent_city = fields.Char(related='parent_property_id.city', string='Cit')
    parent_city_id = fields.Many2one(related='parent_property_id.city_id', string='City ')
    parent_country_id = fields.Many2one(related='parent_property_id.country_id', string='Country ')
    parent_state_id = fields.Many2one(related='parent_property_id.state_id', string='State ')
    parent_website = fields.Char(related='parent_property_id.website', string='Website ')

    # Common Field

    property_seq = fields.Char(string='Sequence', required=True, readonly=True, copy=False,
                               default=lambda self: ('New'))
    name = fields.Char(string='Name', required=True)
    image = fields.Binary(string='Image')
    type = fields.Selection([('land', 'Land'),
                             ('residential', 'Residential'),
                             ('commercial', 'Commercial'),
                             ('industrial', 'Industrial')
                             ], string='Property Type', required=True)
    stage = fields.Selection([('draft', 'Draft'),
                              ('available', 'Available'),
                              ('booked', 'Booked'),
                              ('on_lease', 'On Lease'),
                              ('sale', 'Sale'),
                              ('sold', 'Sold')],
                             string='Stage', default='draft', required=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    longitude = fields.Char(string='Longitude')
    latitude = fields.Char(string='Latitude')
    sale_lease = fields.Selection([('for_sale', 'For Sale'),
                                   ('for_tenancy', 'For Tenancy')],
                                  string='Price / Rent', default='for_tenancy', required=True)
    sale_price = fields.Monetary(string='Sale Price')
    tenancy_price = fields.Monetary(string='Rent / Month')
    is_extra_service = fields.Boolean(string="Any Extra Services")
    token_amount = fields.Monetary(string='Token Amount')
    website = fields.Char(string='Website')
    sold_invoice_id = fields.Many2one('account.move', string='Sold Invoice', readonly=True)
    sold_invoice_state = fields.Boolean(string='Sold Invoice State')
    construct_year = fields.Char(string="Construct Year", size=4)
    buying_year = fields.Char(string="Buying Year", size=4)
    property_licence_no = fields.Char(string='Licence No.')
    address = fields.Char()

    # Address
    zip = fields.Char(string='Pin Code', size=6)
    street = fields.Char(string='Street1')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City  ')
    city_id = fields.Many2one('property.res.city', string='City')
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one(
        "res.country.state", string='State', readonly=False, store=True,
        domain="[('country_id', '=?', country_id)]")

    # Nearby Connectivity
    airport = fields.Char(string='Airport')
    national_highway = fields.Char(string='National Highway ')
    metro_station = fields.Char(string='Metro Station')
    metro_city = fields.Char(string='Metro City')
    school = fields.Char(string="School")
    hospital = fields.Char(string="Hospital")
    shopping_mall = fields.Char(string="Mall")
    park = fields.Char(string="Park")

    # Related Field
    landlord_id = fields.Many2one('res.partner', string='LandLord', domain=[('user_type', '=', 'landlord')])
    tenancy_ids = fields.One2many('tenancy.details', 'property_id', string='History')
    broker_ids = fields.One2many('tenancy.details', 'property_id', string='Broker',
                                 domain=[('is_any_broker', '=', True)])
    amenities_ids = fields.Many2many('property.amenities', string='Amenities ')
    property_specification_ids = fields.Many2many('property.specification', string='Specification ')
    property_vendor_ids = fields.One2many('property.vendor', 'property_id', string='Vendor Details')
    certificate_ids = fields.One2many('property.certificate', 'property_id', string='Certificate')
    maintenance_ids = fields.One2many('maintenance.request', 'property_id', string='Maintenance History')
    floreplan_ids = fields.One2many('floor.plan', 'property_id', string='Floor Plan')
    property_images_ids = fields.One2many('property.images', 'property_id', string='Images')
    tag_ids = fields.Many2many('property.tag', string='Tags')
    extra_service_ids = fields.One2many('extra.service.line', 'property_id', string="Extra Services")
    extra_service_cost = fields.Monetary(string="Total", compute="_compute_extra_service_cost")
    nearby_connectivity_ids = fields.Many2many('property.connectivity', string="Nearby Connectivity")

    # Residential
    residence_type = fields.Selection([('apartment', 'Apartment'),
                                       ('bungalow', 'Bungalow'),
                                       ('vila', 'Vila'),
                                       ('raw_house', 'Raw House'),
                                       ('duplex', 'Duplex House'),
                                       ('single_studio', 'Single Studio')],
                                      string='Type of Residence')
    total_floor = fields.Integer(string='Total Floor', default='4')
    towers = fields.Boolean(string='Tower Building')
    no_of_towers = fields.Integer(string='No. of Towers')
    furnishing = fields.Selection([('fully_furnished', 'Fully Furnished'),
                                   ('only_kitchen', 'Only Kitchen Furnished'),
                                   ('only_bed', 'Only BedRoom Furnished'),
                                   ('not_furnished', 'Not Furnished'),
                                   ], string='Furnishing', default='fully_furnished')
    bed = fields.Integer(string='Bedroom', default=1)
    bathroom = fields.Integer(string='Bathroom', default=1)
    parking = fields.Integer(string='Parking', default=1)
    facing = fields.Selection([('N', 'North(N)'),
                               ('E', 'East(E)'),
                               ('S', 'South(S)'),
                               ('W', 'West(W)'),
                               ('NE', 'North-East(NE)'),
                               ('SE', 'South-East(SE)'),
                               ('SW', 'South-West(SW)'),
                               ('NW', 'North-West(NW)'),
                               ],
                              string='Facing', default='N')
    room_no = fields.Char(string='Flat No./House No.')
    floor = fields.Integer(string='Floor')
    total_square_ft = fields.Char(string='Total Square Feet')
    usable_square_ft = fields.Char(string='Usable Square Feet')
    facilities = fields.Text(string='Facilities')

    # Land
    land_name = fields.Char(string='Land Name')
    area_hector = fields.Char(string='Area in Hector')
    land_facilities = fields.Text(string='Facility')

    # Commercial
    commercial_name = fields.Char(string='Commercial/Shop Name')
    commercial_type = fields.Selection([('full_commercial', 'Full Commercial'),
                                        ('shops', 'Shops'),
                                        ('big_hall', 'Big Hall')],
                                       string='Commercial Type')
    used_for = fields.Selection([('offices', 'Offices'),
                                 (' retail_stores', ' Retail Stores'),
                                 ('shopping_centres', 'Shopping Centres'),
                                 ('hotels', 'Hotels'),
                                 ('restaurants', 'Restaurants'),
                                 ('pubs', 'Pubs'),
                                 ('cafes', 'Cafes'),
                                 ('sport_facilities', 'Sport Facilities'),
                                 ('medical_centres', 'Medical Centres'),
                                 ('hospitals', 'Hospitals'),
                                 ('nursing_homes', 'Nursing Homes'),
                                 ('other', 'Other Use')
                                 ],
                                string='Used For')
    floor_commercial = fields.Integer(string='Floor ')
    total_floor_commercial = fields.Char(string='Total Floor ')
    commercial_facilities = fields.Text(string='Facilities ')
    other_use = fields.Char(string='Other Use')

    # Industrial
    industry_name = fields.Char(string='Industry Name')
    industry_location = fields.Selection([('inside', 'Inside City'),
                                          ('outside', 'Outside City'),
                                          ],
                                         string='Location')
    industrial_used_for = fields.Selection([('company', 'Company'),
                                            ('warehouses', 'Warehouses'),
                                            ('factories', 'Factories'),
                                            ('other', 'Other')],
                                           string='Usage')
    other_usages = fields.Char(string='Usages ')
    industrial_facilities = fields.Text(string='Facilities  ')

    # Measurement Details
    room_measurement_ids = fields.One2many('property.room.measurement', 'room_measurement_id',
                                           string='Room Measurement')
    commercial_measurement_ids = fields.One2many('property.commercial.measurement', 'commercial_measurement_id',
                                                 string='Commercial Measurement')
    industrial_measurement_ids = fields.One2many('property.industrial.measurement', 'industrial_measurement_id',
                                                 string='Industrial Measurement')
    total_room_measure = fields.Integer(string='Total Square feet ', compute='_compute_room_measure', store=True)
    total_commercial_measure = fields.Float(string='Total Square feet', compute='_compute_commercial_measure',
                                              store=True,digits=(0,2))
    total_industrial_measure = fields.Integer(string='Total Square feet  ', compute='_compute_industrial_measure',
                                              store=True)

    # CRM Lead
    lead_count = fields.Integer(string="Lead Count", compute="_compute_lead")
    lead_opp_count = fields.Integer(string="Opportunity Count", compute="_compute_lead")

    @api.depends('room_measurement_ids')
    def _compute_room_measure(self):
        for rec in self:
            total = 0
            if rec.room_measurement_ids:
                for data in rec.room_measurement_ids:
                    total = total + data.carpet_area
                    rec.total_room_measure = total
            else:
                rec.total_room_measure = 0

    @api.depends('sale_lease')
    def _compute_lead(self):
        for rec in self:
            rec.lead_count = self.env['crm.lead'].search_count([('property_id', '=', rec.id), ('type', '=', 'lead')])
            rec.lead_opp_count = self.env['crm.lead'].search_count(
                [('property_id', '=', rec.id), ('type', '=', 'opportunity')])

    @api.depends('commercial_measurement_ids')
    def _compute_commercial_measure(self):
        for rec in self:
            total = 0
            if rec.commercial_measurement_ids:
                for data in rec.commercial_measurement_ids:
                    total = total + data.carpet_area
                    rec.total_commercial_measure = total
            else:
                rec.total_commercial_measure = 0

    @api.depends('industrial_measurement_ids')
    def _compute_industrial_measure(self):
        for rec in self:
            total = 0
            if rec.industrial_measurement_ids:
                for data in rec.industrial_measurement_ids:
                    total = total + data.carpet_area
                    rec.total_industrial_measure = total
            else:
                rec.total_industrial_measure = 0

    @api.depends('extra_service_ids')
    def _compute_extra_service_cost(self):
        for rec in self:
            amount = 0.0
            if rec.extra_service_ids:
                for data in rec.extra_service_ids:
                    amount = amount + data.price
                rec.extra_service_cost = amount
            else:
                rec.extra_service_cost = 0.0

    # Smart Button Count
    document_count = fields.Integer(string='Document Count', compute='_compute_document_count')
    request_count = fields.Integer(string='Request Count', compute='_compute_request_count')
    booking_count = fields.Integer(string='Booking Count', compute='_compute_booking_count')

    # Sequence Create
    @api.model
    def create(self, vals):
        print(vals,'ooooooooooo')
        if vals.get('property_seq', 'New') == 'New':
            vals['property_seq'] = self.env['ir.sequence'].next_by_code(
                'property.details') or ('New')
        res = super(PropertyDetails, self).create(vals)
        return res

    def name_get(self):
        data = []
        for rec in self:
            if rec.is_parent_property:
                if rec.type == 'land':
                    data.append((rec.id, '%s - %s - Land' % (rec.name, rec.parent_property_id.name)))
                elif rec.type == 'residential':
                    data.append((rec.id, '%s - %s - Residential' % (rec.name, rec.parent_property_id.name)))
                elif rec.type == 'commercial':
                    data.append((rec.id, '%s - %s - Commercial' % (rec.name, rec.parent_property_id.name)))
                elif rec.type == 'industrial':
                    data.append((rec.id, '%s - %s - Industrial' % (rec.name, rec.parent_property_id.name)))
                else:
                    data = []
            else:
                if rec.type == 'land':
                    data.append((rec.id, '%s - Land' % rec.name))
                elif rec.type == 'residential':
                    data.append((rec.id, '%s - Residential' % rec.name))
                elif rec.type == 'commercial':
                    data.append((rec.id, '%s - Commercial' % rec.name))
                elif rec.type == 'industrial':
                    data.append((rec.id, '%s - Industrial' % rec.name))
                else:
                    data = []
        return data

    # Buttons
    def action_in_available(self):
        for rec in self:
            rec.stage = 'available'
        return True

    def action_in_booked(self):
        for rec in self:
            rec.stage = 'booked'
        return True

    def action_sold(self):
        for rec in self:
            rec.stage = 'sold'
        return True

    def action_in_sale(self):
        if self.sale_lease == 'for_sale':
            self.stage = 'sale'
        else:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'title': ('You need to set "Price/Rent" to "For Sale" to procced'),
                    'sticky': False,
                }
            }
            return message

    # Smart Button
    def _compute_document_count(self):
        for rec in self:
            document_count = self.env['property.documents'].search_count([('property_id', '=', rec.id)])
            rec.document_count = document_count
        return True

    def _compute_booking_count(self):
        for rec in self:
            count = self.env['property.vendor'].search_count([('property_id', '=', rec.id)])
            rec.booking_count = count
        return True

    def _compute_request_count(self):
        for rec in self:
            request_count = self.env['maintenance.request'].search_count([('property_id', '=', rec.id)])
            rec.request_count = request_count
        return True

    def action_maintenance_request(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Request',
            'res_model': 'maintenance.request',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
            'view_mode': 'kanban,list',
            'target': 'current'
        }

    def action_property_document(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Document',
            'res_model': 'property.documents',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
            'view_mode': 'list',
            'target': 'current'
        }

    def action_sale_booking(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Booking Information',
            'res_model': 'property.vendor',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
            'view_mode': 'list',
            'target': 'current'
        }

    def action_crm_lead(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leads',
            'res_model': 'crm.lead',
            'domain': [('property_id', '=', self.id), ('type', '=', 'lead')],
            'context': {'default_property_id': self.id, 'default_type': 'lead'},
            'view_mode': 'list,form',
            'target': 'current'
        }

    def action_crm_lead_opp(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Opportunity',
            'res_model': 'crm.lead',
            'domain': [('property_id', '=', self.id), ('type', '=', 'opportunity')],
            'context': {'default_property_id': self.id, 'default_type': 'opportunity'},
            'view_mode': 'list,form',
            'target': 'current'
        }

    @api.onchange('is_parent_property', 'parent_property_id')
    def _onchange_parent_property(self):
        for rec in self:
            if rec.is_parent_property and rec.parent_property_id:
                rec.nearby_connectivity_ids = [(6, 0, rec.parent_property_id.nearby_connectivity_ids.ids)]
            else:
                rec.nearby_connectivity_ids = None

    @api.model
    def get_property_stats(self):
        # Property Stages
        property = self.env['property.details']
        avail_property = property.sudo().search_count([('stage', '=', 'available')])
        booked_property = property.sudo().search_count([('stage', '=', 'booked')])
        lease_property = property.sudo().search_count([('stage', '=', 'on_lease')])
        sale_property = property.sudo().search_count([('stage', '=', 'sale')])
        sold_property = property.sudo().search_count([('stage', '=', 'sold')])
        total_property = property.sudo().search_count([])
        currency_symbol = self.env['res.currency'].search([]).mapped('symbol')
        draft_contract = self.env['tenancy.details'].sudo().search_count([('contract_type', '=', 'new_contract')])
        running_contract = self.env['tenancy.details'].sudo().search_count([('contract_type', '=', 'running_contract')])
        expire_contract = self.env['tenancy.details'].sudo().search_count([('contract_type', '=', 'expire_contract')])
        booked = self.env['property.vendor'].sudo().search_count([('stage', '=', 'booked')])
        sale_sold = self.env['property.vendor'].sudo().search_count([('stage', '=', 'sold')])

        # Total Tenancy and Sold Information
        sold_total = self.env['property.vendor'].search([('stage', '=', 'sold')]).mapped('sale_price')
        total = 0
        for price in sold_total:
            total = total + price
        total_str = str(total)
        full_tenancy_total = self.env['rent.invoice'].search(
            ['|', ('type', '=', 'rent'), ('type', '=', 'full_rent')]).mapped('amount')
        full_rent = self.env['rent.invoice'].search([]).mapped('rent_amount')
        final = full_tenancy_total + full_rent
        final_rent = 0
        for rent in final:
            final_rent = final_rent + rent
        final_rent_str = str(final_rent)

        # Pending Invoice
        pending_invoice = self.env['rent.invoice'].search_count([('payment_state', '=', 'not_paid')])

        # Property Type
        land_property = property.sudo().search_count([('type', '=', 'land')])
        residential_property = property.sudo().search_count([('type', '=', 'residential')])
        commercial_property = property.sudo().search_count([('type', '=', 'commercial')])
        industrial_property = property.sudo().search_count([('type', '=', 'industrial')])
        property_type = [['Land', 'Residential', 'Commercial', 'Industrial'],
                         [land_property, residential_property, commercial_property, industrial_property]]
        property_stage = [['Available Properties', 'Sold Properties', 'Booked Properties', 'On Sale', 'On Lease'],
                          [avail_property, sold_property, booked_property, sale_property, lease_property]]

        data = {
            'avail_property': avail_property,
            'booked_property': booked_property,
            'lease_property': lease_property,
            'sale_property': sale_property,
            'sold_property': sold_property,
            'total_property': total_property,
            'sold_total': total_str + ' ' + currency_symbol[0] if currency_symbol else "",
            'rent_total': final_rent_str + ' ' + currency_symbol[0] if currency_symbol else "",
            'draft_contract': draft_contract,
            'running_contract': running_contract,
            'expire_contract': expire_contract,
            'booked': booked,
            'sale_sold': sale_sold,
            'property_type': property_type,
            'property_stage': property_stage,
            'pending_invoice': pending_invoice,
            'tenancy_top_broker': self.get_top_broker(),
            'due_paid_amount': self.due_paid_amount(),
        }
        return data

    def get_top_broker(self):
        broker_tenancy = {}
        broker_sold = {}
        for group in self.env['tenancy.details'].read_group([('is_any_broker', '=', True)],
                                                            ['broker_id'],
                                                            ['broker_id'], limit=5):
            if group['broker_id']:
                name = self.env['res.partner'].sudo().browse(int(group['broker_id'][0])).name
                broker_tenancy[name] = group['broker_id_count']
        for group in self.env['property.vendor'].read_group([('is_any_broker', '=', True), ('stage', '=', 'sold')],
                                                            ['broker_id'],
                                                            ['broker_id'], limit=5):
            if group['broker_id']:
                name = self.env['res.partner'].sudo().browse(int(group['broker_id'][0])).name
                broker_sold[name] = group['broker_id_count']

        brokers_tenancy_list = dict(sorted(broker_tenancy.items(), key=lambda x: x[1], reverse=True))
        broker_sold_list = dict(sorted(broker_sold.items(), key=lambda x: x[1], reverse=True))
        return [list(brokers_tenancy_list.keys()), list(brokers_tenancy_list.values()), list(broker_sold_list.keys()),
                list(broker_sold_list.values())]

    def due_paid_amount(self):
        sold = {}
        tenancy = {}
        not_paid_amount_sold = 0.0
        paid_amount_sold = 0.0
        not_paid_amount_tenancy = 0.0
        paid_amount_tenancy = 0.0
        property_sold = self.env['property.vendor'].sudo().search([])
        for data in property_sold:
            if data.stage == "sold":
                if data.sold_invoice_payment_state == "not_paid":
                    not_paid_amount_sold = not_paid_amount_sold + data.sold_invoice_id.amount_total
                if data.book_invoice_payment_state == 'not_paid':
                    not_paid_amount_sold = not_paid_amount_sold + data.book_invoice_id.amount_total
                if data.sold_invoice_payment_state == "paid":
                    paid_amount_sold = paid_amount_sold + data.sold_invoice_id.amount_total
                if data.book_invoice_payment_state == 'paid':
                    paid_amount_sold = paid_amount_sold + data.book_invoice_id.amount_total
        sold['Property Sold Due'] = not_paid_amount_sold
        sold['Property Sold Paid'] = paid_amount_sold
        property_tenancy = self.env['rent.invoice'].sudo().search([])
        for rec in property_tenancy:
            if rec.payment_state == 'not_paid':
                not_paid_amount_tenancy = not_paid_amount_tenancy + rec.rent_invoice_id.amount_total
            if rec.payment_state == 'paid':
                paid_amount_tenancy = paid_amount_tenancy + rec.rent_invoice_id.amount_total
        tenancy['Tenancy Due'] = not_paid_amount_tenancy
        tenancy['Tenancy Paid'] = paid_amount_tenancy
        return [list(sold.keys()), list(sold.values()), list(tenancy.keys()),
                list(tenancy.values())]

    def action_gmap_location(self):
        if self.longitude and self.latitude:
            longitude = self.longitude
            latitude = self.latitude
            http_url = 'https://maps.google.com/maps?q=loc:' + latitude + ',' + longitude
            return {
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': http_url,
            }
        else:
            raise ValidationError("! Enter Proper Longitude and Latitude Values")

    @api.onchange('is_parent_property', 'parent_property_id')
    def _onchange_parent_landlord(self):
        for rec in self:
            if rec.is_parent_property:
                if rec.parent_property_id:
                    rec.landlord_id = rec.parent_property_id.landlord_id.id
                    rec.zip = rec.parent_property_id.zip,
                    rec.street = rec.parent_property_id.street,
                    rec.street2 = rec.parent_property_id.street2,
                    rec.city_id = rec.parent_property_id.city_id.id,
                    rec.country_id = rec.parent_property_id.country_id.id,
                    rec.state_id = rec.parent_property_id.state_id.id,
                    rec.website = rec.parent_property_id.website


# Room Measurement
class PropertyRoomMeasurement(models.Model):
    _name = 'property.room.measurement'
    _description = 'Room Property Measurement Details'

    type_room = fields.Selection([('hall', 'Hall'),
                                  ('bed_room', 'Bed Room'),
                                  ('kitchen', 'Kitchen'),
                                  ('drawing_room', 'Drawing Room'),
                                  ('bathroom', 'Bathroom'),
                                  ('store_room', 'Store Room'),
                                  ('balcony', 'Balcony'),
                                  ('wash_area', 'Wash Area'),
                                  ],
                                 string='House Section')
    length = fields.Integer(string='Length(ft)')
    width = fields.Integer(string='Width(ft)')
    height = fields.Integer(string='Height(ft)')
    no_of_unit = fields.Integer(string="No of Unit", default=1)
    carpet_area = fields.Integer(string='Carpet Area(ft²)', compute='_compute_carpet_area')
    measure = fields.Char(string='ft²', default='ft²', readonly=True)
    room_measurement_id = fields.Many2one('property.details', string='Room Details')

    @api.depends('length', 'width')
    def _compute_carpet_area(self):
        for rec in self:
            if rec.length and rec.width:
                total = rec.length * rec.width * rec.no_of_unit
                rec.carpet_area = total
            else:
                rec.carpet_area = 0


# Commercial Measurement
class PropertyCommercialMeasurement(models.Model):
    _name = 'property.commercial.measurement'
    _description = 'Commercial Property Measurement Details'

    shops = fields.Char(string='Section')
    length = fields.Integer(string='Length(ft)')
    width = fields.Integer(string='Width(ft)')
    height = fields.Integer(string='Height(ft)')
    carpet_area = fields.Float(string='Area(ft²)',digits=(10,2))#, compute='_compute_carpet_area')
    measure = fields.Char(string='ft²', default='ft²', readonly=True)
    commercial_measurement_id = fields.Many2one('property.details', string='Commercial Details')
    no_of_unit = fields.Integer(string="Floor", default=1)

    # @api.depends('length', 'width')
    # def _compute_carpet_area(self):
    #     for rec in self:
    #         if rec.length and rec.width:
    #             total = rec.length * rec.width #* rec.no_of_unit  commented because no need write now
    #             rec.carpet_area = total
    #         else:
    #             rec.carpet_area = 0

    @api.constrains('no_of_unit', 'commercial_measurement_id')
    def _check_duplicate_shops(self):
        for record in self:
            if record.no_of_unit and record.commercial_measurement_id:
                existing_shops = self.search([
                    ('no_of_unit', '=', record.no_of_unit),
                    ('commercial_measurement_id', '=', record.commercial_measurement_id.id),
                    ('id', '!=', record.id)  # Exclude itself during update
                ])
                if existing_shops:
                    raise exceptions.ValidationError(
                        "A record with the same  Floor already exists for this  property.")

    @api.model
    def create(self, vals):
        record = super(PropertyCommercialMeasurement, self).create(vals)
        record._check_duplicate_shops()
        return record

    def write(self, vals):
        result = super(PropertyCommercialMeasurement, self).write(vals)
        self._check_duplicate_shops()
        return result


class PropertyIndustrialMeasurement(models.Model):
    _name = 'property.industrial.measurement'
    _description = 'Industrial Property Measurement Details'

    asset = fields.Char(string='industrial Asset')
    length = fields.Integer(string='Length(ft)')
    width = fields.Integer(string='Width(ft)')
    height = fields.Integer(string='Height(ft)')
    carpet_area = fields.Integer(string='Area(ft²)', compute='_compute_carpet_area')
    measure = fields.Char(string='ft²', default='ft²', readonly=True)
    industrial_measurement_id = fields.Many2one('property.details', string='Industrial Details')
    no_of_unit = fields.Integer(string="No of Unit", default=1)

    @api.depends('length', 'width')
    def _compute_carpet_area(self):
        for rec in self:
            if rec.length and rec.width:
                total = rec.length * rec.width * rec.no_of_unit
                rec.carpet_area = total
            else:
                rec.carpet_area = 0


class PropertyDocuments(models.Model):
    _name = 'property.documents'
    _description = 'Document related to Property'
    _rec_name = 'doc_type'

    property_id = fields.Many2one('property.details', string='Property Name', readonly=True)
    document_date = fields.Date(string='Date', default=fields.Date.today())
    doc_type = fields.Selection([('photos', 'Photo'),
                                 ('brochure', 'Brochure'),
                                 ('certificate', 'Certificate'),
                                 ('insurance_certificate', 'Insurance Certificate'),
                                 ('utilities_insurance', 'Utilities Certificate')],
                                string='Document Type', required=True)
    document = fields.Binary(string='Documents', required=True)
    file_name = fields.Char(string='File Name')


class PropertyAmenities(models.Model):
    _name = 'property.amenities'
    _description = 'Details About Property Amenities'
    _rec_name = 'title'

    image = fields.Binary(string='Image')
    title = fields.Char(string='Title')


class PropertySpecification(models.Model):
    _name = 'property.specification'
    _description = 'Details About Property Specification'
    _rec_name = 'title'

    image = fields.Image(string='Image')
    title = fields.Char(string='Title')
    description_line1 = fields.Char(string='Description')
    description_line2 = fields.Char(string='Description Line 2')
    description_line3 = fields.Char(string='Description Line 3')


class CertificateType(models.Model):
    _name = 'certificate.type'
    _description = 'Type Of Certificate'
    _rec_name = 'type'

    type = fields.Char(string='Type')


class PropertyCertificate(models.Model):
    _name = 'property.certificate'
    _description = 'Property Related All Certificate'
    _rec_name = 'type_id'

    type_id = fields.Many2one('certificate.type', string='Type')
    expiry_date = fields.Date(string='Expiry Date')
    responsible = fields.Char(string='Responsible')
    note = fields.Char(string='Note')
    property_id = fields.Many2one('property.details', string='Property')


class ParentProperty(models.Model):
    _name = 'parent.property'
    _description = 'Parent Property Details'

    name = fields.Char(string='Name')
    image = fields.Binary(string='Image')
    amenities_ids = fields.Many2many('property.amenities', string='Amenities')
    property_specification_ids = fields.Many2many('property.specification', string='Specification')
    zip = fields.Char(string='Pin Code', size=6)
    street = fields.Char(string='Street1')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City ')
    city_id = fields.Many2one('property.res.city', string='City')
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one(
        "res.country.state", string='State', readonly=False, store=True,
        domain="[('country_id', '=?', country_id)]")
    landlord_id = fields.Many2one('res.partner', string='LandLord', domain=[('user_type', '=', 'landlord')])
    website = fields.Char(string='Website')
    airport = fields.Char(string='Airport')
    national_highway = fields.Char(string='National Highway')
    metro_station = fields.Char(string='Metro Station')
    metro_city = fields.Char(string='Metro City')
    school = fields.Char(string="School")
    hospital = fields.Char(string="Hospital")
    shopping_mall = fields.Char(string="Mall")
    park = fields.Char(string="Park")
    nearby_connectivity_ids = fields.Many2many('property.connectivity', string="Nearby Connectivity")


class FloorPlan(models.Model):
    _name = 'floor.plan'
    _description = 'Details About Floor Plan'

    image = fields.Image(string='Image')
    title = fields.Char(string='Title')
    # floor_no = fields.Selection(
    #     [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7')],
    #     string='Floor Number',
    # )
    property_id = fields.Many2one('property.details', string='Property')


class PropertyImages(models.Model):
    _name = 'property.images'
    _description = 'Property Images'

    property_id = fields.Many2one('property.details', string='Property Name', readonly=True)
    title = fields.Char(string='Title')
    image = fields.Image(string='Images')


class PropertyTag(models.Model):
    _name = 'property.tag'
    _description = 'Property Tags'
    _rec_name = 'title'

    title = fields.Char(string='Title')
    color = fields.Integer(string='Color')


class TenancyExtraService(models.Model):
    _inherit = 'product.product'

    is_extra_service_product = fields.Boolean(string="Is Extras Service")


class ExtraServiceLine(models.Model):
    _name = 'extra.service.line'
    _description = "Tenancy Extras Service"

    service_id = fields.Many2one('product.product', string="Service", domain=[('is_extra_service_product', '=', True)])
    price = fields.Float(related="service_id.lst_price", string="Cost")
    service_type = fields.Selection([('once', 'Once'), ('monthly', 'Monthly')], string="Type", default="once")
    property_id = fields.Many2one('property.details', string="Property")


class PropertyResCity(models.Model):
    _name = 'property.res.city'
    _description = 'Cities'
    name = fields.Char(string="City Name", required=True)


class PropertyConnectivity(models.Model):
    _name = 'property.connectivity'
    _description = "Property Nearby Connectivity"

    name = fields.Char(string="Title")
    distance = fields.Char(string="Distance")
    image = fields.Image(string='Images')


class AccountJournal(models.Model):
    _inherit = "account.journal"

    check_sequence_id = fields.Many2one(
            comodel_name='ir.sequence',
            string='Check Sequence',
            readonly=True,
            copy=False,
            help="Checks numbering sequence.",
        )
