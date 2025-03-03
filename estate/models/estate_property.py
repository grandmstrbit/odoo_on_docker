from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero



class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Example Estate Property'
    _order = 'id desc'

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
        ('check_expected_price', 'CHECK(expected_price > 0 AND expected_price != 0)', 'The expected price must be strictly positive.'),
        ('check_selling_price', 'CHECK(selling_price >= 0)',  'The selling price must be strictly positive.'),
    ]

    @api.ondelete(at_uninstall=False)
    def _delete_properties(self):
        for record in self:
            if record.status != 'new':
                raise UserError("Only New and Cancelled can be deleted")

    @api.constrains('selling_price', 'expected_price') #цена не менее 90%
    def _check_selling_price(self):
        for record in self:
            if float_is_zero(record.selling_price, precision_digits=2):
                continue
            if float_compare(record.selling_price, 0.9 * record.expected_price, precision_digits=2) < 0:
                raise ValidationError("The selling price cannot be lower than 90% of the expected price.")

    @api.depends("living_area", "garden_area") #общая площадь сада и дома
    def _compute_total(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends("offer_ids.price") #лучшее предложение
    def _compute_best_offer(self):
        for record in self:
            if record.offer_ids:  # Проверяем, есть ли связанные предложения
                record.best_offer = max(record.offer_ids.mapped("price"))
            else:
                record.best_offer = 0.0

    @api.onchange("garden") #если активно, устанавливает значения по умолчанию
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10 
            self.garden_orientation = 'north'
        else:
            self.garden_area = 0
            self.garden_orientation = False

    def action_sold(self): #кнопка 
        for record in self:
            if record.status == 'cancelled':
                raise UserError("Cancelled properties cannot be sold.")
            record.status = 'sold'
        return True

    def action_cancel(self): #кнопка
        for record in self:
            if record.status == 'sold':
                raise UserError("Sold properties cannot be cancelled.")
            record.status = 'cancelled'
        return True

    def unlink(self): #для удаления форм
        for record in self:
            record.offer_ids.unlink()
        return super(EstateProperty, self).unlink()

    def _update_property_status(self): #метод для обновления статуса свойства на основе предложений
        for property in self:
            if any(offer.status == 'accepted' for offer in property.offer_ids):
                property.write({'status': 'offer accepted'})
            elif property.offer_ids:
                property.write({'status': 'offer received'})
            else:
                property.write({'status': 'new'})



class EstatePropertyType(models.Model):
    _name = 'estate.property.type'
    _description = 'Estate Property Type'
    _order = 'sequence ASC, name ASC'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    offer_ids = fields.One2many('estate.property.offer', 'property_type_id', string='Offers')
    offer_count = fields.Integer(string="Quantity Offers", compute='_compute_offer_count', store=True)
    
    property_ids = fields.One2many("estate.property", "property_id")

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)',
         'The name must be unique.')
    ]

    @api.depends('offer_ids')
    def _compute_offer_count(self):
        for record in self:
            record.offer_count = len(record.offer_ids)


class EstatePropertyTags(models.Model):
    _name = 'estate.property.tags'
    _description = 'Estate Property Tags'
    _order = 'name asc'

    name = fields.Char(string='Name', required=True)
    color = fields.Integer() 

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)',
         'The name must be unique.')
    ]


class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'Estate Property Offer'
    _order = 'price desc'

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
    property_type_id = fields.Many2one('estate.property.type', string="Property Type", 
        related='property_id.property_id', store=True)

    _sql_constraints = [
        ('check_price', 'CHECK(price > 0 AND price != 0)', 'The offer price must be strictly positive.'),
    ]      

    @api.model
    def create(self, vals):
        # Получаем свойство, к которому относится предложение
        property_id = self.env['estate.property'].browse(vals.get('property_id'))
        # Проверяем, есть ли существующие предложения
        if property_id.offer_ids:
            # Находим максимальную сумму среди существующих предложений
            max_offer_price = max(property_id.offer_ids.mapped('price'))   
            # Если новое предложение меньше максимального, вызываем ошибку
            if vals.get('price', 0.0) < max_offer_price:
                raise ValidationError("The offer price cannot be lower than the existing.")
        # Создаем предложение
        offer = super(EstatePropertyOffer, self).create(vals)
        # Обновляем статус связанного свойства на "Offer Received"
        if offer.property_id:
            offer.property_id._update_property_status()
        return offer

    @api.depends("validity", "date_deadline") #расчет дэдлайна
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

    def action_confirm(self): #кнопка в модели offer
        for record in self:
            # Устанавливаем продажную цену и покупателя в связанной модели EstateProperty
            record.property_id.write({
                'selling_price': record.price,  # Устанавливаем продажную цену
                'partner_id': record.partner_id.id,  # Устанавливаем покупателя
            })
            record.status = 'accepted'
            record.property_id._update_property_status()
        return True

    def action_refuse(self): #кнопка в модели offer
        for record in self:
            record.property_id.write({
                'selling_price': 0,
                'partner_id': False,
                })
            record.status = 'refused'
            record.property_id._update_property_status()
        return True


class ResUsers(models.Model):
    _inherit = 'res.users'


    property_ids = fields.One2many('estate.property', 'user_id', string='uWu', domain=[('active', '=', True)])

    @api.depends('property_ids')
    def _compute_property_count(self):
        for record in self:
            record.property_count = len(record.property_ids)
    property_count = fields.Integer(string='Number of Properties', compute='_compute_proeprty_count')