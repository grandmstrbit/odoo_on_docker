from odoo import models, fields, api



class AccountMoveLine(models.Model):
    _inherit = 'res.users'

    proeprty_ids = fields.One2many('estate.proeprty')

