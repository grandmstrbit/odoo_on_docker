from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
import copy 
import logging
import threading

class EstateProperty(models.Model):
	_name = 'estate.property'
	_description = 'Example Estate Property'

	name = fields.Char(string='Name', required=True)
	description = fields.Text(string='Description')
	postcode = fields.Char(string='Postcode')
	date_availability = fields.Date(copy=False, string='Available From',
		default = fields.Date.today() + relativedelta(months=+3))
	expected_price = fields.Float(string="Expected Price", required=True)
	selling_price = fields.Float(copy=False, string='Selling Price', readonly=True)
	bedrooms = fields.Integer(string='Bedrooms', default="2")
	living_area = fields.Integer(string='Living Area (sqm)')
	facades = fields.Integer(string='Facades')
	garage = fields.Boolean(string='Garage')
	garden = fields.Boolean(string='Garden')
	garden_area = fields.Integer (string='Garden Area (sqm)')
	garden_orientation = fields.Selection(
		[('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')],
		string='Garden Orientation')
	status = fields.Selection(
		[('new', 'New'), ('offer received', 'Offer Received'), ('offer accepted', 'Offer Accepted'), ('sold', 'Sold'), ('canselled', 'Canselled')],
		string='Status', copy=False, required=True, default='new')
	active = fields.Boolean(string='Active', default=True)
	
	property_id = fields.Many2one('estate.property.type', string='Property Type')
	salesman_id = fields.Many2one('salesman', string='Salesman')
	buyer_id = fields.Many2one('buyer', string='Buyer')

	tax_ids = fields.Many2many('estate.property.tags')

	test_ids = fields.One2many("estate.property.offer", "partner_id", string="Offers")


class EstatePropertyType(models.Model):
	_name = 'estate.property.type'
	_description = 'Estate Property Type'

	name = fields.Char(string='Name', required=True)
	description = fields.Text(string='Description')


class Salesman(models.Model):
	_name = 'salesman'
	_description = "Lead / Opportunity"
	
	user_id = fields.Many2one('res.users', string='Salesperson', index=True, tracking=True, default=lambda self: self.env.user)
	
	
class Buyer(models.Model):
	_name = 'buyer'
	_description = "Just Buyer"

	name = fields.Char(string='Buyer', copy=False, default='Azurich aka Adunchik')
	partner_id = fields.Many2one(
        'res.partner', string='Customer', index=True, tracking=10,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")


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

