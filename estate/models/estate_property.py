from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero
import io
import base64
from docx import Document


class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Example Estate Property'
    _order = 'id desc'
"""
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
    offer_count = fields.Integer(string=" ", compute='_compute_offer_count', store=True)
    
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
"""

# Модель для хранения данных СРО
'''
class SroContacts(models.Model):
    _name = 'sro.contacts'
    _description = 'SRO Contacts'
   # Регистрационные данные
    registration_number = fields.Char(string="Регистрационный номер")
    short_name = fields.Char(string="Сокращенное наименование")
    full_name = fields.Char(string="Полное наименование")
    inn = fields.Char(string="ИНН")
    ogrn = fields.Char(string="ОГРН")
    registration_date = fields.Date(string="Дата гос. регистрации ЮЛ/ИП")

    # Сведения о членстве в СРО
    sro_membership_compliance = fields.Selection([
        ('active', 'Соответствует'),
        ('suspended', 'Не соответствует'),
    ], string="Сведения о соответствии члена СРО условиям членства, предусмотренным законодательством РФ и (или) внутренними документами СРО")
    sro_membership_status = fields.Selection([
        ('active', 'Является членом'),
        ('suspended', 'Исключен'),
    ], string="Статус членства")
    sro_registration_date = fields.Date(string="Дата регистрации в реестре СРО (внесения сведений в реестр)")
    sro_admission_basis = fields.Char(string="Основание приема в СРО") #Должна быть ссылка на документ

    # Компенсационные фонды
    compensation_fund_vv_amount = fields.Float(string="Сумма взноса в Компенсационный Фонд возмещения вреда (КФ ВВ) (руб.)")
    vv_responsibility_level = fields.Char(string="Уровень ответственности ВВ")
    contract_work_cost = fields.Char(string="Стоимость работ по одному договору")
    compensation_fund_odo_amount = fields.Float(string="Сумма взноса в Компенсационный Фонд обеспечения договорных обязательств (КФ ОДО) (руб.)")
    odo_responsibility_level = fields.Char(string="Уровень ответственности ОДО")
    max_obligation_amount = fields.Char(string="Предельный размер обязательств по договорам, заключаемым с использованием конкурентных способов заключения договоров")

    # Руководство
    executive_authority = fields.Char(string="Единоличный исполнительный орган/руководитель коллегиального испольнительного органа")

    # Контактные данные
    phone = fields.Char(string="Контактные телефоны")
    zip = fields.Char(string="Индекс")
    country_id = fields.Many2one('res.country', string="Страна")
    state_id = fields.Many2one('res.country.state', string="Субъект РФ")
    city = fields.Char(string="Населённый пункт")
    street = fields.Char(string="Улица")
    street2 = fields.Char(string="Дом")

    # Страхование
    insurer_info = fields.Text(string="Сведения о страховщике") #СОЗДАТЬ МОДЕЛЬ с атрибутами, сделать связи one2many 
    insurance_contract_number = fields.Char(string="Номер договора страхования")
    insurance_contract_expiry = fields.Date(string="Срок действия договора страхования", widget="daterange")
    insurance_amount = fields.Float(string="Страховая сумма (руб.)")

    # Связь с res.partner
    partner_id = fields.Many2one('res.partner', string='Контакты')
'''

