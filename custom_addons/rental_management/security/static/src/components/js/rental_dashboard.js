/** @odoo-module */
import { registry } from "@web/core/registry"
import { loadJS } from "@web/core/assets"
import { ChartRenderer } from "./chart_renderer/chart_renderer"
import { useService } from "@web/core/utils/hooks"
import { whenReady, mount } from "@odoo/owl";
const { Component, onWillStart, useRef, onMounted , useState } = owl

export class OwlRentalDashboard extends Component {
   //property_type
    async getPropertyType(){
        const data = await this.orm.readGroup("property.details",[],['type','name'],['type'])
        console.log(data)
        this.state.propertyType = {
            data: {
                labels: data.map(d=>d.type),
                datasets: [
                  {
                    label: 'Count',
                    data: data.map(d=>d.type_count),
                    hoverOffset: 15
                  }
                ]
            },
            label_field: 'type'
        }
    }
    // property stage
    async getPropertyStage(){
        const data = await this.orm.readGroup("property.details",[],['stage','name'],['stage'])
        this.state.propertyStage = {
            data: {
                labels: data.map(d=>d.stage),
                datasets: [
                  {
                    label: 'Count',
                    data: data.map(d=>d.stage_count),
                    hoverOffset: 15
                  }
                ]
            },
            label_field: 'stage'
        }
    }

    // broker wise tenancy
    async getBrokerTenancy(){
        const data = await this.orm.readGroup("res.partner",[['user_type','=', 'broker']],['name','type'],['name'])
        this.state.brokerTenancy = {
            data: {
                labels: data.map(d=>d.name),
                datasets: [
                  {
                    label: 'Count',
                    data: data.map(d=>d.name),
                    hoverOffset: 15
                  }
                ]
            },
            label_field: 'name'
        }
    }
    //broker wise property sold
    async getBrokerPropertySold(){
        const data = await this.orm.readGroup("property.details",[],['stage','name'],['stage'])
        this.state.brokerPropertySold = {
            data: {
                labels: data.map(d=>d.stage),
                datasets: [
                  {
                    label: 'Count',
                    data: data.map(d=>d.stage),
                    hoverOffset: 15
                  }
                ]
            },
            label_field: 'stage'
        }
    }

