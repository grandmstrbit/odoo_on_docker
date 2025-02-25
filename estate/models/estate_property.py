from dateutil.relativedelta import relativedelta
from odoo import api, fields, models

from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo.tools.float_utils import float_compare, float_is_zero

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
    selling_price = fields.Float(copy=False, string='Selling Price', readonly=True, default=0)  # По умолчанию 0
    bedrooms = fields.Integer(string='Bedrooms', default=2)
    living_area = fields.Integer(string='Living Area (sqm)')
    facades = fields.Integer(string='Facades')
    garage = fields.Boolean(string='Garage')
    garden = fields.Boolean(string='Garden')
    garden_area = fields.Integer(string='Garden Area (sqm)')
    garden_orientation = fields.Selection(
        [('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')],
        string='Garden Orientation')
    status = fields.Selection(
        [('new', 'New'), ('offer received', 'Offer Received'), ('offer accepted', 'Offer Accepted'), ('sold', 'Sold'), ('cancelled', 'Cancelled')],
        string='Status', copy=False, required=True, default='new')
    active = fields.Boolean(string='Active', default=True)

    property_id = fields.Many2one('estate.property.type', string='Property Type')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, 
        tracking=10, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', copy=False, string='Buyer', 
        index=True, tracking=10)
    tax_ids = fields.Many2many('estate.property.tags')
    offer_ids = fields.One2many("estate.property.offer", "property_id")
    best_offer = fields.Float(string='Best Offer', compute="_compute_best_offer", readonly=True)
    
    total_area = fields.Float(string="Total Area", compute="_compute_total", store=True)  # сумма двух значений
    
    _sql_constraints = [
        ('check_expected_price', 'CHECK(expected_price >= 0)', 'The expected price must be strictly positive.'),
        ('check_selling_price', 'CHECK(selling_price >= 0)',  'The selling price must be strictly positive.'),
    ]    

    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):
        for record in self:
            if float_compare(record.selling_price, 0.9 * record.expected_price, precision_digits=2) < 0:
                raise ValidationError("The selling price cannot be lower than 90% of the expected price.")

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

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10 
            self.garden_orientation = 'north'
        else:
            self.garden_area = 0
            self.garden_orientation = False

    def action_sold(self):
        for record in self:
            if record.status == 'cancelled':
                raise UserError("Cancelled properties cannot be sold.")
            record.status = 'sold'
        return True

    def action_cancel(self):
        for record in self:
            if record.status == 'sold':
                raise UserError("Sold properties cannot be cancelled.")
            record.status = 'cancelled'
        return True


class EstatePropertyType(models.Model):
    _name = 'estate.property.type'
    _description = 'Estate Property Type'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)',
         'The name must be unique.')
    ]


class EstatePropertyTags(models.Model):
    _name = 'estate.property.tags'
    _description = 'Estate Property Tags'

    name = fields.Char(string='Name', required=True, default="cozy")

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)',
         'The name must be unique.')
    ]


class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'Estate Property Offer'

    price = fields.Float()
    status = fields.Selection(
        [('draft', 'Draft'), ('accepted', 'Accepted'), ('refused', 'Refused')],
        string='Status', copy=False, default='draft')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    property_id = fields.Many2one('estate.property', string='Property', required=True)
    validity = fields.Integer(string="Validity (days)", default=7)
    deadline = fields.Date(string="Deadline", compute="_compute_deadline", 
        inverse="_inverse_deadline", store=True)
    date_deadline = fields.Date(string="Deadline", default=fields.Date.today())

    _sql_constraints = [
        ('check_price', 'CHECK(price >= 0)', 'The expected price must be strictly positive.'),
    ]      

    @api.depends("validity", "date_deadline")
    def _compute_deadline(self):
        for record in self:
            if record.date_deadline and record.validity:
                record.deadline = record.date_deadline + relativedelta(days=record.validity)
            else:
                record.deadline = False

    def _inverse_deadline(self):
        for record in self:
            if record.deadline and record.date_deadline:
                delta = (record.deadline - record.date_deadline).days
                record.validity = delta if delta > 0 else 0
            else:
                record.validity = 0

    def action_confirm(self):
        for record in self:
            # Если статус не 'draft', предложение нельзя подтвердить
            if record.status != 'draft':
                raise UserError("Only draft offers can be confirmed.")

            # Устанавливаем цену предложения (или 0, если цена не указана)
            record.price = record.price if record.price is not None else 0

            # Проверяем, что selling_price равно 0 до подтверждения предложения
            if not float_is_zero(record.property_id.selling_price, precision_digits=2):
                raise UserError("Selling price must be zero until an offer is confirmed.")

            # Устанавливаем продажную цену и покупателя в связанной модели EstateProperty
            record.property_id.write({
                'selling_price': record.price,  # Устанавливаем продажную цену
                'partner_id': record.partner_id.id,  # Устанавливаем покупателя
            })

            # Отклоняем все другие предложения для этого свойства
            other_offers = self.search([
                ('property_id', '=', record.property_id.id),
                ('id', '!=', record.id),
                ('status', '=', 'draft'),
            ])
            other_offers.write({'status': 'refused'})

            # Устанавливаем статус текущего предложения как "accepted"
            record.status = 'accepted'
        return True

    def action_refuse(self):
        for record in self:
            # Если статус не 'draft', предложение нельзя отказать
            if record.status != 'draft':
                raise UserError("Only draft offers can be refused.")
            record.status = 'refused'
        return True