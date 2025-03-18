from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero
from io import BytesIO
import base64
import io
from datetime import date, datetime
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx import Document
from docx.shared import Cm
from odoo.http import request, content_disposition
from werkzeug.wrappers import Response
from docx.oxml import OxmlElement, ns

class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Example Estate Property'
    _order = 'id desc'


class SroContactsWork(models.Model):
    _name = 'sro.contacts.work'
    _description = "sro contacts work"

    has_work_rights = fields.Boolean(string="Правом не наделен")
    
    # Сведения о наличии прав на выполнение работ
    number = fields.Char(string="№")
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

    @api.onchange('has_work_rights')
    def _onchange_has_work_rights(self):
        """Очищает поля, если галочка установлена"""
        if self.has_work_rights:
            self.update({
                'number': False,
                'right_status': False,
                'right_effective_date': False,
                'right_basis': False,
                'construction_object': False,
                'hazardous_objects': False,
                'nuclear_objects': False,
                'odo_right': 'draft',
            })

    partner2_id = fields.Many2one('res.partner', string="Выполнение работ", invisible=True)


    def action_export_work_docx(self):
        """Генерация DOCX с заголовками сверху и значениями снизу в альбомной ориентации"""
        doc = Document()

        # Делаем ориентацию альбомной
        section = doc.sections[0]
        section.page_width = Inches(11.69)  # A4 (альбомная)
        section.page_height = Inches(8.27)  # A4 (альбомная)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)

        fields_data = {
            "№": self.number or '',
            "Статус права": dict(self._fields['right_status'].selection).get(self.right_status, ''),
            "Дата вступления решения в силу": self.right_effective_date.strftime('%d.%m.%Y') if self.right_effective_date else '',
            "Основание выдачи (Документ №)": self.right_basis or '',
            "Объект капитального строительства": dict(self._fields['construction_object'].selection).get(self.construction_object, ''),
            "Особо опасные, технически сложные и уникальные объекты": dict(self._fields['hazardous_objects'].selection).get(self.hazardous_objects, ''),
            "Объекты использования атомной энергии": dict(self._fields['nuclear_objects'].selection).get(self.nuclear_objects, ''),
            "Наличие права на ОДО (Дата вступления решения в силу, Документ №)": dict(self._fields['odo_right'].selection).get(self.odo_right, ''),
        }

        # Создаём таблицу
        table = doc.add_table(rows=2, cols=len(fields_data))
        table.autofit = False  # Отключаем авторазмер, чтобы таблица заняла всю ширину страницы

        # Устанавливаем ширину колонок равномерно
        col_width = section.page_width / len(fields_data) - Inches(0.1)  # Минус небольшой отступ
        for row in table.rows:
            for cell in row.cells:
                cell.width = col_width

        # Функция для установки шрифта
        def set_font(cell, bold=False):
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    run.bold = bold

        # Заполняем первую строку (атрибуты)
        header_cells = table.rows[0].cells
        for i, field_name in enumerate(fields_data.keys()):
            header_cells[i].text = field_name
            set_font(header_cells[i], bold=True)

        # Заполняем вторую строку (значения)
        value_cells = table.rows[1].cells
        for i, field_value in enumerate(fields_data.values()):
            value_cells[i].text = field_value
            set_font(value_cells[i])

        # Сохранение в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        registration_number = self.partner2_id.registration_number or "записи"
        # Создание вложения в Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f'Наличие права на выполнение работ {registration_number}.docx',
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })

        # Возвращение ссылки на скачивание
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class SroContactsDiscipline(models.Model):
    _name = 'sro.contacts.discipline'
    _description = "sro contacts discipline"

    is_discipline = fields.Boolean(string="Сведений нет")
    discipline_message = fields.Char(compute="_compute_discipline_message", store=False)
    #Сведения о дисциплинарных производствах
    disciplinary_basis = fields.Char(string="Основание открытия дисциплинарного производства")
    disciplinary_start_date = fields.Date(string="Дата открытия дисциплинарного производства")
    disciplinary_decision = fields.Text(string="Решение дисциплинарной комиссии")
    disciplinary_decision_date = fields.Date(string="Дата решения дисциплинарной комиссии")

    @api.depends('is_discipline')
    def _compute_discipline_message(self):
        for record in self:
            record.discipline_message = "Сведений о дисциплинарных производствах нет." if record.is_discipline else ""

    @api.onchange('is_discipline')
    def _onchange_is_discipline(self):
        if self.is_discipline:
            self.update({
                'disciplinary_basis': False,
                'disciplinary_start_date': False,
                'disciplinary_decision': False,
                'disciplinary_decision_date': False,
            })
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
        doc = Document()

        fields_data = {
            "Основание открытия дисциплинарного производства": self.disciplinary_basis or '',
            "Дата открытия дисциплинарного производства": self.disciplinary_start_date.strftime('%d.%m.%Y') if self.disciplinary_start_date else '',
            "Решение Дисциплинарной комиссии": self.disciplinary_decision or '',
            "Дата решения Дисциплинарной комиссии": self.disciplinary_decision_date.strftime('%d.%m.%Y') if self.disciplinary_decision_date else '',
        }

        # Создаём таблицу
        table = doc.add_table(rows=2, cols=len(fields_data))
        table.autofit = False  # Отключаем авторазмер, чтобы таблица заняла всю ширину страницы

        # Устанавливаем ширину таблицы в процентах
        tbl = table._element
        tblPr = tbl.find(ns.qn('w:tblPr'))
        if tblPr is None:
            tblPr = OxmlElement('w:tblPr')
            tbl.append(tblPr)

        tblW = OxmlElement('w:tblW')
        tblW.set(ns.qn('w:w'), "5800")  # Максимальная ширина
        tblW.set(ns.qn('w:type'), "pct")  # В процентах
        tblPr.append(tblW)

        # Функция для установки шрифта
        def set_font(cell):
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)

        # Заполняем первую строку (атрибуты)
        header_cells = table.rows[0].cells
        for i, field_name in enumerate(fields_data.keys()):
            header_cells[i].text = field_name
            for para in header_cells[i].paragraphs:
                for run in para.runs:
                    run.bold = True  # Заголовки жирные
            set_font(header_cells[i])

        # Заполняем вторую строку (значения)
        value_cells = table.rows[1].cells
        for i, field_value in enumerate(fields_data.values()):
            value_cells[i].text = field_value
            set_font(value_cells[i])

        # Сохранение в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        registration_number = self.partner3_id.registration_number or "записи"
        # Создание вложения в Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f'Сведения о дисциплинарных взысканиях {registration_number}.docx',
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })

        # Возвращение ссылки на скачивание
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }



class SroContactsInspection(models.Model):
    _name = 'sro.contacts.inspection'
    _description = "sro contacts inspection"

    # Флаг для отображения полей проверки
    inspections_conducted = fields.Boolean(string="Проверки не проводились")

    # Сведения о результатах проведенных проверок
    inspection_member_number = fields.Selection(
        selection=lambda self: self._get_registration_numbers(),
        string="Регистрационный номер члена",
        help="Выберите регистрационный номер из списка или введите вручную."
    )
    inspection_act_date = fields.Date(string="Дата акта проверки")
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
    inspection_internal_violations = fields.Text(string="Нарушения внутренних документов и стандартов А «СО «СЧ»")
    inspection_contract_violations = fields.Text(string="Нарушение исполнения обязательств по договорам строительного подряда, заключенным с использованием конкурентных способов заключения договоров")
    inspection_result = fields.Selection([
        ('yes', 'Нарушения имеются'),
        ('no', 'Нарушений не имеется'),
        ('draft', 'Проверки не проводились'),
    ], string="Результат проверки (итог)")
    inspection_disciplinary_measures = fields.Text(string="Применение мер дисциплинарного воздействия (итог)")
    inspection_measures_list = fields.Text(string="Перечень мер дисциплинарного воздействия")

    @api.model
    def _get_registration_numbers(self):
        """Получаем список регистрационных номеров из res.partner"""
        partners = self.env['res.partner'].search([('registration_number', '!=', False)])
        return [(partner.registration_number, partner.registration_number) for partner in partners]

    @api.onchange('partner4_id')
    def _onchange_partner_id(self):
        """При выборе партнера автоматически заполняет регистрационный номер, но поле остается редактируемым"""
        if self.partner4_id:
            self.inspection_member_number = self.partner4_id.registration_number
        else:
            self.inspection_member_number = False

    @api.onchange('inspections_conducted')
    def _onchange_inspections_conducted(self):
        """Очищает поля при снятии галочки."""
        if self.inspections_conducted:
            self.update({
                'inspection_member_number': False,
                'inspection_act_date': False,
                'inspection_month_year': False,
                'inspection_type': False,
                'inspection_form': False,
                'inspection_law_violations': False,
                'inspection_internal_violations': False,
                'inspection_contract_violations': False,
                'inspection_disciplinary_measures': False,
                'inspection_measures_list': False,
                'inspection_result': 'draft',
            })
    partner4_id = fields.Many2one('res.partner')

    def action_export_inspection_docx(self):
        """Генерация DOCX с данными о результатах проверки"""
        doc = Document()
        
        fields_data = {
            "Заголовок": self.inspection_member_number or '—',
            "Дата акта проверки": self.inspection_act_date.strftime('%d.%m.%Y') if self.inspection_act_date else '—',
            "Месяц, год проверки": self.inspection_month_year or '—',
            "Перечень мер дисциплинарного воздействия": self.inspection_measures_list or '—',
            "Результат проверки": dict(self._fields['inspection_result'].selection).get(self.inspection_result, '—'),
        }
        # Создаём таблицу
        table = doc.add_table(rows=2, cols=len(fields_data))
        table.autofit = False  # Отключаем авторазмер, чтобы таблица заняла всю ширину страницы

        # Устанавливаем ширину таблицы в процентах
        tbl = table._element
        tblPr = tbl.find(ns.qn('w:tblPr'))
        if tblPr is None:
            tblPr = OxmlElement('w:tblPr')
            tbl.append(tblPr)

        tblW = OxmlElement('w:tblW')
        tblW.set(ns.qn('w:w'), "5700")  # Максимальная ширина
        tblW.set(ns.qn('w:type'), "pct")  # В процентах
        tblPr.append(tblW)

        # Функция для установки шрифта
        def set_font(cell):
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)

        # Заполняем первую строку (атрибуты)
        header_cells = table.rows[0].cells
        for i, field_name in enumerate(fields_data.keys()):
            header_cells[i].text = field_name
            for para in header_cells[i].paragraphs:
                for run in para.runs:
                    run.bold = True  # Заголовки жирные
            set_font(header_cells[i])

        # Заполняем вторую строку (значения)
        value_cells = table.rows[1].cells
        for i, field_value in enumerate(fields_data.values()):
            value_cells[i].text = field_value
            set_font(value_cells[i])

        # Сохранение в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        registration_number = self.partner4_id.registration_number or "записи"
        # Создание вложения в Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f'Сведения о результатах проведенных проверок {registration_number}.docx',
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })

        # Возвращение ссылки на скачивание
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
        ('draft', 'Преложений нет'),
    ], string="Предложение или поиск подряда")
    tender_description = fields.Text(string="Описание подряда")
    tender_contact_info = fields.Text(string="Контактные данные")
    tender_member_number = fields.Selection(
        selection=lambda self: self._get_registration_numbers(),
        string="Регистрационный номер члена",
        help="Выберите регистрационный номер из списка или введите вручную."
    )
    tender_short_name = fields.Char(string="Сокращенное наименование организации")

    @api.model
    def _get_registration_numbers(self):
        """Получаем список регистрационных номеров из res.partner"""
        partners = self.env['res.partner'].search([('registration_number', '!=', False)])
        return [(partner.registration_number, partner.registration_number) for partner in partners]

    @api.onchange('partner5_id')
    def _onchange_partner_id(self):
        """При выборе партнера автоматически заполняет регистрационный номер, но поле остается редактируемым"""
        if self.partner5_id:
            self.tender_member_number = self.partner5_id.registration_number
        else:
            self.tender_member_number = False

    @api.onchange('tender_type')
    def _onchange_tender_type(self):
        if self.tender_type == 'draft':
            self.update({
                'tender_description': False,
                'tender_contact_info': False,
                'tender_member_number': False,
                'tender_short_name': False,
            })
    partner5_id = fields.Many2one('res.partner')

    def action_export_contract_docx(self):
        """Генерация DOCX с таблицей для данных о подряде"""
        doc = Document()

        fields_data = {
            "Предложение или поиск подряда": dict(self._fields['tender_type'].selection).get(self.tender_type, '—'),
            "Описание подряда": self.tender_description or '—',
            "Контактные данные": self.tender_contact_info or '—',
            "Регистрационный номер члена": str(self.tender_member_number) if self.tender_member_number else "—",
            "Сокращённое наименование организации": str(self.tender_short_name) if self.tender_short_name else "—"
        }

        # Создаём таблицу
        table = doc.add_table(rows=2, cols=len(fields_data))
        table.autofit = False

        # Устанавливаем ширину таблицы
        tbl = table._element
        tblPr = tbl.find(ns.qn('w:tblPr'))
        if tblPr is None:
            tblPr = OxmlElement('w:tblPr')
            tbl.append(tblPr)

        tblW = OxmlElement('w:tblW')
        tblW.set(ns.qn('w:w'), "5500")  # Максимальная ширина таблицы
        tblW.set(ns.qn('w:type'), "pct")  # В процентах
        tblPr.append(tblW)

        # Функция для установки шрифта
        def set_font(cell):
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)

        # Заполняем первую строку (атрибуты)
        header_cells = table.rows[0].cells
        for i, field_name in enumerate(fields_data.keys()):
            header_cells[i].text = field_name
            for para in header_cells[i].paragraphs:
                for run in para.runs:
                    run.bold = True
            set_font(header_cells[i])

        # Заполняем вторую строку (значения)
        value_cells = table.rows[1].cells
        for i, field_value in enumerate(fields_data.values()):
            value_cells[i].text = field_value
            set_font(value_cells[i])

        # Сохранение в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        registration_number = self.partner5_id.registration_number or "записи"
        # Создание вложения в Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f'Предложение подряда {registration_number}.docx',
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })

        # Возвращение ссылки на скачивание
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class ConstructionRightSuspension(models.Model):
    _name = "sro.contacts.construction"
    _description = "sro contacts construction"

    number = fields.Char(string="№:")
    decision_date = fields.Date(string="Дата решения:")
    management_decision = fields.Selection([
        ('suspended', 'Приостановление действия права'),
        ('resumed', 'Возобновлено действия права'),
    ], string="Решение органов управления (право):")
    decision_basis = fields.Text(string="Основание решения:")

    partner6_id = fields.Many2one('res.partner')

    def action_export_construction_docx(self):
        """Генерация DOCX с таблицей для данных о приостановлении/возобновлении права"""

        doc = Document()
        section = doc.sections[0]

        fields_data = {
            "№": self.number or '—',
            "Дата решения": self.decision_date.strftime('%d.%m.%Y') if self.decision_date else '—',
            "Решение органов управления (право)": dict(self._fields['management_decision'].selection).get(self.management_decision, '—'),
            "Основание решения": self.decision_basis or '—'
        }

        # Создаём таблицу
        table = doc.add_table(rows=2, cols=len(fields_data))
        
        # Устанавливаем ширину колонок равномерно
        col_width = (section.page_width - section.left_margin - section.right_margin) / len(fields_data)
        for i, cell in enumerate(table.rows[0].cells):
            cell.width = col_width

        # Функция для установки шрифта
        def set_font(cell, bold=False):
            for para in cell.paragraphs:
                if not para.runs:
                    para.add_run()
                for run in para.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    run.bold = bold

        # Заполняем первую строку (атрибуты)
        for i, field_name in enumerate(fields_data.keys()):
            table.cell(0, i).text = field_name
            set_font(table.cell(0, i), bold=True)

        # Заполняем вторую строку (значения)
        for i, field_value in enumerate(fields_data.values()):
            table.cell(1, i).text = field_value
            set_font(table.cell(1, i))

        # Сохранение в память
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        registration_number = self.partner6_id.registration_number or "записи"
        # Создание вложения в Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f'Наличие права на выполнение работ {registration_number}.docx',
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })

        # Возвращение ссылки на скачивание
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }



class InsurerInfo(models.Model):
    _name = "insurer.info"
    _description = "insurer info"

    name = fields.Char(string="Наименование организации:")
    license_number = fields.Char(string="№ Лицензии:")
    address = fields.Text(string="Адрес:")
    phone_insurer = fields.Char(string="Контактные телефоны:")
    website = fields.Char(string="Веб-сайт:")
    email = fields.Char(string="Электронная почта:")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Регистрационные данные
    registration_number = fields.Char(string="Регистрационный номер:", index=True, unique=True)
    short_name = fields.Char(string="Сокращенное наименование организации:")
    full_name = fields.Char(string="Полное наименование организации:")
    inn = fields.Char(string="ИНН:")
    ogrn = fields.Char(string="ОГРН:")
    registration_date = fields.Date(string="Дата гос. регистрации ЮЛ/ИП:")

    # Сведения о членстве в СРО
    sro_membership_compliance = fields.Selection([
        ('active', 'Соответствует'),
        ('suspended', 'Не соответствует'),
    ], string="Сведения о соответствии члена СРО условиям членства, предусмотренным законодательством РФ и (или) внутренними документами СРО:")
    sro_membership_status = fields.Selection([
        ('active', 'Является членом'),
        ('suspended', 'Исключен'),
    ], string="Статус членства")
    sro_registration_date = fields.Date(string="Дата регистрации в реестре СРО (внесения сведений в реестр):")
    sro_admission_basis = fields.Char(string="Основание приема в СРО:") #Должна быть ссылка на документ

    show_termination_fields = fields.Boolean(
        compute="_compute_show_termination_fields", store=False)
    termination_date = fields.Date(string="Дата прекращения членства")
    termination_reason = fields.Text(string="Основание прекращения членства")
    termination_info = fields.Text(string="Сведения о прекращении членства")

    # Компенсационные фонды
    compensation_fund_vv_amount = fields.Float(string="Сумма взноса в Компенсационный Фонд возмещения вреда (КФ ВВ) (руб.):")
    vv_responsibility_level = fields.Char(string="Уровень ответственности ВВ:")
    contract_work_cost = fields.Char(string="Стоимость работ по одному договору:")
    compensation_fund_odo_amount = fields.Float(string="Сумма взноса в Компенсационный Фонд обеспечения договорных обязательств (КФ ОДО) (руб.):")
    odo_responsibility_level = fields.Char(string="Уровень ответственности ОДО:")
    max_obligation_amount = fields.Char(string="Предельный размер обязательств по договорам, заключаемым с использованием конкурентных способов заключения договоров:")

    # Руководство
    executive_authority = fields.Char(string="Единоличный исполнительный орган/руководитель коллегиального испольнительного органа:")

    # Контактные данные
    phone_sro = fields.Char(string="Контактные телефоны:")
    zip = fields.Char(string="Адрес (Индекс):")
    country_id = fields.Many2one('res.country', string="Адрес (Страна):")
    state_id = fields.Many2one('res.country.state', string="Адрес (Субъект РФ):")
    city = fields.Char(string="Адрес (Населённый пункт):")
    street = fields.Char(string="Адрес (Улица):")
    street2 = fields.Char(string="Адреc (Дом):")

    # Страхование
    insurer_info = fields.Many2one('insurer.info', string="Сведения о страховщике:") 
    
    insurer_name = fields.Char(string="Наименование организации:", related='insurer_info.name', store=True)
    insurer_license_number = fields.Char(string="№ Лицензии:", related='insurer_info.license_number', store=True)
    insurer_address = fields.Text(string="Адрес:", related='insurer_info.address', store=True)
    insurer_phone = fields.Char(string="Контактные телефоны:", store=True)
    insurer_website = fields.Char(string="Веб-сайт:", related='insurer_info.website', store=True)
    insurer_email = fields.Char(string="Электронная почта:", related='insurer_info.email', store=True)

    insurance_contract_number = fields.Char(string="Номер договора страхования:")
    insurance_contract_expiry = fields.Char(string="Срок действия договора страхования:")
    insurance_amount = fields.Float(string="Страховая сумма (руб.):")

    # Связь One2many с sro.contacts
    sro_contact2_ids = fields.One2many('sro.contacts.work', 'partner2_id', string="Наличие права на выполнение работ")
    sro_contact3_ids = fields.One2many('sro.contacts.discipline', 'partner3_id', string="Сведения о дисциплинарных производствах")
    sro_contact4_ids = fields.One2many('sro.contacts.inspection', 'partner4_id', string="Сведения о результатах проведенных проверок")
    sro_contact5_ids = fields.One2many('sro.contacts.contract', 'partner5_id', string="Предложения подрядов")
    sro_contact6_ids = fields.One2many('sro.contacts.construction', 'partner6_id', string="Сведения о приостановлении/возобновлении действия права выполнять строительсвто, реконструкцию, капиатльный ремонт объектов капитального строительства")

    @api.depends('sro_membership_status')
    def _compute_show_termination_fields(self):
        for record in self:
            record.show_termination_fields = record.sro_membership_status == 'suspended'

    def name_get(self):
        """Показывает только регистрационный номер в списке выбора"""
        result = []
        for partner in self:
            name = partner.registration_number or "Без номера"
            result.append((partner.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Поиск по регистрационному номеру"""
        args = args or []
        if name:
            partners = self.search([('registration_number', operator, name)] + args, limit=limit)
        else:
            partners = self.search(args, limit=limit)
        return partners.name_get()

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
        self.ensure_one()

        doc = Document()
        heading = doc.add_paragraph('Информация')
        run = heading.runs[0]
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)
        run.bold = True
        heading.alignment = 1  # Выравнивание по центру

        def add_info(attribute, value):
            if isinstance(value, (date, datetime)):
                value = value.strftime('%d.%m.%Y')
            elif isinstance(value, float):
                value = f"{value:,.2f}".replace(",", " ")
            elif not value:
                value = "—"

            table = doc.add_table(rows=1, cols=2)
            table.autofit = False
            table.columns[0].width = Cm(7)
            table.columns[1].width = Cm(9)
            
            row = table.rows[0].cells
            row[0].text = attribute
            row[1].text = str(value)
            
            for cell in row:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = "Times New Roman"  # Изменяем шрифт
                        run.font.size = Pt(12)  # Размер шрифта 12 pt

        # Регистрационные данные
        add_info("Регистрационный номер:", self.registration_number)
        add_info("Сокращенное наименование организации:", self.short_name)
        add_info("Полное наименование организации:", self.full_name)
        add_info("ИНН:", self.inn)
        add_info("ОГРН:", self.ogrn)
        add_info("Дата гос. регистрации ЮЛ/ИП:", self.registration_date)
        
        # Сведения о членстве в СРО
        add_info("Сведения о соответствии члена СРО условиям членства, предусмотренным законодательством РФ и (или) внутренними документами СРО:", dict(self._fields['sro_membership_compliance'].selection).get(self.sro_membership_compliance, '—'))
        add_info("Статус членства:", dict(self._fields['sro_membership_status'].selection).get(self.sro_membership_status, '—'))
        add_info("Дата регистрации в реестре СРО (внесения сведений в реестр):", self.sro_registration_date)
        add_info("Основание приема в СРО:", self.sro_admission_basis)
        
        # Компенсационные фонды
        add_info("Сумма взноса в Компенсационный Фонд возмещения вреда (КФ ВВ) (руб.):", self.compensation_fund_vv_amount)
        add_info("Уровень ответственности ВВ:", self.vv_responsibility_level)
        add_info("Стоимость работ по одному договору:", self.contract_work_cost)
        add_info("Сумма взноса в Компенсационный Фонд обеспечения договорных обязательств (КФ ОДО) (руб.):", self.compensation_fund_odo_amount)
        add_info("Уровень ответственности ОДО:", self.odo_responsibility_level)
        add_info("Предельный размер обязательств по договорам, заключаемым с использованием конкурентных способов заключения договоров:", self.max_obligation_amount)
        
        # Руководство
        add_info("Единоличный исполнительный орган/руководитель коллегиального исполнительного органа:", self.executive_authority)
        
        # Контактные данные
        add_info("Контактные телефоны:", self.phone_sro)
        add_info("Адрес (Индекс):", self.zip)
        add_info("Адрес (Страна):", self.country_id.name)
        add_info("Адрес (Субъект РФ):", self.state_id.name)
        add_info("Адрес (Населённый пункт):", self.city)
        add_info("Адрес (Улица):", self.street)
        add_info("Адрес (Дом):", self.street2)
        
        paragraph = doc.add_paragraph("\n")
        run = paragraph.add_run()  # Добавляем run вручную
        run.text = "\nСведения о страховщике:"
        run.font.name = "Times New Roman"  # Меняем шрифт
        run.font.size = Pt(12)
        run.bold = False  # Устанавливаем размер шрифта 12 pt

        # Создаем таблицу (2 колонки: атрибут и значение)
        table = doc.add_table(rows=0, cols=2)
        table.autofit = True

        def add_table_row(attribute, value):
            row_cells = table.add_row().cells
            row_cells[0].text = attribute
            row_cells[0].paragraphs[0].runs[0].bold = True
            row_cells[1].text = value if value else "—"

        add_table_row("Наименование организации:", self.insurer_name)
        add_table_row("№ Лицензии:", self.insurer_license_number)
        add_table_row("Адрес:", self.insurer_address)
        add_table_row("Контактные телефоны:", self.insurer_phone)
        add_table_row("Веб-сайт:", self.insurer_website)
        add_table_row("Электронная почта:", self.insurer_email)

        # Убираем границы у таблицы
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = "Times New Roman"
                        run.font.size = Pt(12)
                        run.bold = False 
                        paragraph.paragraph_format.space_after = Cm(0.1)  # Уменьшаем отступы

        # Добавляем заголовок "Договор страхования"
        paragraph = doc.add_paragraph("\n")

        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.bold = False

        # Создаем отдельную таблицу для договора страхования
        table_insurance = doc.add_table(rows=0, cols=2)
        table_insurance.autofit = True

        # Функция добавления строки в таблицу договора страхования
        def add_table_row_insurance(attribute, value):
            row_cells = table_insurance.add_row().cells
            row_cells[0].text = attribute
            row_cells[1].text = value if value else "—"

        # Заполняем таблицу договора страхования (без жирного шрифта)
        add_table_row_insurance("Номер договора страхования:", self.insurance_contract_number)
        add_table_row_insurance("Срок действия договора страхования:", self.insurance_contract_expiry)
        add_table_row_insurance("Страховая сумма (руб.):", f"{self.insurance_amount:,.2f}".replace(",", " "))

        # Применяем шрифт ко всей таблице договора страхования
        for row in table_insurance.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = "Times New Roman"
                        run.font.size = Pt(12)



        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': f'Данные реестра по {self.name}.docx',
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