class SroContactsWork(models.Model):
    _name = 'sro.contacts.work'
    _description = "sro contacts work"

    # Сведения о наличии прав на выполнение работ
    number = fields.Integer(string="№")
    right_status = fields.Selection([
        ('active', 'Действует'),
        ('suspended', 'Прекращено'),
    ], string="Статус права")
    right_effective_date = fields.Date(string="Дата вступления решения в силу")
    right_basis = fields.Char(string="Основание выдачи") # ССЫЛКА НА ДОКУМЕНТ
    construction_object = fields.Selection([
        ('yes', 'Да'),
        ('no', 'Нет'),
    ], string="Объект капитального строительства")
    hazardous_objects = fields.Selection([
        ('yes', 'Да'),
        ('no', 'Нет'),
    ], string="Особо опасные, технически сложные и уникальные объекты")
    nuclear_objects = fields.Selection([
        ('yes', 'Да'),
        ('no', 'Нет'),
    ], string="Объекты использования атомной энергии")
    odo_right = fields.Selection([
        ('yes', 'Да'),
        ('no', 'Нет'),
        ('draft', 'Правом не наделен'),
    ], string="Наличие права на ОДО") # ДОБАВИТЬ ССЫЛКУ НА ПРОТОКОЛ
    date_field = fields.Date()

    partner2_id = fields.Many2one('res.partner', invisible=True)

    @api.model
    def create_record(self):
        record = self.create({
            'odo_right': 'draft',  # Устанавливаем значение в поле Selection
            'date_field': date.today(),  # Устанавливаем текущую дату
        })

        return record

    def action_export_work_docx(self):
        """Генерирует DOCX-файл с данными о наличии прав на выполнение работ"""
        self.ensure_one()  # Гарантируем, что метод вызывается для одной записи

        doc = Document()
        doc.add_heading(f'Сведения о праве на выполнение работ', level=1)

        doc.add_paragraph(f"№: {self.number or '—'}")
        doc.add_paragraph(f"Статус права: {dict(self._fields['right_status'].selection).get(self.right_status, '—')}")
        doc.add_paragraph(f"Дата вступления в силу: {self.right_effective_date or '—'}")
        doc.add_paragraph(f"Основание выдачи: {self.right_basis or '—'}")

        doc.add_heading('Объекты работ', level=2)
        doc.add_paragraph(f"Объект капитального строительства: {dict(self._fields['construction_object'].selection).get(self.construction_object, '—')}")
        doc.add_paragraph(f"Особо опасные, технически сложные и уникальные объекты: {dict(self._fields['hazardous_objects'].selection).get(self.hazardous_objects, '—')}")
        doc.add_paragraph(f"Объекты использования атомной энергии: {dict(self._fields['nuclear_objects'].selection).get(self.nuclear_objects, '—')}")

        doc.add_heading('Право на ОДО', level=2)
        doc.add_paragraph(f"Наличие права на ОДО: {dict(self._fields['odo_right'].selection).get(self.odo_right, '—')}")

        # Сохраняем в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Кодируем файл в base64 и создаём вложение
        attachment = self.env['ir.attachment'].create({
            'name': f'Право_на_работу_{self.number}.docx',
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': 'sro.contacts.work',
            'res_id': self.id,
            'type': 'binary',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

class SroContactsDiscipline(models.Model):
    _name = 'sro.contacts.discipline'
    _description = "sro contacts discipline"

    # Новые поля: Сведения о дисциплинарных производствах
    disciplinary_basis = fields.Char(string="Основание открытия дисциплинарного производства")
    disciplinary_start_date = fields.Date(string="Дата открытия дисциплинарного производства")
    disciplinary_decision = fields.Text(string="Решение дисциплинарной комиссии")
    disciplinary_decision_date = fields.Date(string="Дата решения дисциплинарной комиссии")

    partner3_id = fields.Many2one('res.partner', invisible=True)

    def action_export_discipline_docx(self):
        """Генерация DOCX с информацией о дисциплинарном производстве"""
        self.ensure_one()

        doc = Document()
        doc.add_heading('Сведения о дисциплинарном производстве', level=1)

        doc.add_paragraph(f"Основание открытия: {self.disciplinary_basis or '—'}")
        doc.add_paragraph(f"Дата открытия: {self.disciplinary_start_date or '—'}")
        doc.add_paragraph(f"Решение комиссии:\n{self.disciplinary_decision or '—'}")
        doc.add_paragraph(f"Дата решения: {self.disciplinary_decision_date or '—'}")

        # Сохраняем в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Создание вложения в Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f"Сведения_о_дисциплинарном_производстве.docx",
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': 'sro.contacts.discipline',
            'res_id': self.id,
            'type': 'binary',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class SroContactsInspection(models.Model):
    _name = 'sro.contacts.inspection'
    _description = "sro contacts inspection"

    # Новые поля: Сведения о результатах проведенных проверок
    inspection_member_number = fields.Char(string="Регистрационный номер члена")
    inspection_act_date = fields.Date(string="Дата акта проверки")
    inspection_month_year = fields.Date(string="Месяц, год проверки")
    inspection_type = fields.Selection([
        ('scheduled', 'Плановая'),
        ('unscheduled', 'Внеплановая'),
    ], string="Вид проверки")
    inspection_form = fields.Selection([
        ('documentary', 'Документарная'),
        ('onsite', 'Выездная'),
    ], string="Форма проверки")
    inspection_law_violations = fields.Text(string="Нарушения требований законодательства РФ о градостроительной деятельности, о техническом регулировании, Стандартов НОСТРОЙ")
    inspection_internal_violations = fields.Text(string="Нарушения внутренних документов и стандартов А 'СО 'СЧ'")
    inspection_contract_violations = fields.Text(string="Нарушение исполнения обязательств по договорам строительного подряда, заключенным с использованием конкурентных способов заключения договоров")
    inspection_result = fields.Selection([
        ('yes', 'Нарушения имеются'),
        ('no', 'Нарушений не имеется'),
        ('draft', 'Проверки не проводились'),
    ], string="Результат проверки (итог)")
    inspection_disciplinary_measures = fields.Text(string="Применение мер дисциплинарного воздействия (итог)")
    inspection_measures_list = fields.Text(string="Перечень мер дисциплинарного воздействия")

    partner4_id = fields.Many2one('res.partner', invisible=True)

    def action_export_inspection_docx(self):
        """Генерация DOCX с данными о результатах проверки"""
        doc = Document()
        doc.add_heading('Сведения о результатах проведенной проверки', level=1)

        doc.add_paragraph(f"Регистрационный номер члена: {self.inspection_member_number or '—'}")
        doc.add_paragraph(f"Дата акта проверки: {self.inspection_act_date or '—'}")
        doc.add_paragraph(f"Месяц, год проверки: {self.inspection_month_year or '—'}")
        doc.add_paragraph(f"Вид проверки: {dict(self._fields['inspection_type'].selection).get(self.inspection_type, '—')}")
        doc.add_paragraph(f"Форма проверки: {dict(self._fields['inspection_form'].selection).get(self.inspection_form, '—')}")
        doc.add_paragraph(f"Нарушения законодательства: {self.inspection_law_violations or '—'}")
        doc.add_paragraph(f"Нарушения внутренних документов: {self.inspection_internal_violations or '—'}")
        doc.add_paragraph(f"Нарушение обязательств по договорам: {self.inspection_contract_violations or '—'}")
        doc.add_paragraph(f"Результат проверки: {dict(self._fields['inspection_result'].selection).get(self.inspection_result, '—')}")
        doc.add_paragraph(f"Меры дисциплинарного воздействия: {self.inspection_disciplinary_measures or '—'}")
        doc.add_paragraph(f"Перечень мер дисциплинарного воздействия:\n{self.inspection_measures_list or '—'}")

        # Сохраняем в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Создание вложения в Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f"Сведения_о_результатах_проведенной_проверки.docx",
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': 'sro.contacts.inspection',
            'res_id': self.id,
            'type': 'binary',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

class SroContactsContract(models.Model):
    _name = 'sro.contacts.contract'
    _description = "sro contacts contract"

    # Новые поля: Предложения подрядов
    tender_type = fields.Selection([
        ('offer', 'Предложение подряда'),
        ('search', 'Поиск подряда'),
    ], string="Предложение или поиск подряда")
    tender_description = fields.Text(string="Описание подряда")
    tender_contact_info = fields.Text(string="Контактные данные")
    tender_member_number = fields.Char(string="Регистрационный номер члена")
    tender_short_name = fields.Char(string="Сокращенное наименование организации")

    partner5_id = fields.Many2one('res.partner', invisible=True)

    def action_export_contract_docx(self):
        """Генерация DOCX с данными о результатах проверки"""
        doc = Document()
        doc.add_heading('Предложение подряда', level=1)

        doc.add_paragraph(f"Предложение или поиск подряда: {dict(self._fields['tender_type'].selection).get(self.tender_type, '—')}")
        doc.add_paragraph(f"Описание подряда: {self.tender_description or '—'}")
        doc.add_paragraph(f"Контактные данные: {self.tender_contact_info or '—'}")
        doc.add_paragraph(f"Регистрационный номер члена: {self.tender_member_number or '—'}")
        doc.add_paragraph(f"Сокращённое наименование организации: {self.tender_short_name or '—'}")

        # Сохраняем в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Создание вложения в Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f"Предложение_подряда.docx",
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': 'sro.contacts.contract',
            'res_id': self.id,
            'type': 'binary',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

class InsurerInfo(models.Model):
    _name = "insurer.info"
    _description = "insurer info"

    name = fields.Char(string="Наименование организации")
    license_number = fields.Char(string="№ Лицензии")
    address = fields.Text(string="Адрес")
    phone_insurer = fields.Char(string="Контактные телефоны")
    website = fields.Char(string="Веб-сайт")
    email = fields.Char(string="Электронная почта")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Регистрационные данные
    registration_number = fields.Char(string="Регистрационный номер")
    short_name = fields.Char(string="Сокращенное наименование")
    full_name = fields.Char(string="Полное наименование")
    inn = fields.Char(string="ИНН")
    ogrn = fields.Char(string="ОГРН")
    registration_date = fields.Date(string="Дата гос. регистрации ЮЛ/ИП")

    # Сведения о членстве в СРО
    sro_membership_compliance = fields.Selection([
        ('active', 'Соответствует'),
        ('suspended', 'Не соответствует'),
    ], string="Сведения о соответствии члена СРО условиям членства, предусмотренным законодательством РФ и (или) внутренними документами СРО")
    sro_membership_status = fields.Selection([
        ('active', 'Является членом'),
        ('suspended', 'Исключен'),
    ], string="Статус членства")
    sro_registration_date = fields.Date(string="Дата регистрации в реестре СРО (внесения сведений в реестр)")
    sro_admission_basis = fields.Char(string="Основание приема в СРО") #Должна быть ссылка на документ

    # Компенсационные фонды
    compensation_fund_vv_amount = fields.Float(string="Сумма взноса в Компенсационный Фонд возмещения вреда (КФ ВВ) (руб.)")
    vv_responsibility_level = fields.Char(string="Уровень ответственности ВВ")
    contract_work_cost = fields.Char(string="Стоимость работ по одному договору")
    compensation_fund_odo_amount = fields.Float(string="Сумма взноса в Компенсационный Фонд обеспечения договорных обязательств (КФ ОДО) (руб.)")
    odo_responsibility_level = fields.Char(string="Уровень ответственности ОДО")
    max_obligation_amount = fields.Char(string="Предельный размер обязательств по договорам, заключаемым с использованием конкурентных способов заключения договоров")

    # Руководство
    executive_authority = fields.Char(string="Единоличный исполнительный орган/руководитель коллегиального испольнительного органа")

    # Контактные данные
    phone_sro = fields.Char(string="Контактные телефоны")
    zip = fields.Char(string="Адрес (Индекс)")
    country_id = fields.Many2one('res.country', string="Адрес (Страна)")
    state_id = fields.Many2one('res.country.state', string="Адрес (Субъект РФ)")
    city = fields.Char(string="Адрес (Населённый пункт)")
    street = fields.Char(string="Адрес (Улица)")
    street2 = fields.Char(string="Адрес (Дом)")

    # Страхование
    insurer_info = fields.Many2one('insurer.info', string="Сведения о страховщике") #СОЗДАТЬ МОДЕЛЬ с атрибутами, сделать связи one2many 
    
    insurer_name = fields.Char(string="Наименование организации", related='insurer_info.name', readonly=True)
    insurer_license_number = fields.Char(string="№ Лицензии", related='insurer_info.license_number', readonly=True)
    insurer_address = fields.Text(string="Адрес", related='insurer_info.address', readonly=True)
    insurer_phone = fields.Char(string="Контактные телефоны", related='insurer_info.phone_insurer', readonly=True)
    insurer_website = fields.Char(string="Веб-сайт", related='insurer_info.website', readonly=True)
    insurer_email = fields.Char(string="Электронная почта", related='insurer_info.email', readonly=True)

    insurance_contract_number = fields.Char(string="Номер договора страхования")
    insurance_contract_expiry = fields.Char(string="Срок действия договора страхования")
    insurance_amount = fields.Float(string="Страховая сумма (руб.)")

    # Связь One2many с sro.contacts
    #sro_contact_ids = fields.One2many('sro.contacts', 'partner_id', string="Сведения о членах СРО")
    sro_contact2_ids = fields.One2many('sro.contacts.work', 'partner2_id', string="Права на выполнение работ")
    sro_contact3_ids = fields.One2many('sro.contacts.discipline', 'partner3_id', string="Дисциплинарные производства")
    sro_contact4_ids = fields.One2many('sro.contacts.inspection', 'partner4_id', string="Результаты проведения проверок")
    sro_contact5_ids = fields.One2many('sro.contacts.contract', 'partner5_id', string="Предложения подрядов")

    def action_export_contact_docx(self):
        """Генерирует DOCX-файл с информацией о текущем контакте"""
        self.ensure_one()  # Гарантируем, что метод вызывается для одного контакта

        doc = Document()
        doc.add_heading(f'Контактная информация: {self.name}', level=1)

        # Основные регистрационные данные
        doc.add_heading('Регистрационные данные', level=2)
        doc.add_paragraph(f"Регистрационный номер: {self.registration_number or '—'}")
        doc.add_paragraph(f"Сокращённое наименование: {self.short_name or '—'}")
        doc.add_paragraph(f"Полное наименование: {self.full_name or '—'}")
        doc.add_paragraph(f"ИНН: {self.inn or '—'}")
        doc.add_paragraph(f"ОГРН: {self.ogrn or '—'}")
        doc.add_paragraph(f"Дата гос. регистрации ЮЛ/ИП: {self.registration_date or '—'}")

        # Членство в СРО
        doc.add_heading('Членство в СРО', level=2)
        doc.add_paragraph(f"Статус членства: {dict(self._fields['sro_membership_status'].selection).get(self.sro_membership_status, '—')}")
        doc.add_paragraph(f"Сведения о соответствии члена СРО условиям членства, предусмотренным законодательством РФ и (или) внутренними документами СРО: {dict(self._fields['sro_membership_compliance'].selection).get(self.sro_membership_compliance, '—')}")
        doc.add_paragraph(f"Дата регистрации в реестре СРО (внесения сведений в реестр): {self.sro_registration_date or '—'}")
        doc.add_paragraph(f"Основание приёма в СРО: {self.sro_admission_basis or '—'}")

        # Компенсационные фонды
        doc.add_heading('Компенсационные фонды', level=2)
        doc.add_paragraph(f"Сумма взноса в Компенсационный Фонд возмещения вреда (КФ ВВ) (руб.): {self.compensation_fund_vv_amount or '—'} руб.")
        doc.add_paragraph(f"Уровень ответственности ВВ: {self.vv_responsibility_level or '—'}")
        doc.add_paragraph(f"Стоимость работ по одному договору: {self.contract_work_cost or '—'}")
        doc.add_paragraph(f"Сумма взноса в Компенсационный Фонд обеспечения договорных обязательств (КФ ОДО) (руб.): {self.compensation_fund_odo_amount or '—'} руб.")
        doc.add_paragraph(f"Уровень ответственности ОДО: {self.odo_responsibility_level or '—'}")
        doc.add_paragraph(f"Предельный размер обязательств по договорам, заключаемым с использованием конкурентных способов заключения договоров: {self.max_obligation_amount or '—'}")

        # Руководство
        doc.add_heading('Руководство', level=2)
        doc.add_paragraph(f"Единоличный исполнительный орган/руководитель коллегиального исполнительного органа: {self.executive_authority or '—'}")

        # Контактные данные
        doc.add_heading('Контактные данные', level=2)
        doc.add_paragraph(f"Контактный телефон: {self.phone_sro or '—'}")
        doc.add_paragraph(f"Адрес: {self.zip or ''}, {self.country_id.name or ''}, {self.state_id.name or ''}, {self.city or ''}, {self.street or ''}")

        # Страхование
        doc.add_heading('Страхование', level=2)
        doc.add_paragraph(f"Сведения о страховщике: {''}")
        doc.add_paragraph(f"Наименование организации: {self.insurer_name or '—'}") 
        doc.add_paragraph(f"№ Лицензии: {self.insurer_license_number or '—'}")
        doc.add_paragraph(f"Адрес: {self.insurer_address or '—'}")
        doc.add_paragraph(f"Контактные телефоны: {self.insurer_phone or '—'}")
        doc.add_paragraph(f"Веб-сайт: {self.insurer_website or '—'}")
        doc.add_paragraph(f"Электронная почта: {self.insurer_email or '—'}")

        doc.add_paragraph(f"Номер договора страхования: {self.insurance_contract_number or '—'}")
        doc.add_paragraph(f"Срок действия договора страхования: {self.insurance_contract_expiry or '—'}")
        doc.add_paragraph(f"Страховая сумма (руб.): {self.insurance_amount or '—'} руб.")

        # Сохраняем в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Кодируем файл в base64 и создаём вложение
        attachment = self.env['ir.attachment'].create({
            'name': f'Контакт_{self.name}.docx',
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': 'res.partner',
            'res_id': self.id,
            'type': 'binary',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }