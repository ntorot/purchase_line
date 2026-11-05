/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

const buttonsBarModule = odoo.loader.modules.get('@account_reports/components/account_report/buttons_bar/buttons_bar');
const mainControllerModule = odoo.loader.modules.get('@account_reports/components/account_report/account_report');

if (buttonsBarModule && mainControllerModule) {
    
    const AccountReportButtonsBar = buttonsBarModule.AccountReportButtonsBar;
    
    patch(AccountReportButtonsBar.prototype, {
        setup() {
            super.setup(...arguments);
            
            const injectPhysicalButtons = () => {
                const container = document.querySelector(".o_control_panel_actions construction, .o_control_panel_actions .d-flex.gap-1");
                
                if (container) {
                    const actionName = (this.env?.config?.action?.name || this.env?.config?.displayName || document.title || '').toLowerCase();
                    
                    const isBalance = actionName.includes("balance de comprobación") || actionName.includes("trial balance");
                    const isMayor = actionName.includes("libro mayor") || actionName.includes("general ledger");

                    let btnDiario = document.getElementById("btn_custom_libro_diario");
                    if (isBalance) {
                        if (!btnDiario) {
                            btnDiario = document.createElement("button");
                            btnDiario.id = "btn_custom_libro_diario";
                            btnDiario.type = "button";
                            btnDiario.className = "btn btn-secondary type_custom_button ms-1";
                            btnDiario.innerText = "Libro Diario";
                            
                            btnDiario.addEventListener("click", (e) => {
                                e.preventDefault();
                                window.dispatchEvent(new CustomEvent("click_print_diario_clean"));
                            });
                            container.appendChild(btnDiario);
                        }
                    } else if (btnDiario) {
                        btnDiario.remove();
                    }

                    let btnMayor = document.getElementById("btn_custom_libro_mayor");
                    if (isMayor) {
                        if (!btnMayor) {
                            btnMayor = document.createElement("button");
                            btnMayor.id = "btn_custom_libro_mayor";
                            btnMayor.type = "button";
                            btnMayor.className = "btn btn-secondary type_custom_button ms-1";
                            btnMayor.innerText = "Libro Mayor";
                            
                            btnMayor.addEventListener("click", (e) => {
                                e.preventDefault();
                                window.dispatchEvent(new CustomEvent("click_print_mayor_clean"));
                            });
                            container.appendChild(btnMayor);
                        }
                    } else if (btnMayor) {
                        btnMayor.remove();
                    }
                }
            };

            onMounted(() => setTimeout(injectPhysicalButtons, 50));
            onPatched(() => setTimeout(injectPhysicalButtons, 50));
        }
    });

    const AccountReportAction = mainControllerModule.AccountReportAction || mainControllerModule.AccountReport;

    patch(AccountReportAction.prototype, {
        setup() {
            super.setup(...arguments);
            
            onMounted(() => {
                window.addEventListener("click_print_diario_clean", () => this.onPrintCustomPDF('purchase_line.action_report_balance_mes', 'Libro_Diario'));
                window.addEventListener("click_print_mayor_clean", () => this.onPrintCustomPDF('purchase_line.action_report_libro_mayor', 'Libro_Mayor'));
            });
        },

        async onPrintCustomPDF(actionXmlId, fileNameTitle) {
            
            const currentOptions = this.controller?.options || this.reportOptions || {};
            const reportId = this.props.action?.context?.report_id || this.props.actionContext?.report_id;

            const cleanOptions = { ...currentOptions };
            if (reportId) {
                cleanOptions['report_id'] = reportId;
            }

            const dateFrom = cleanOptions.date?.date_from || 'Reporte';

            this.env.services.action.doAction({
                type: 'ir.actions.report',
                report_name: actionXmlId === 'purchase_line.action_report_balance_mes' ? 'purchase_line.report_balance_mes_clean' : 'purchase_line.report_libro_mayor_clean',
                report_type: 'qweb-pdf',
                name: `${fileNameTitle}_${dateFrom}`,
                print_report_name: `'${fileNameTitle}_${dateFrom}'`,
                context: {
                    custom_report_options: cleanOptions,
                    active_id: reportId,
                    print_report_name: `${fileNameTitle}_${dateFrom}`
                }
            });
        }
    });
}