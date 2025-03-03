from odoo import api, models, fields
from odoo.exceptions import UserError


class EstateAccount(models.Model):
    _inherit = 'estate.property'

    partner_id = fields.Many2one(
        'res.partner', copy=False, string='Buyer',
        index=True, tracking=10
    )
    move_type = fields.Selection(
        selection=[
            ('entry', 'Journal Entry'),
            ('out_invoice', 'Customer Invoice'),
            ('out_refund', 'Customer Credit Note'),
            ('in_invoice', 'Vendor Bill'),
            ('in_refund', 'Vendor Credit Note'),
            ('out_receipt', 'Sales Receipt'),
            ('in_receipt', 'Purchase Receipt'),
        ],
        string='Type', required=True, store=True, index=True,
        readonly=True, tracking=True, default="entry", change_default=True
    )

    def _prepare_invoice_vals(self):

        if not self.partner_id:
            raise UserError("Buyer is not set. Please set a buyer before selling the property.")
        if not self.selling_price:
            raise UserError("Selling price is not set. Please set a selling price before selling the property.")

        return {
            'move_type': 'out_invoice',  # Тип счета-фактуры (исходящий)
            'partner_id': self.partner_id.id,  # Покупатель
            'invoice_line_ids': [
                # Первая строка: 6% от продажной цены
                (0, 0, {
                    'name': f'{self.name}',  # Название строки
                    'quantity': 1,  # Количество
                    'price_unit': self.selling_price * 0.06,  # Цена за единицу (6% от продажной цены)
                }),
                # Вторая строка: Административные сборы
                (0, 0, {
                    'name': 'Administrative fees',  # Название строки
                    'quantity': 1,  # Количество
                    'price_unit': 100.00,  # Фиксированная цена
                }),
            ],
        }

    def action_sold(self):

        # Вызов оригинального метода action_sold
        super(EstateAccount, self).action_sold()

        # Подготовка значений для счета-фактуры
        invoice_vals = self._prepare_invoice_vals()

        # Создание счета-фактуры
        self.env['account.move'].create(invoice_vals)

        return True