    // property tenancy due/paid
    async getPropertyDuePaid(){
        const data = await this.orm.readGroup("rent.invoice",[['payment_state','in',['paid','not_paid']]],['amount','payment_state'],['amount'])
        this.state.propertyDuePaid = {
            data: {
                labels: data.map(d=>d.amount),
                datasets: [
                  {
                    label: 'Count',
                    data: data.map(d=>d.amount_count),
                    hoverOffset: 15
                  }
                ]
            },
            label_field: 'amount'
        }

    }
    //property sold due/paid
    async getPropertySoldDuePaid(){
        const data = await this.orm.readGroup("property.details",[],['land_name','name'],['land_name'])
        this.state.propertySoldDuePaid = {
             data: {
                labels: data.map(d=>d.land_name),
                datasets: [
                  {
                    label: 'Count',
                    data: data.map(d=>d.land_name_count),
                    hoverOffset: 15
                  }
                ]
            },
            label_field: 'land_name'
        }
    }
    setup() {
        this.state = useState({
//        Statistics
             total:{
                property:0,
             },
             available:{
                property:0,
             },
             sold:{
                property:0,
             },
             booked:{
                property:0,
             },
             onSale:{
                property:0,
             },
             onLease:{
                property:0,
             },
//Sale Details
             totalBooked:{
                property:0,
             },
             property:{
                sold:0,
             },
             totalSold:{
                amount:0,
             },
//Tenancy Details
            draft:{
                contract:0,
            },running:{
                contract:0,
            },expired:{
                contract:0,
            },totalRent:{
                amount:0,
            },invoiceDue:{
                reminder:0,
            },

        });
        this.orm = useService("orm")
        this.actionService = useService("action");
       onWillStart(async ()=>{
        await this.getTotalProperties()
        await this.getAvailableProperties()
        await this.getSoldProperties()
        await this.getBookedProperties()
        await this.getOnSale()
        await this.getOnLease()
        await this.getTotalBooked()
        await this.getPropertySold()
        await this.getDraftContract()
        await this.getRunningContract()
        await this.getExpiredContract()
        await this.getTotalRentAmount()
        await this.getInvoiceDueReminder()
        await this.getPropertyType()
        await this.getPropertyStage()
        await this.getBrokerTenancy()
        await this.getBrokerPropertySold()
        await this.getPropertyDuePaid()
        await this.getPropertySoldDuePaid()
       })
    }
// Statistic func. and views
    async getTotalProperties(){ // total properties
        const data = await this.orm.searchCount("property.details",[['stage','in',['available','sale','sold','draft','booked','on_lease']]])
        this.state.total.property = data
    }
    viewTotalProperties(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Total Properties",
            res_model: "property.details",
            domain: [['stage','in',['available', 'sale','sold','on_lease','booked']]],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getAvailableProperties(){
        const data = await this.orm.searchCount("property.details",[['stage','in',['available']]])
        this.state.available.property = data
    }
    viewAvailableProperties(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Available Properties",
            res_model: "property.details",
            domain: [['stage','in',['available']]],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getSoldProperties(){
        const data = await this.orm.searchCount("property.details",[['stage','in',['sold']]])
        this.state.sold.property = data
    }
    viewSoldProperties(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Sold Properties",
            res_model: "property.details",
            domain: [['stage','in',['sold']]],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getBookedProperties(){
        const data = await this.orm.searchCount("property.details",[['stage','in',['booked']]])
        this.state.booked.property = data
    }
    viewBookedProperties(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Booked Properties",
            res_model: "property.details",
            domain: [['stage','in',['booked']]],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getOnSale(){
        const data = await this.orm.searchCount("property.details",[['stage','in',['sale']]])
        this.state.onSale.property = data
    }
    viewOnSaleProperties(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "On Sale Properties",
            res_model: "property.details",
            domain: [['stage','in',['sale']]],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getOnLease(){
        const data = await this.orm.searchCount("property.details",[['stage','in',['on_lease']]])
        this.state.onLease.property = data
    }
    viewOnLeaseProperties(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "On Lease Properties",
            res_model: "property.details",
            domain: [['stage','in',['on_lease']]],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
//Sale Details
    async getTotalBooked(){
        const data = await this.orm.searchCount("property.vendor",[['stage','=',['booked']]])
        this.state.totalBooked.property = data
    }
    viewTotalBookedProperties(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Total Booked Properties",
            res_model: "property.vendor",
            domain: [['stage', '=', 'booked']],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getPropertySold(){
        const data = await this.orm.searchCount("property.vendor",[['stage','in',['sold']]])
        this.state.property.sold = data
    }
    viewPropertySold(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Sold Properties",
            res_model: "property.vendor",
            domain: [['stage','in',['sold']]],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getTotalSoldAmount(){
        const data = await this.orm.searchCount("property.vendor",[['stage','in',['sold']]])
        this.state.totalSold.amount = data.map(d=>d.sale_price)
    }
    viewTotalSoldAmount(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Total Sold Amount",
            res_model: "property.vendor",
            domain: [['stage','in',['sold']]],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
//Tenancy Details
    async getDraftContract(){
        const data = await this.orm.searchCount("tenancy.details",[['contract_type','in',['new_contract']]])
        this.state.draft.contract = data
    }
    viewDraftContract(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Draft Contract",
            res_model: "tenancy.details",
            domain: [['contract_type', '=', 'new_contract']],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getRunningContract(){
        const data = await this.orm.searchCount("tenancy.details",[['contract_type','in',['running_contract']]])
        this.state.running.contract = data
    }
    viewRunningContract(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Running Contract",
            res_model: "tenancy.details",
            domain: [['contract_type', '=', 'running_contract']],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getExpiredContract(){
        const data = await this.orm.searchCount("tenancy.details",[['contract_type','in',['expire_contract']]])
        this.state.expired.contract = data
    }
    viewExpiredContract(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Expired Contract",
            res_model: "tenancy.details",
            domain: [['contract_type', '=', 'new_contract']],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getTotalRentAmount() {
        try {
            const data_1 = await this.orm.searchRead("property.vendor", [["stage", "=", "sold"]], ["sale_price"]);
            const totalSalePrice = data_1.reduce((sum, record) => sum + (record.sale_price || 0), 0);
            const data_2 = await this.orm.searchRead("rent.invoice", [["type", "=", "rent"]], ["amount"]);
            const totalRentAmount = data_2.reduce((sum, record) => sum + (record.amount || 0), 0);
            const data_3 = await this.orm.searchRead("rent.invoice", [["type", "=", "full_rent"]], ["rent_amount"]);
            const totalFullRentAmount = data_3.reduce((sum, record) => sum + (record.rent_amount || 0), 0);
            this.state.totalRent.amount = totalSalePrice + totalRentAmount + totalFullRentAmount;
        } catch (error) {
            console.error("Error fetching total rent amount:", error);
            throw error;
        }
    }
    viewTotalRentAmount(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Property Rent",
            res_model: "rent.invoice",
            domain: ['|', ['type', '=', 'rent'], ['type', '=', 'full_rent']],
            views: [[false, 'kanban'],[false, 'list'], [false, 'form']],
            context: { create: false }
        })
    }
    async getInvoiceDueReminder(){
        const data = await this.orm.searchCount("rent.invoice",[['payment_state', '=', 'not_paid']])
        this.state.invoiceDue.reminder = data
    }
    viewInvoiceDueReminder(){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Pending Invoice",
            res_model: "rent.invoice",
            domain: [['payment_state', '=', 'not_paid']],
            views: [[false, 'list'], [false, 'form'], [false, 'search']],
            context: {"search_default_landlord":1,
                        "create": false},
        })
    }
}
OwlRentalDashboard.template = "owl.OwlRentalDashboard"
OwlRentalDashboard.components = { ChartRenderer }
registry.category("actions").add("owl.rental_dashboard", OwlRentalDashboard)