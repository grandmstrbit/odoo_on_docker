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

    partner2_id = fields.Many2one('res.partner', string="Выполнение работ", invisible=True)


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

    def format_date(date_value):
        """Преобразует дату в формат DD.MM.YY"""
        if not date_value:
            return '—'
        if isinstance(date_value, str):  # Если строка, парсим
            date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
        elif isinstance(date_value, datetime):  # Если datetime, берем только дату
            date_value = date_value.date()
        elif not isinstance(date_value, date):  # Если это не date, значит что-то не так
            return '—'
        return date_value.strftime('%d.%m.%Y')

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
    inspection_act_date = fields.Char(string="Дата акта проверки")
    inspection_month_year = fields.Char(string="Месяц, год проверки")
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
    ], string="Результат проверки (итог)", default='draft')
    inspection_disciplinary_measures = fields.Text(string="Применение мер дисциплинарного воздействия (итог)")
    inspection_measures_list = fields.Text(string="Перечень мер дисциплинарного воздействия")

    show_inspection_fields = fields.Boolean(string="Показывать поля проверки", compute="_compute_show_inspection_fields", store=True)

    @api.onchange('inspection_result')
    def _compute_show_inspection_fields(self):
        for record in self:
            record.show_inspection_fields = record.inspection_result != 'draft'

    @api.onchange('inspection_result')
    def _onchange_inspection_result(self):
        """Очищаем ненужные поля при выборе 'Проверки не проводились'"""
        if self.inspection_result == 'draft':
            self.inspection_member_number = False
            self.inspection_act_date = False
            self.inspection_month_year = False
            self.inspection_type = False
            self.inspection_form = False
            self.inspection_law_violations = False
            self.inspection_internal_violations = False
            self.inspection_contract_violations = False
            self.inspection_disciplinary_measures = False
            self.inspection_measures_list = False

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
    phone_insurer = fields.Char(string="Контактные телефоны", store=True)
    website = fields.Char(string="Веб-сайт")
    email = fields.Char(string="Электронная почта")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Регистрационные данные
    registration_number = fields.Char(string="Регистрационный номер")
    short_name = fields.Char(string="Сокращенное наименование организации")
    full_name = fields.Char(string="Полное наименование организации")
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
    street2 = fields.Char(string="Адреc (Дом)")

    # Страхование
    insurer_info = fields.Many2one('insurer.info', string="Сведения о страховщике") #СОЗДАТЬ МОДЕЛЬ с атрибутами, сделать связи one2many 
    
    insurer_name = fields.Char(string="Наименование организации", related='insurer_info.name', store=True)
    insurer_license_number = fields.Char(string="№ Лицензии", related='insurer_info.license_number', store=True)
    insurer_address = fields.Text(string="Адрес", related='insurer_info.address', store=True)
    insurer_phone = fields.Char(string="Контактные телефоны", store=True)
    insurer_website = fields.Char(string="Веб-сайт", related='insurer_info.website', store=True)
    insurer_email = fields.Char(string="Электронная почта", related='insurer_info.email', store=True)

    insurance_contract_number = fields.Char(string="Номер договора страхования")
    insurance_contract_expiry = fields.Char(string="Срок действия договора страхования")
    insurance_amount = fields.Float(string="Страховая сумма (руб.)")

    # Связь One2many с sro.contacts
    #sro_contact_ids = fields.One2many('sro.contacts', 'partner_id', string="Сведения о членах СРО")
    sro_contact2_ids = fields.One2many('sro.contacts.work', 'partner2_id', string="Наличие права на выполнение работ")
    sro_contact3_ids = fields.One2many('sro.contacts.discipline', 'partner3_id', string="Сведения о дисциплинарных производствах")
    sro_contact4_ids = fields.One2many('sro.contacts.inspection', 'partner4_id', string="Сведения о результатах проведенных проверок")
    sro_contact5_ids = fields.One2many('sro.contacts.contract', 'partner5_id', string="Предложения подрядов")

    def format_date(date_value):
        """Преобразует дату в формат DD.MM.YY"""
        if not date_value:
            return '—'
        if isinstance(date_value, str):  # Если строка, парсим
            date_value = datetime.strptime(date_value, '%y-%m-%d').date()
        elif isinstance(date_value, datetime):  # Если datetime, берем только дату
            date_value = date_value.date()
        elif not isinstance(date_value, date):  # Если это не date, значит что-то не так
            return '—'
        return date_value.strftime('%d.%m.%y')

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
