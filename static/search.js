/**
 * 검색 기능을 초기화하는 모듈
 */
function initSearchModule(onItemClick) {
    const searchInput = document.getElementById('common-search-input');
    const typeSelect = document.getElementById('common-search-type');
    const resultsArea = document.getElementById('common-search-results');

    if (!searchInput || !resultsArea) return;

    searchInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') e.preventDefault();
    });

    document.addEventListener('click', function (e) {
        if (!searchInput.contains(e.target) && !resultsArea.contains(e.target)) {
            resultsArea.innerHTML = '';
            resultsArea.style.display = 'none';
        }
    });

    let debounceTimer; // 디바운싱 타이머 변수

    searchInput.addEventListener('input', function () {
        const query = this.value.trim();
        const type = typeSelect.value;

        // 입력이 없으면 즉시 결과창 닫기 (디바운싱 취소)
        if (query.length < 1) {
            clearTimeout(debounceTimer);
            resultsArea.innerHTML = '';
            resultsArea.style.display = 'none';
            return;
        }

        // 이전 타이머 취소 (연속 입력 시 API 요청 지연)
        clearTimeout(debounceTimer);

        // 300ms 후에 API 요청 실행
        debounceTimer = setTimeout(() => {
            fetch(`/api/search?q=${encodeURIComponent(query)}&type=${type}`)
                .then(res => res.json())
                .then(data => {
                    resultsArea.innerHTML = '';

                    if (data.length > 0) {
                        resultsArea.style.display = 'block';

                        data.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'search-result-item';

                            // 1. 힌트(길잡이말) 처리
                            const hintText = (item.desc && item.desc !== 'nan')
                                ? `<span style="color:#aaa; font-size:0.85em; margin-left:6px;">${item.desc}</span>`
                                : '';

                            // 2. 품사(POS) 처리
                            const posText = item.pos
                                ? `<span style="color:#a855f7; font-weight:600; font-size:0.85em; margin-left:4px;">[${item.pos}]</span>`
                                : '';

                            // 3. [NEW] 관련형 매칭 정보 처리 (예: "가" 검색 시 -> "관련형: 가")
                            let relatedText = '';
                            if (item.related) {
                                relatedText = `<span style="color:#ff9f43; font-size:0.8em; margin-left:6px;">(관련형: ${item.related})</span>`;
                            }

                            // 4. 렌더링 (대표색 불투명 적용)
                            const gradeNum = item.grade.replace(/[^0-9]/g, '');

                            // 색상 매핑 (Solid Colors)
                            // 1: #10b981 (Green), 2: #3b82f6 (Blue), 3: #8b5cf6 (Purple)
                            // 4: #f59e0b (Yellow), 5: #ef4444 (Red), 6: #64748b (Slate)
                            const colorMap = {
                                '1': '#10b981',
                                '2': '#3b82f6',
                                '3': '#8b5cf6',
                                '4': '#f59e0b',
                                '5': '#ef4444',
                                '6': '#64748b'
                            };
                            const bgColor = colorMap[gradeNum] || '#94a3b8';

                            div.innerHTML = `
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div style="text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                        <strong>${item.text}</strong>
                                        ${posText}
                                        ${relatedText}
                                        ${hintText}
                                    </div>
                                    <span style="font-size:0.75em; color:#fff; background:${bgColor}; padding: 2px 6px; border-radius:4px; white-space: nowrap; margin-left: 10px;">
                                        ${item.grade}
                                    </span>
                                </div>
                            `;

                            div.addEventListener('click', function () {
                                onItemClick(item);
                            });

                            resultsArea.appendChild(div);
                        });
                    } else {
                        resultsArea.style.display = 'block';
                        resultsArea.innerHTML = '<div class="search-result-item" style="color:#888; text-align:center;">검색 결과가 없습니다.</div>';
                    }
                })
                .catch(err => console.error('검색 실패:', err));
        }, 300); // 300ms Delay
    });
}