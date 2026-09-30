/** @odoo-module */
import { registry } from "@web/core/registry"
import { loadJS } from "@web/core/assets"
const { Component, onWillStart, useRef, onMounted } = owl

export class ChartRenderer extends Component {
    setup(){
        this.chartRef = useRef("chart")
        onWillStart(async ()=>{
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
        })

        onMounted(()=>this.renderChart())
    }
    renderChart(){
        new Chart(this.chartRef.el,
        {
          type: this.props.type,
          data: this.props.config.data,

          options: {
            layout: {
              padding: {
                left: 35, // Adds padding to the left, moving the chart to the right
              }
            },
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                  position: 'bottom', // Places the legend at the bottom
                  padding: {
                    top: 20 // Adds padding to the left, moving the chart to the right
                  }
              },
              title: {
                display: true,
                text: this.props.title,
                position: 'bottom',
              }
            },
          },
        }
      );
    }
}

ChartRenderer.template = "owl.ChartRenderer"