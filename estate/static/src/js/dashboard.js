/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class EstateDashboard extends Component {
    static template = "estate_property.EstateDashboard";

    setup() {
        this.state = useState({
            totalProperties: 0,
            totalOffers: 0,
            averagePrice: 0,
        });

        // Загрузите данные для дашборда
        this.loadData();
    }

    async loadData() {
        try {
            const data = await this.env.services.rpc({
                model: "estate.property",
                method: "get_dashboard_data",
            });

            // Обновите состояние
            this.state.totalProperties = data.total_properties;
            this.state.totalOffers = data.total_offers;
            this.state.averagePrice = data.average_price;
        } catch (error) {
            console.error("Ошибка при загрузке данных:", error);
        }
    }
}

// Регистрация действия
registry.category("actions").add("action_estate_dashboard", EstateDashboard);