{
    "name": "Сведения о членах СРО",
    "version": "17.0.1.0.0",
    "category": "Contacts",
    "summary": "SRO Contacts",
    "author": "Asoft21",
    "website": 'https://asoft21.ru',
    "depends": [
        "hr",
        "website_blog",
        "web"
        ],
    "data": [
        "security/ir.model.access.csv",
         "views/res_partner_views.xml",
         "views/sro_contacts_work_views.xml",
         "views/sro_contacts_discipline_views.xml",
         "views/sro_contacts_inspection_views.xml",
         "views/sro_contacts_contract_views.xml",
         "views/sro_contacts_construction.xml",
         "views/hr_employee.xml",
         "views/sro_contacts_inspection_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
        ],
    },
    "application": True, 
    "license": "LGPL-3",
}



