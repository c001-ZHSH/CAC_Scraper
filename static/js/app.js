document.addEventListener('DOMContentLoaded', () => {
    const cacUrlInput = document.getElementById('cacUrl');
    const fetchUnivBtn = document.getElementById('fetchUnivBtn');
    const urlError = document.getElementById('urlError');
    const universitySelection = document.getElementById('universitySelection');
    const univList = document.getElementById('univList');
    const selectAllCheckbox = document.getElementById('selectAll');
    const selectedCount = document.getElementById('selectedCount');
    const startScrapingBtn = document.getElementById('startScrapingBtn');
    const progressSection = document.getElementById('progressSection');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercentage = document.getElementById('progressPercentage');
    const logContainer = document.getElementById('logContainer');
    const downloadSection = document.getElementById('downloadSection');
    const downloadBtn = document.getElementById('downloadBtn');

    let universitiesData = [];
    let currentBaseUrl = '';

    // fetchUnivBtn click handler
    fetchUnivBtn.addEventListener('click', async () => {
        const url = cacUrlInput.value.trim();
        if (!url) {
            showError('請輸入有效的網址');
            return;
        }

        // Optional: Simple regex to check cac URL format loosely
        if (!url.includes('cac.edu.tw')) {
            showError('請確認輸入的是大考中心 (cac.edu.tw) 的網頁');
            return;
        }

        hideError();
        fetchUnivBtn.disabled = true;
        fetchUnivBtn.innerHTML = '<span class="spinner"></span> 正在載入...';

        try {
            const response = await fetch('/api/fetch_universities', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Server error');
            }

            universitiesData = data.universities;
            currentBaseUrl = url.substring(0, url.lastIndexOf('/') + 1);

            renderUniversityList(universitiesData);
            universitySelection.classList.remove('hidden');

            // Scroll to selection
            universitySelection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        } catch (error) {
            showError(`載入失敗: ${error.message}`);
        } finally {
            fetchUnivBtn.disabled = false;
            fetchUnivBtn.textContent = '載入大學列表';
        }
    });

    // Render checkbox list
    function renderUniversityList(univs) {
        univList.innerHTML = '';
        univs.forEach(univ => {
            const item = document.createElement('label');
            item.className = 'univ-item checkbox-container';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = univ.id;
            checkbox.dataset.url = univ.url;
            checkbox.dataset.name = univ.name;

            checkbox.addEventListener('change', updateSelectionState);

            const checkmark = document.createElement('span');
            checkmark.className = 'checkmark';

            const text = document.createTextNode(univ.name);

            item.appendChild(checkbox);
            item.appendChild(checkmark);
            item.appendChild(text);
            univList.appendChild(item);
        });

        // Reset state
        selectAllCheckbox.checked = false;
        updateSelectionState();
    }

    // Select all handler
    selectAllCheckbox.addEventListener('change', (e) => {
        const isChecked = e.target.checked;
        const checkboxes = univList.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = isChecked;
        });
        updateSelectionState();
    });

    // Update counting and button state
    function updateSelectionState() {
        const checkboxes = Array.from(univList.querySelectorAll('input[type="checkbox"]'));
        const selectedCountNum = checkboxes.filter(cb => cb.checked).length;

        selectedCount.textContent = `已選擇: ${selectedCountNum}`;

        // Update styling of parent item
        checkboxes.forEach(cb => {
            if (cb.checked) {
                cb.parentElement.classList.add('selected');
            } else {
                cb.parentElement.classList.remove('selected');
            }
        });

        // Update Select All checkbox state pseudo-three-state
        selectAllCheckbox.checked = selectedCountNum === checkboxes.length && checkboxes.length > 0;
        selectAllCheckbox.indeterminate = selectedCountNum > 0 && selectedCountNum < checkboxes.length;

        if (selectedCountNum > 0) {
            startScrapingBtn.disabled = false;
            startScrapingBtn.classList.add('pulse');
        } else {
            startScrapingBtn.disabled = true;
            startScrapingBtn.classList.remove('pulse');
        }
    }

    // Start scraping handler
    startScrapingBtn.addEventListener('click', async () => {
        const selectedCheckboxes = Array.from(univList.querySelectorAll('input[type="checkbox"]:checked'));
        const selectedUniversities = selectedCheckboxes.map(cb => ({
            id: cb.value,
            name: cb.dataset.name,
            url: cb.dataset.url
        }));

        if (selectedUniversities.length === 0) return;

        // UI Reset
        universitySelection.classList.add('hidden');
        progressSection.classList.remove('hidden');
        downloadSection.classList.add('hidden');
        logContainer.innerHTML = '';
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0%';
        progressText.textContent = '準備啟動爬蟲...';

        progressSection.scrollIntoView({ behavior: 'smooth' });

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    universities: selectedUniversities,
                    base_url: currentBaseUrl
                })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || '無法啟動爬蟲');
            }

            // This endpoint will return SSE streaming eventually if we use text/event-stream 
            // Since we used fetch(), we'll need to read the stream manually
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            handleStreamEvent(data);
                        } catch (e) {
                            console.error('JSON Parse error on SSE:', e, line);
                        }
                    }
                });
            }

        } catch (error) {
            addLog(`❌ 錯誤: ${error.message}`, 'error');
            progressText.textContent = '爬蟲啟動失敗';
        }
    });

    function handleStreamEvent(data) {
        if (data.type === 'start') {
            addLog(`啟動爬蟲，共需爬取 ${data.total} 所大學...`, 'info');
        } else if (data.type === 'progress') {
            const percent = ((data.current / data.total) * 100).toFixed(0);
            progressBar.style.width = `${percent}%`;
            progressPercentage.textContent = `${percent}%`;
            progressText.textContent = data.message;
            addLog(`⏳ ${data.message}`);
        } else if (data.type === 'complete') {
            progressBar.style.width = `100%`;
            progressPercentage.textContent = `100%`;
            progressText.textContent = '資料爬取與統整完成！';
            addLog(`✅ 所有作業完成！產出檔案中...`, 'success');

            // Setup download button
            downloadBtn.onclick = () => {
                window.location.href = data.download_url;
            };
            downloadSection.classList.remove('hidden');
            startScrapingBtn.classList.remove('pulse');
        }
    }

    function addLog(message, type = '') {
        const el = document.createElement('div');
        el.className = `log-entry ${type}`;

        // Add timestamp
        const now = new Date();
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

        el.textContent = `[${timeStr}] ${message}`;
        logContainer.appendChild(el);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    function showError(msg) {
        urlError.textContent = msg;
        urlError.classList.remove('hidden');
    }

    function hideError() {
        urlError.classList.add('hidden');
    }
});
