document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selection ---
    const appLayout = document.getElementById('app-layout');
    const uploadPrompt = document.getElementById('upload-prompt');
    const fileInput = document.getElementById('file-input');
    const chooseImageBtn = document.getElementById('choose-image-btn');
    const imageAndResultsContainer = document.getElementById('image-and-results-container');
    const imagePreview = document.getElementById('image-preview');
    const spinner = document.getElementById('spinner');
    const resultsContainer = document.getElementById('results');
    const errorContainer = document.getElementById('error-message');
    const extractedTextArea = document.getElementById('extracted-text');
    const correctedTextArea = document.getElementById('corrected-text');
    const historyListContainer = document.getElementById('history-list-container');
    const clearHistoryBtn = document.getElementById('clear-history-btn');
    const newQueryBtn = document.getElementById('new-query-btn');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    const languageSelect = document.getElementById('language-select');

    let currentImageThumbnail = null;
    let currentFile = null;

    // --- Sidebar Toggle Logic ---
    sidebarToggleBtn.addEventListener('click', () => {
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            appLayout.classList.toggle('sidebar-mobile-open');
        } else {
            appLayout.classList.toggle('sidebar-collapsed');
        }
    });

    // --- New Query Logic ---
    newQueryBtn.addEventListener('click', () => {
        fileInput.value = '';
        imageAndResultsContainer.style.display = 'none';
        errorContainer.style.display = 'none';
        uploadPrompt.style.display = 'block';
        currentImageThumbnail = null;
        currentFile = null;
        document.querySelectorAll('.history-item').forEach(li => li.classList.remove('active'));
    });

    // --- History Management ---
    const formatDateLabel = (date) => {
        const today = new Date();
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);

        if (date.toDateString() === today.toDateString()) return 'Today';
        if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
        
        return date.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
    };

    const loadHistory = () => {
        historyListContainer.innerHTML = '';
        const history = JSON.parse(localStorage.getItem('inkwizHistory')) || [];
        
        if (history.length === 0) {
            historyListContainer.innerHTML = '<div class="no-history">No history yet.</div>';
            clearHistoryBtn.style.display = 'none';
            return;
        }
        
        clearHistoryBtn.style.display = 'block';

        const groupedByDate = history.reduce((acc, item) => {
            const dateLabel = formatDateLabel(new Date(item.id));
            if (!acc[dateLabel]) {
                acc[dateLabel] = [];
            }
            acc[dateLabel].push(item);
            return acc;
        }, {});

        for (const dateLabel in groupedByDate) {
            const groupContainer = document.createElement('div');
            groupContainer.className = 'history-date-group';

            const heading = document.createElement('h3');
            heading.textContent = dateLabel;
            groupContainer.appendChild(heading);

            const list = document.createElement('ul');
            list.className = 'history-items-list';
            
            groupedByDate[dateLabel].forEach(item => {
                const li = document.createElement('li');
                li.className = 'history-item';
                li.dataset.id = item.id;

                const img = document.createElement('img');
                img.src = item.thumbnail;
                img.alt = 'History thumbnail';
                img.className = 'history-thumb';

                const detailsDiv = document.createElement('div');
                detailsDiv.className = 'history-details';

                const titleSpan = document.createElement('span');
                titleSpan.textContent = `Query`;
                titleSpan.className = 'history-title';

                const timeSpan = document.createElement('span');
                timeSpan.textContent = new Date(item.id).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                timeSpan.className = 'history-time';
                
                detailsDiv.appendChild(titleSpan);
                detailsDiv.appendChild(timeSpan);

                li.appendChild(img);
                li.appendChild(detailsDiv);
                li.addEventListener('click', () => loadHistoryItem(item.id));
                list.appendChild(li);
            });

            groupContainer.appendChild(list);
            historyListContainer.appendChild(groupContainer);
        }
    };

    const saveToHistory = (extractedText, correctedText, thumbnail) => {
        let history = JSON.parse(localStorage.getItem('inkwizHistory')) || [];
        const newEntry = {
            id: Date.now(),
            extracted_text: extractedText,
            corrected_text: correctedText,
            thumbnail: thumbnail,
        };
        history.unshift(newEntry);
        if (history.length > 30) history.pop();
        localStorage.setItem('inkwizHistory', JSON.stringify(history));
        loadHistory();
        setTimeout(() => {
            const newLi = historyListContainer.querySelector(`[data-id='${newEntry.id}']`);
            if (newLi) newLi.classList.add('active');
        }, 100);
    };

    const loadHistoryItem = (id) => {
        const history = JSON.parse(localStorage.getItem('inkwizHistory')) || [];
        const item = history.find(h => h.id == id);
        if (item) {
            uploadPrompt.style.display = 'none';
            imageAndResultsContainer.style.display = 'block';
            imagePreview.src = item.thumbnail;
            spinner.style.display = 'none';
            extractedTextArea.value = item.extracted_text;
            correctedTextArea.value = item.corrected_text;
            resultsContainer.style.display = 'grid';
            document.querySelectorAll('.history-item').forEach(li => {
                li.classList.toggle('active', li.dataset.id == id);
            });
        }
    };

    clearHistoryBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to clear all history?')) {
            localStorage.removeItem('inkwizHistory');
            loadHistory();
            newQueryBtn.click();
        }
    });

    // --- Drag and Drop & File Input Logic ---
    chooseImageBtn.addEventListener('click', () => fileInput.click());
    uploadPrompt.addEventListener('click', (e) => {
        if (e.target.id === 'upload-prompt' || e.target.closest('.upload-icon-wrapper') || e.target.closest('h2') || e.target.closest('p')) {
           fileInput.click();
        }
    });
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadPrompt.addEventListener(eventName, e => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadPrompt.addEventListener(eventName, () => uploadPrompt.classList.add('drag-over'), false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        uploadPrompt.addEventListener(eventName, () => uploadPrompt.classList.remove('drag-over'), false);
    });
    uploadPrompt.addEventListener('drop', (e) => {
        handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    function handleFiles(files) {
        if (files.length === 0) return;
        const file = files[0];

        if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
            showError('Invalid file type. Please upload a PNG, JPG, or WEBP image.');
            return;
        }
        if (file.size > 16 * 1024 * 1024) {
             showError('File is too large. Maximum size is 16MB.');
             return;
        }
        
        currentFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            currentImageThumbnail = e.target.result;
            imagePreview.src = currentImageThumbnail;
            processFile();
        };
        reader.readAsDataURL(file);
    }
    
    // --- Form Submission / Processing Logic ---
    async function processFile() {
        if (!currentFile || !currentImageThumbnail) {
            showError("Please select an image file first.");
            return;
        }
        
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('language', languageSelect.value);

        setProcessingState(true);

        try {
            const response = await fetch('/process', { method: 'POST', body: formData });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'An unknown server error occurred.');
            
            extractedTextArea.value = data.extracted_text;
            correctedTextArea.value = data.corrected_text;
            resultsContainer.style.display = 'grid';
            saveToHistory(data.extracted_text, data.corrected_text, currentImageThumbnail);

        } catch (error) {
            showError(error.message);
        } finally {
            setProcessingState(false);
        }
    }

    // --- Copy Button Logic ---
    document.body.addEventListener('click', (e) => {
        const button = e.target.closest('.copy-btn');
        if (button) {
            const targetId = button.dataset.target;
            const textArea = document.getElementById(targetId);
            navigator.clipboard.writeText(textArea.value).then(() => {
                const buttonSpan = button.querySelector('span');
                const originalText = buttonSpan.innerText;
                button.classList.add('copied');
                buttonSpan.innerText = 'Copied!';
                setTimeout(() => {
                    button.classList.remove('copied');
                    buttonSpan.innerText = originalText;
                }, 2000);
            }).catch(err => showError('Failed to copy text.'));
        }
    });

    // --- UI Helper Functions ---
    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        uploadPrompt.style.display = 'none';
        imageAndResultsContainer.style.display = 'none';
    }

    function setProcessingState(isProcessing) {
        uploadPrompt.style.display = 'none';
        imageAndResultsContainer.style.display = 'block';
        spinner.style.display = isProcessing ? 'block' : 'none';
        
        if (isProcessing) {
            resultsContainer.style.display = 'none';
            errorContainer.style.display = 'none';
            document.querySelectorAll('.history-item').forEach(li => li.classList.remove('active'));
        }
    }

    // --- Initial Load ---
    loadHistory();
});
