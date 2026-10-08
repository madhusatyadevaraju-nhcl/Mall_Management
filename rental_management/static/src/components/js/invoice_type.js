/** @odoo-module */
import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart, useRef, onMounted, useState } = owl;

export class OwlInvoiceType extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.menuItems = [
          { id: 1, label: "Rent", parent: "Invoices Type" },
          { id: 2, label: "Cam", parent: "Invoices Type" },
          { id: 3, label: "Advance", parent: "Invoices Type" },
          { id: 4, label: "Marketing", parent: "Invoices Type" },
          { id: 5, label: "Electric", parent: "Invoices Type" },
          { id: 6, label: "Gas", parent: "Invoices Type" },
          { id: 7, label: "Signage", parent: "Invoices Type" },
        ];

        this.state = useState({
            selected: 1,
            selectedMonth: "All",
            months: ["All", "January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"],
            lastParent: '',
            selectedTenant: "All",
            tenants: [],
            records: [],
            recordCount: 0,
            totalRent: 0,
            totalCam: 0,
            totalAdvanced: 0,
            totalMarketing: 0,
            totalElectric: 0,
            totalGas: 0,
            totalSignage: 0,

        });

        this.getTypeFromSelected = () => {
            const typeMap = {
                1: "rent",
                2: "cam",
                3: "advanced",
                4: "marketing",
                5: "electric",
                6: "gas",
                7: "signage",
            };
            return typeMap[this.state.selected];
        };
        onWillStart(async () => {
            await this.loadDashboardData();
            await this.loadRecordsForSelectedType();
            await this.loadTenants();
        });
        this.selectMenu = this.selectMenu.bind(this);
        this.onTenantChange = this.onTenantChange.bind(this);
    }
    selectMenu(id) {
        this.state.selected = id;
        this.loadRecordsForSelectedType(); // Fetch kanban records for this selection
    }
    async onMonthChange(ev) {
        this.state.selectedMonth = ev.target.value;
        await this.loadRecordsForSelectedType(); // Let filtering be handled inside
    }
    // load the data

  async onTenantChange(ev) {
      let tid = ev.target.value;
      if (tid !== "All") {
        tid = parseInt(tid, 10);           // convert "5" → 5
      }
      this.state.selectedTenant = tid;     // now matches t.id’s type
      await this.loadRecordsForSelectedType();
  }
  async loadDashboardData() {
    try {
        const invoiceTypes = [
            "rent",
            "cam",
            "advanced",
            "marketing",
            "electric",
            "gas",
            "signage"
        ];

        // Fetch counts
        const counts = await Promise.all(
            invoiceTypes.map(type => this.getInvoiceCount([type]))
        );

        // Assign counts to state
        invoiceTypes.forEach((type, index) => {
            const key = `total${type.charAt(0).toUpperCase()}${type.slice(1)}`;
            this.state[key] = counts[index];
        });

        // Fetch actual records
        const records = await this.orm.searchRead(
            "account.move",
            [["nhcl_invoice_type", "=", "rent"]],
            ["id", "name", "state", "invoice_date", "partner_id"]
        );
        this.state.records = records;
        this.state.recordCount = records.length;

        console.log("Fetched Records:", this.state.records);

    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
  }
  async loadRecordsForSelectedType() {
  try {
    const invoiceType = this.getTypeFromSelected();
    const domain = [["nhcl_invoice_type", "=", invoiceType]];

    // Month filter (skip if “All”)
    if (this.state.selectedMonth && this.state.selectedMonth !== "All") {
      const year = new Date().getFullYear();
      const monthNames = {
        "January": 0, "February": 1, "March": 2, "April": 3, "May": 4, "June": 5, "July": 6, "August": 7, "September": 8, "October": 9, "November": 10, "December": 11
      };
      const mi = monthNames[this.state.selectedMonth];
      if (mi !== undefined) {
        const start = new Date(year, mi,   1);
        const end   = new Date(year, mi+1, 0);
        const fmt = d => d.toISOString().split("T")[0];
        domain.push(["invoice_date", ">=", fmt(start)]);
        domain.push(["invoice_date", "<=", fmt(end)]);
      }
    }

    // Tenant filter (skip if “All”)
    if (this.state.selectedTenant && this.state.selectedTenant !== "All") {
      domain.push(["partner_id", "=", parseInt(this.state.selectedTenant)]);
    }

    // Fetch and assign
    const records = await this.orm.searchRead(
      "account.move", domain, ["name", "state", "invoice_date", "partner_id"]
    );
    this.state.records = records;
    this.state.recordCount = records.length;

  } catch (error) {
    console.error("Error loading records:", error);
  }
}
  async loadTenants() {
    // Fetch partner_id from existing invoices
    const moves = await this.orm.searchRead(
      "account.move",
      [],                  // no filter, or narrow by your invoice type if you like
      ["partner_id"]
    );
    // Extract unique [id, name] pairs
    const map = new Map();
    for (const mv of moves) {
      const p = mv.partner_id;
      if (p && p.length && !map.has(p[0])) {
        map.set(p[0], p[1]);
      }
    }
    // Build state.tenants, with an "All Tenants" first
    this.state.tenants = [
      { id: "All", name: "All Tenants" },
      ...[...map.entries()].map(([id, name]) => ({ id, name })),
    ];
  }


   async getInvoiceCount(stages) {
        return this.orm.searchCount("account.move", [['nhcl_invoice_type', 'in', stages]]);
   }

// view action
    openRecord(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Invoice",
            res_model: "account.move",
            res_id: id,
            views: [[false, 'form']],
            target: "current",
        });
    }
}
OwlInvoiceType.template = "owl.OwlInvoiceType";
registry.category("actions").add("owl.invoice_type", OwlInvoiceType);