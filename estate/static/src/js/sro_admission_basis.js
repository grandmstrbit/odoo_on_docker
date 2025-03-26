/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { mount } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc_service";

class SroAdmissionBasis extends Component {
    static template = "estate.SroAdmissionBasis";

    setup() {
        this.state = useState({ admissionBasis: null });
        this.fetchAdmissionBasis();
    }

    async fetchAdmissionBasis() {
        const container = document.querySelector("#sro-admission-basis-container");
        if (!container) return;

        const admissionId = container.dataset.admissionId;
        if (admissionId) {
            try {
                this.state.admissionBasis = await rpc(`/sro_admission_basis/${admissionId}`);
            } catch (error) {
                console.error("Ошибка при загрузке данных:", error);
                this.state.admissionBasis = null;  // <-- Избегаем undefined
            }
        } else {
            console.warn("admissionId не найден!");
            this.state.admissionBasis = null;
        }
    }

    get admissionBasisUrl() {
        return this.state.admissionBasis
            ? `/blog/resheniia-pravleniia-3/${this.state.admissionBasis.id}`
            : null;
    }
}

// Регистрация в Odoo
import { registry } from "@web/core/registry";
registry.category("fields").add("sro_admission_basis_link", SroAdmissionBasis);

// Автоматический рендеринг
document.addEventListener("DOMContentLoaded", () => {
    const container = document.querySelector("#sro-admission-basis-container");
    if (container) {
        mount(SroAdmissionBasis, { target: container });
    }
});