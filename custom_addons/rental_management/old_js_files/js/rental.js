/**@odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from  "@odoo/owl";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
const actionRegistry = registry.category("actions");

 export class ActionMenu extends Component {
     setup() {
            this.rpc = useService("rpc");
        }

     async fetchData() {
        const result = await this.rpc("/property/details/get_stats");
        this.updateDashboard(result);
    }

    updateDashboard(data) {
        document.querySelector("#avail-property").textContent = data.view_avail_property;
        document.querySelector("#total-property").textContent = data.view_total_property;
        document.querySelector("#booked-property").textContent = data.view_booked_property;
        document.querySelector("#lease-property").textContent = data.view_lease_stats;
        document.querySelector("#sale-property").textContent = data.view_sale_stats;
        document.querySelector("#sold-property").textContent = data.view_sold_stats;
        document.querySelector("#sold-total").textContent = data.view_property_sold;
        document.querySelector("#draft-contract").textContent = data.view_draft_rent;
        document.querySelector("#running-contract").textContent = data.view_running_rent;
        document.querySelector("#expire-contract").textContent = data.view_expire_rent;
        document.querySelector("#booked-property-sale").textContent = data.view_booked_sale;
        document.querySelector("#sale-sold").textContent = data.view_sale_sold;
        document.querySelector("#pending-invoice").textContent = data.view_pending_invoice;
    }
//  const ActionMenu = AbstractAction.extend({
//    template: 'rentalDashboard',
//    renderElement: function (ev) {
//      const self = this;
//      $.when(this._super())
//        .then(function (ev) {
//          rpc.query({
//            model: "property.details",
//            method: "get_property_stats",
//          }).then(function (result) {
//            $('#avail_property').empty().append(result['avail_property']);
//            $('#booked_property').empty().append(result['booked_property']);
//            $('#lease_property').empty().append(result['lease_property']);
//            $('#sale_property').empty().append(result['sale_property']);
//            $('#sold_property').empty().append(result['sold_property']);
//            $('#total_property').empty().append(result['total_property']);
//            $('#sold_total').empty().append(result['sold_total']);
//            $('#rent_total').empty().append(result['rent_total']);
//            $('#draft_contract').empty().append(result['draft_contract']);
//            $('#running_contract').empty().append(result['running_contract']);
//            $('#expire_contract').empty().append(result['expire_contract']);
//            $('#booked').empty().append(result['booked']);
//            $('#sale_sold').empty().append(result['sale_sold']);
//            $('#pending_invoice').empty().append(result['pending_invoice']);
//            self.propertyType(result['property_type']);
//            self.propertyStages(result['property_stage']);
//            self.topBrokers(result['tenancy_top_broker']);
//            self.topBrokersSold(result['tenancy_top_broker']);
//            self.tenancyDuePaid(result['due_paid_amount']);
//            self.soldDuePaid(result['due_paid_amount']);
//          });
//        });
//    },
    view_avail_property: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Available Property'),
        type: 'ir.actions.act_window',
        res_model: 'property.details',
        domain: [['stage', '=', 'available']],
        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_total_property: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Total Property'),
        type: 'ir.actions.act_window',
        res_model: 'property.details',
        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_booked_property: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Booked Property'),
        type: 'ir.actions.act_window',
        res_model: 'property.details',
        domain: [['stage', '=', 'booked']],
        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_lease_stats: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Property On Lease'),
        type: 'ir.actions.act_window',
        res_model: 'property.details',
        domain: [['stage', '=', 'on_lease']],
        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_sale_stats: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Property On Sale'),
        type: 'ir.actions.act_window',
        res_model: 'property.details',
        domain: [['stage', '=', 'sale']],
        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_sold_stats: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Sold Property'),
        type: 'ir.actions.act_window',
        res_model: 'property.details',
        domain: [['stage', '=', 'sold']],
        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_property_sold: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Property Sold'),
        type: 'ir.actions.act_window',
        res_model: 'property.vendor',
        domain: [['stage', '=', 'sold']],
        views: [[false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_property_rent: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Property Rent'),
        type: 'ir.actions.act_window',
        res_model: 'rent.invoice',
        domain: ['|', ['type', '=', 'rent'], ['type', '=', 'full_rent']],
        views: [[false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_draft_rent: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Draft Contract'),
        type: 'ir.actions.act_window',
        res_model: 'tenancy.details',
        domain: [['contract_type', '=', 'new_contract']],
        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_running_rent: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Running Contract'),
        type: 'ir.actions.act_window',
        res_model: 'tenancy.details',
        domain: [['contract_type', '=', 'running_contract']],
        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_expire_rent: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Expire Contract'),
        type: 'ir.actions.act_window',
        res_model: 'tenancy.details',
        domain: [['contract_type', '=', 'expire_contract']],
        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_booked_sale: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Booked Property'),
        type: 'ir.actions.act_window',
        res_model: 'property.vendor',
        domain: [['stage', '=', 'booked']],
        views: [[false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
    view_sale_sold: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Sold Property'),
        type: 'ir.actions.act_window',
        res_model: 'property.vendor',
        domain: [['stage', '=', 'sold']],
        views: [[false, 'list'], [false, 'form']],
        target: 'current'
      });
    },
     view_pending_invoice: function (ev) {
      ev.preventDefault();
      return this.do_action({
        name: _t('Pending Invoice'),
        type: 'ir.actions.act_window',
        res_model: 'rent.invoice',
        domain: [['payment_state', '=', 'not_paid']],
        views: [[false, 'list'], [false, 'form'], [false, 'search']],
        context:{'search_default_landlord':1},
        target: 'current'
      });
    },
    get_action: function (ev, name, res_model) {
      ev.preventDefault();
      return this.do_action({
        name: _t(name),
        type: 'ir.actions.act_window',
        res_model: res_model,
        views: [[false, 'kanban'], [false, 'tree'], [false, 'form']],
        target: 'current'
      });
    },
    apexGraph: function () {
      Apex.grid = {
        padding: {
          right: 0,
          left: 0,
          top: 10,
        }
      }
      Apex.dataLabels = {
        enabled: false
      }
    },
    //Graph
    propertyType: function (data) {
      const options = {
        series: data[1],
        chart: {
          type: 'donut',
          height: 410
        },
        colors: ['#33679c', '#6FFCD0', '#F084A3', '#82CDFF'],
        dataLabels: {
          enabled: false
        },
        labels: data['0'],
        legend: {
          position: 'bottom',
        },
      };
      this.renderGraph("#property_type", options);
    },
    propertyStages: function (data) {
      const options = {
        series: data[1],
        chart: {
          type: 'pie',
          height: 410
        },
        colors: ['#FFADAD', '#FFD6A5', '#FDFFB6', '#CAFFBF', '9BF6FF'],
        dataLabels: {
          enabled: false
        },
        labels: data[0],
        legend: {
          position: 'bottom',
        },

      };
      this.renderGraph("#property_stages", options);
    },
    topBrokers: function (data) {
      var options = {
        series: [{
          name: "Tenancies",
          data: data[1],
        }],
        chart: {
          height: 350,
          type: 'bar',
        },
        colors: ['#FFADAD', '#FFD6A5', '#FDFFB6', '#CAFFBF', '9BF6FF'],
        plotOptions: {
          bar: {
            columnWidth: '45%',
            distributed: true,
          }
        },
        dataLabels: {
          enabled: false
        },
        legend: {
          show: false
        },
        xaxis: {
          categories: data[0],
          labels: {
            style: {
              fontSize: '12px'
            }
          }
        }
      };
      this.renderGraph("#top_brokers", options);
    },
    topBrokersSold: function (data) {
      var options = {
        series: [{
          name: "Property Sale",
          data: data[3],
        }],
        chart: {
          height: 350,
          type: 'bar',
        },
        colors: ['#FFADAD', '#FFD6A5', '#FDFFB6', '#CAFFBF', '9BF6FF'],
        plotOptions: {
          bar: {
            columnWidth: '45%',
            distributed: true,
          }
        },
        dataLabels: {
          enabled: false
        },
        legend: {
          show: false
        },
        xaxis: {
          categories: data[2],
          labels: {
            style: {
              fontSize: '12px'
            }
          }
        }
      };
      this.renderGraph("#top_brokers_sale", options);
    },
    tenancyDuePaid: function (data) {
      const options = {
        series: data[3],
        chart: {
          type: 'pie',
          height: 410
        },
        colors: ['#FF6464', '#96BB7C'],
        dataLabels: {
          enabled: false
        },
        labels: data[2],
        legend: {
          position: 'bottom',
        },
      };
      this.renderGraph("#tenancy_due_paid", options);
    },
    soldDuePaid: function (data) {
      const options = {
        series: data[1],
        chart: {
          type: 'pie',
          height: 410
        },
        colors: ['#FF1700', '#4AA96C'],
        dataLabels: {
          enabled: false
        },
        labels: data[0],
        legend: {
          position: 'bottom',
        },
      };
      this.renderGraph("#sold_due_paid", options);
    },
    renderGraph: function (render_id, options) {
      $(render_id).empty();
      const graphData = new ApexCharts(document.querySelector(render_id), options);
      graphData.render();
    },
    willStart: function () {
       const self = this;
            return this._super()
            .then(function() {});
        },
//  });
//  actionRegistry.add("property_dashboard", ActionMenu);
}
ActionMenu.template = "rental_management.rentalDashboard";
actionRegistry.add("cmr_dashboard_tag", ActionMenu);
