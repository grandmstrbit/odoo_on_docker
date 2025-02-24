from dateutil.relativedelta import relativedelta
from odoo import api, fields, models

from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import copy 
import logging
import threading
import ast
import json
import re
import warnings


class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Example Estate Property'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    postcode = fields.Char(string='Postcode')
    date_availability = fields.Date(copy=False, string='Available From',
        default=fields.Date.today() + relativedelta(months=+3))
    expected_price = fields.Float(string="Expected Price", required=True)
    selling_price = fields.Float(copy=False, string='Selling Price', readonly=True)
    bedrooms = fields.Integer(string='Bedrooms', default="2")
    living_area = fields.Integer(string='Living Area (sqm)')
    facades = fields.Integer(string='Facades')
    garage = fields.Boolean(string='Garage')
    garden = fields.Boolean(string='Garden')
    garden_area = fields.Integer(string='Garden Area (sqm)')
    garden_orientation = fields.Selection(
        [('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')],
        string='Garden Orientation')
    status = fields.Selection(
        [('new', 'New'), ('offer received', 'Offer Received'), ('offer accepted', 'Offer Accepted'), ('sold', 'Sold'), ('canselled', 'Canselled')],
        string='Status', copy=False, required=True, default='new')
    active = fields.Boolean(string='Active', default=True)

    property_id = fields.Many2one('estate.property.type', string='Property Type')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, 
        tracking=10, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', copy=False, string='Customer', 
        index=True, tracking=10)
    tax_ids = fields.Many2many('estate.property.tags')
    offer_ids = fields.One2many("estate.property.offer", "property_id")
    best_offer = fields.Float(string='Best Offer', compute="_compute_best_offer", readonly=True)
    
    total_area = fields.Float(string="Total Area", compute="_compute_total", store=True)  # сумма двух значений
    

    @api.depends("living_area", "garden_area")
    def _compute_total(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends("offer_ids.price")
    def _compute_best_offer(self):
        for record in self:
            if record.offer_ids:  # Проверяем, есть ли связанные предложения
                record.best_offer = max(record.offer_ids.mapped("price"))
            else:
                record.best_offer = 0.0


class EstatePropertyType(models.Model):
    _name = 'estate.property.type'
    _description = 'Estate Property Type'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')


class EstatePropertyTags(models.Model):
    _name = 'estate.property.tags'
    _description = 'Estate Property Tags'

    name = fields.Char(string='Name', required=True, default="cozy")


class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'Estate Property Offer'

    price = fields.Float()
    status = fields.Selection(
        [('accepted', 'Accepted'), ('refused', 'Refused')],
        string='Status', copy=False)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    property_id = fields.Many2one('estate.property', string='Property', required=True)
    validility = fields.Integer(string="Validility (days)", default="7")
    deadline = fields.Date(string="Deadline")
