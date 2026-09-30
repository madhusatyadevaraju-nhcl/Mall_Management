/** @odoo-module **/

import { session } from '@web/session';
import { formatFloatTime } from '@web/views/fields/formatters';
import { formatFloat } from "@web/core/utils/numbers";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
//import { jsonrpc } from "@web/core/network/rpc_service";
import { rpc } from "@web/core/network/rpc";

import {
    renderToElement
} from "@web/core/utils/render";


export class TemplateDashboard extends Component {
    setup() {
//        this.action = useService('action');
        this.actionService = useService("action");
        this.orm = useService('orm');
        this.state = useState({
            dashboardValues: null,
        });
        this.url=[]
        this.value = "aaaaa"

        onWillStart(this.onWillStart);
    }

        async onWillStart() {
        const { errorData } = this.props;
        this.url.push(1)
        this.url.push(2)
        this.url.push(3)
        this.url.push(4)

          this.values = await this.orm.call("axis.helpdesk.ticket.team", "filter_stage_data_dashboard", [], {});

    }
    onDashboardActionClicked()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,kanban',
            view_type: 'list',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form']],

            domain: [['helpdesk_stage_id.is_close','=',false]],
            target: 'current'
            })

    }

     onDashboardActionClickedInprogress()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,kanban',
            view_type: 'list',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form']],

            domain: [['helpdesk_stage_id.name','=','In Progress']],
            target: 'current'
            })

    }

    onDashboardActionClickedSolved()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,kanban',
            view_type: 'list',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form']],

            domain: [['helpdesk_stage_id.name','=','Solved']],
            target: 'current'
            })

    }
    onDashboardActionClickedClosed()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'axis.helpdesk.ticket',
            view_mode: 'tree,kanban',
            view_type: 'list',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form']],

            domain: [['helpdesk_stage_id.is_close','=',true]],
            target: 'current'
            })

    }

    onChangeTeamLead(el) {

    var teamElement = document.querySelector('.o_team');
    var assignUserElement = document.querySelector('.o_assign');
    var dateElement = document.querySelector('#date_filter');

    var team_id = teamElement.value;
    console.log("\n\n element", team_id)

    var assignUser_id = assignUserElement.value;
    var date_id = dateElement.value;

    var datepicker = document.querySelector('.datepicker');
    if (date_id == 9) {
        datepicker.style.display = "flex"; // Use style to change display
    } else {
        datepicker.style.display = "none";
    }

    // Make the RPC call
    rpc('/getData', {
        'team_id': team_id,
        'assignUser_id': assignUser_id,
        'date_id': date_id,
    }).then(function(data) {
        console.log("RESULTTTTTTTTTTTTTTTTTTTTTTTTTT", data);
        var result = data;
        document.getElementById("tbody_new").innerHTML = ''; // Clear existing content

        var not_update_stage = null; // Initialize not_update_stage
        for (const ticket of result['ticket_ids']) {
            var stage = ticket['helpdesk_stage_id'];
            if (not_update_stage !== stage) {
                var stageRow = `<tr><td colspan='6' style='background-color:#27c2b4; font-weight:bold; border: 1px solid #27c2b4'>${stage}</td></tr>`;
                document.getElementById("tbody_new").insertAdjacentHTML('beforeend', stageRow);

                var html_header = `<tr style='background-color:#deeaff; font-weight:bold; border: 1px solid #27c2b4; border-right: 1px solid #dbd3d3;'><td><b>Ticket No</b></td><td><b>Customer Name</b></td><td><b>Create Date</b></td><td><b>Last Update Date</b></td><td><b>Assign User</b></td><td><b>Stage</b></td></tr>`;
                document.getElementById("tbody_new").insertAdjacentHTML('beforeend', html_header);
            }
            not_update_stage = stage;
            // Create a new row for the ticket
            var html = `<tr style='border-right: 1px solid #dbd3d3;'><td style='border-right: 1px solid #dbd3d3;'>${ticket['number']}</td><td style='border-right: 1px solid #dbd3d3;'>${ticket['partner_id']}</td><td style='border-right: 1px solid #dbd3d3;'>${ticket['create_date']}</td><td style='border-right: 1px solid #dbd3d3;'>${ticket['write_date']}</td><td style='border-right: 1px solid #dbd3d3;'>${ticket['res_user_id']}</td><td style='border-right: 1px solid #dbd3d3;'>${ticket['helpdesk_stage_id']}</td></tr>`;
            document.getElementById("tbody_new").insertAdjacentHTML('beforeend', html);
        }
    });
}

}

TemplateDashboard.components = {
    ...KanbanRenderer.components,

};
TemplateDashboard.template = 'website_axis_helpdesk_advance.TemplateDashboard';


