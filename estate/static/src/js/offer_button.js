/** @odoo-module **/

import { Component } from "@odoo/owl";

export class OfferButton extends Component {
    static template = "estate_property.OfferButton";

    onClick() {
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "estate.property.offer",
            views: [[false, "list"], [false, "form"]],
            domain: [["property_type_id", "=", this.props.record.resId]],
            context: {
                default_property_type_id: this.props.record.resId,
            },
        });
    }
}