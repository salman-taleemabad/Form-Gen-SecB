document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('rubric-form');
    const lessonPlanText = document.getElementById('lesson-plan-text');
    const lessonPlanFile = document.getElementById('lesson-plan-file');
    const useExampleBtn = document.getElementById('use-example');
    const generateBtn = document.getElementById('generate-btn');
    const rubricTableContainer = document.getElementById('rubric-table-container');
    const errorMessage = document.getElementById('error-message');
    const loadingSpinner = document.getElementById('loading-spinner');
    const downloadButtons = document.getElementById('download-buttons');
    const downloadCSV = document.getElementById('download-csv');
    const downloadXLSX = document.getElementById('download-xlsx');
    const downloadDOCX = document.getElementById('download-docx');
    const generateAnotherBtn = document.getElementById('generate-another');
    const generateAnotherContainer = document.getElementById('generate-another-container');
    const inputPanel = document.querySelector('.input-panel');
    const fileChosen = document.getElementById('file-chosen');

    let lastRubric = null;
    let rubricBaseFilename = 'rubric';

    // Input exclusivity logic
    lessonPlanText.addEventListener('input', function () {
        if (lessonPlanText.value.trim().length > 0) {
            lessonPlanFile.disabled = true;
            fileChosen.textContent = 'No file chosen';
        } else {
            lessonPlanFile.disabled = false;
        }
    });
    lessonPlanFile.addEventListener('change', function () {
        if (lessonPlanFile.files.length > 0) {
            lessonPlanText.disabled = true;
            fileChosen.textContent = lessonPlanFile.files[0].name;
            rubricBaseFilename = lessonPlanFile.files[0].name.replace(/\.[^/.]+$/, '');
        } else {
            lessonPlanText.disabled = false;
            fileChosen.textContent = 'No file chosen';
            rubricBaseFilename = 'rubric';
        }
    });

    useExampleBtn.addEventListener('click', async function (e) {
        e.preventDefault();
        errorMessage.textContent = '';
        lessonPlanFile.value = '';
        lessonPlanFile.disabled = true;
        lessonPlanText.disabled = false;
        try {
            const res = await fetch('/sample-lesson-plan');
            const data = await res.json();
            lessonPlanText.value = data.lesson_plan;
        } catch (err) {
            errorMessage.textContent = 'Failed to load example lesson plan.';
        }
    });

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        errorMessage.textContent = '';
        rubricTableContainer.innerHTML = '';
        loadingSpinner.style.display = 'flex';
        generateBtn.disabled = true;
        useExampleBtn.disabled = true;
        downloadButtons.style.display = 'none';
        generateAnotherContainer.style.display = 'none';
        lastRubric = null;

        const text = lessonPlanText.value.trim();
        const file = lessonPlanFile.files[0];
        let formData = new FormData();
        let format = '';

        if (file) {
            formData.append('file', file);
            formData.append('format', 'file');
            format = 'file';
        } else if (text) {
            formData.append('lesson_plan', text);
            formData.append('format', 'text');
            format = 'text';
        } else {
            errorMessage.textContent = 'Please provide a lesson plan (paste or upload).';
            loadingSpinner.style.display = 'none';
            generateBtn.disabled = false;
            useExampleBtn.disabled = false;
            return;
        }

        if (!file && text) {
            rubricBaseFilename = prompt('Enter a filename for your rubric (no extension):', 'rubric') || 'rubric';
        }

        try {
            const res = await fetch('/generate-rubric', {
                method: 'POST',
                body: formData
            });
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Failed to generate rubric.');
            }
            const rubric = await res.json();
            lastRubric = rubric;
            renderRubricTable(rubric);
            downloadButtons.style.display = 'flex';
            generateAnotherContainer.style.display = 'block';
            inputPanel.style.display = 'none';
        } catch (err) {
            errorMessage.textContent = err.message || 'Error generating rubric.';
        } finally {
            loadingSpinner.style.display = 'none';
            generateBtn.disabled = false;
            useExampleBtn.disabled = false;
        }
    });

    function renderRubricTable(rubric) {
        if (!Array.isArray(rubric) || rubric.length === 0) {
            rubricTableContainer.innerHTML = '<p>No rubric generated.</p>';
            downloadButtons.style.display = 'none';
            generateAnotherContainer.style.display = 'none';
            return;
        }
        let html = '<table id="rubric-table"><thead><tr>' +
            '<th>Code</th>' +
            '<th>Indicator Description</th>' +
            '<th>Yes</th>' +
            '<th>Partial</th>' +
            '<th>No</th>' +
            '</tr></thead><tbody>';
        for (const row of rubric) {
            html += '<tr>' +
                `<td class="code-cell">${row.code}</td>` +
                `<td>${row.indicator_description}</td>` +
                `<td>${row.yes}</td>` +
                `<td>${row.partial}</td>` +
                `<td>${row.no}</td>` +
                '</tr>';
        }
        html += '</tbody></table>';
        rubricTableContainer.innerHTML = html;
    }

    // --- Download logic ---
    downloadCSV.addEventListener('click', function () {
        if (!lastRubric) return;
        const csvRows = [
            ['Code', 'Indicator Description', 'Yes', 'Partial', 'No'],
            ...lastRubric.map(row => [row.code, row.indicator_description, row.yes, row.partial, row.no])
        ];
        const csvContent = csvRows.map(r => r.map(cell => '"' + (cell || '').replace(/"/g, '""') + '"').join(',')).join('\r\n');
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = rubricBaseFilename + '.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    downloadXLSX.addEventListener('click', function () {
        if (!lastRubric) return;
        // Use SheetJS via CDN
        if (typeof XLSX === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js';
            script.onload = () => exportXLSX();
            document.body.appendChild(script);
        } else {
            exportXLSX();
        }
        function exportXLSX() {
            const ws = XLSX.utils.json_to_sheet(lastRubric, { header: ['code', 'indicator_description', 'yes', 'partial', 'no'] });
            XLSX.utils.sheet_add_aoa(ws, [['Code', 'Indicator Description', 'Yes', 'Partial', 'No']], { origin: 'A1' });
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Rubric');
            XLSX.writeFile(wb, rubricBaseFilename + '.xlsx');
        }
    });

    downloadDOCX.addEventListener('click', function () {
        if (!lastRubric) return;
        // Simple HTML to Word using a data URI
        const table = document.getElementById('rubric-table');
        let html = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">';
        html += '<head><meta charset="utf-8"><title>Rubric</title></head><body>';
        html += '<h2>Lesson Fidelity Rubric</h2>';
        html += table.outerHTML;
        html += '</body></html>';
        const blob = new Blob([html], { type: 'application/msword' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = rubricBaseFilename + '.doc';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    // --- Generate Another Rubric logic ---
    generateAnotherBtn.addEventListener('click', function (e) {
        e.preventDefault();
        // Reset form and UI
        form.reset();
        lessonPlanText.disabled = false;
        lessonPlanFile.disabled = false;
        fileChosen.textContent = 'No file chosen';
        rubricTableContainer.innerHTML = '';
        errorMessage.textContent = '';
        downloadButtons.style.display = 'none';
        generateAnotherContainer.style.display = 'none';
        inputPanel.style.display = 'block';
        lastRubric = null;
        rubricBaseFilename = 'rubric';
    });
}); 