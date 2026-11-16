(function () {
  if (!window.Chart) return;
  Chart.defaults.font.family = '"Inter", -apple-system, BlinkMacSystemFont, sans-serif';
  Chart.defaults.color = "#64748b";

  const labels = document.getElementById("chart-labels");
  const series = document.getElementById("chart-series");
  const statusLabels = document.getElementById("status-labels");
  const statusCounts = document.getElementById("status-counts");
  const salesCanvas = document.getElementById("salesChart");
  const statusCanvas = document.getElementById("statusChart");

  if (salesCanvas && labels && series) {
    new Chart(salesCanvas, {
      type: "line",
      data: {
        labels: JSON.parse(labels.textContent),
        datasets: [{
          label: "Revenue (₱)",
          data: JSON.parse(series.textContent),
          borderColor: "#0f766e",
          borderWidth: 2.5,
          backgroundColor: "rgba(15, 118, 110, 0.1)",
          pointRadius: 2,
          pointHoverRadius: 5,
          fill: true,
          tension: 0.32,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
          y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
        },
      },
    });
  }

  if (statusCanvas && statusLabels && statusCounts) {
    new Chart(statusCanvas, {
      type: "doughnut",
      data: {
        labels: JSON.parse(statusLabels.textContent),
        datasets: [{
          data: JSON.parse(statusCounts.textContent),
          backgroundColor: ["#0284c7", "#4f46e5", "#d97706", "#7c3aed", "#16a34a", "#dc2626"],
          borderWidth: 2,
          borderColor: "#ffffff",
        }],
      },
      options: {
        cutout: "66%",
        plugins: { legend: { position: "bottom", labels: { boxWidth: 12, padding: 14 } } },
      },
    });
  }
})();
