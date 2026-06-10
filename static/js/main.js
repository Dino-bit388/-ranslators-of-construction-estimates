document.addEventListener('DOMContentLoaded', function() {
    if (typeof resultsData !== 'undefined' && resultsData.length > 0) {
        const topMaterials = resultsData.slice(0, 8);
        
        const consumptionCtx = document.getElementById('consumptionChart');
        if (consumptionCtx) {
            new Chart(consumptionCtx, {
                type: 'bar',
                data: {
                    labels: topMaterials.map(m => m.subtype_name),
                    datasets: [{
                        label: 'Расход на 1 м²',
                        data: topMaterials.map(m => m.mean),
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: { callbacks: { label: function(context) { return context.raw.toFixed(3) + ' ед.'; } } }
                    },
                    scales: { y: { beginAtZero: true, title: { display: true, text: 'Расход на 1 м²' } } }
                }
            });
        }
        
        const probabilityCtx = document.getElementById('probabilityChart');
        if (probabilityCtx) {
            new Chart(probabilityCtx, {
                type: 'pie',
                data: {
                    labels: topMaterials.map(m => m.subtype_name),
                    datasets: [{
                        data: topMaterials.map(m => m.probability),
                        backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#7C4DFF']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { position: 'right', labels: { font: { size: 10 } } },
                        tooltip: { callbacks: { label: function(context) { return context.raw.toFixed(1) + '%'; } } }
                    }
                }
            });
        }
    }
    
    const alertElements = document.querySelectorAll('.alert');
    if (alertElements.length > 0) {
        setTimeout(function() {
            alertElements.forEach(function(alert) {
                const closeButton = alert.querySelector('.btn-close');
                if (closeButton) closeButton.click();
            });
        }, 5000);
    }
});