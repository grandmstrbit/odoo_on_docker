from odoo import http
from odoo.http import request

class SroAdmissionController(http.Controller):
    @http.route('/sro_admission_basis/<int:admission_id>', type='json', auth="public")
    def get_admission_basis(self, admission_id):
        admission = request.env["blog.post"].sudo().browse(admission_id)
        if admission.exists():
            return {
                "id": admission.id,
                "name": admission.name,
            }
        return None
