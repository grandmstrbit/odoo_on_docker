{
    "name": "Real Estate",
    "author": "Asoft21 gang hold-on-bang",
    "license": "LGPL-3",
    "category": "Real Estate",
    "summary": "No gletcher gang 2 0 2 5",
    "application": True, 
    "depends": [],
    "data": [
        "security/ir.model.access.csv",

        "views/estate_property_views.xml",
        "views/estate_property_type_views.xml",
        "views/estate_property_tags_views.xml",
        "views/estate_property_offer_views.xml",
        "views/res_users_views.xml",

        "views/estate_property_menu.xml",
        "views/estate_property_type_menu.xml",
        "views/estate_property_tags_menu.xml",

        #"views/assets.xml",
        
        
    ],
    "assets": {
        "web.assets_backend": [
            "estate/static/src/js/offer_button.js",
            "estate/static/src/js/offer_button_registry.js",
                       
            
            "estate/static/src/js/dashboard.js",
            "estate/static/src/js/dashboard_registry.js",
            
            "estate/static/src/xml/offer_button.xml",
            "estate/static/src/xml/dashboard.xml",

            "estate/static/src/css/dashboard.css", 
        ]
    }
}