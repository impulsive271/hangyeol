/**
 * matching_quiz.js
 * 선 잇기 게임을 동적으로 실행하기 위한 모듈
 */

let quizArea, linesGroup, dragLine;
let connections = {};
let isDragging = false;
let startItem = null;
let currentQuizDataForMatching = null; // 정답 확인용 데이터

// 외부에서 이 함수를 호출하면 게임이 시작됩니다.
function initMatchingGame(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // 1. 데이터 저장
    currentQuizDataForMatching = data;
    connections = {}; // 초기화

    // 2. HTML 구조 생성 (SVG + Columns)
    container.innerHTML = `
        <div class="matching-game-container" id="game-area">
            <svg class="svg-layer">
                <g id="lines-group"></g>
                <line id="drag-line" x1="0" y1="0" x2="0" y2="0" style="display:none; stroke:#3b82f6; stroke-width:3; stroke-dasharray:5;" />
            </svg>
            <div class="column left" id="col-left"></div>
            <div class="column right" id="col-right"></div>
        </div>
        <div class="mt-3 text-center">
            <button class="secondary outline" onclick="checkMatchingAnswer()">정답 확인</button>
        </div>
        <div id="matching-feedback" class="mt-3" style="display:none; padding:15px; background:#222; border-radius:8px;"></div>
    `;

    quizArea = document.getElementById('game-area');
    linesGroup = document.getElementById('lines-group');
    dragLine = document.getElementById('drag-line');
    const leftCol = document.getElementById('col-left');
    const rightCol = document.getElementById('col-right');

    // 3. 카드 생성
    // 왼쪽 (단어)
    data.forEach(item => {
        leftCol.appendChild(createCard(item.id, item.word, 'left'));
    });

    // 오른쪽 (뜻) - 섞기
    const shuffled = [...data].sort(() => Math.random() - 0.5);
    shuffled.forEach(item => {
        rightCol.appendChild(createCard(item.id, item.meaning, 'right'));
    });

    // 4. 이벤트 리스너 등록 (Global Mouse Events)
    // 기존 리스너가 중복되지 않게 제거 후 추가
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
    
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
}

function createCard(id, text, type) {
    const card = document.createElement('div');
    card.className = `item-card ${type}`;
    card.dataset.id = id; // 정답 매칭용 ID
    card.dataset.type = type;
    
    // 카드 내용
    card.innerHTML = `
        <span class="text">${text}</span>
        <div class="dot"></div>
    `;

    // 드래그 시작 이벤트
    card.addEventListener('mousedown', onMouseDown);
    return card;
}

// --- 드래그 앤 드롭 로직 ---

function onMouseDown(e) {
    const card = e.currentTarget;
    startItem = card;
    isDragging = true;

    const startPos = getDotPos(startItem);
    dragLine.setAttribute('x1', startPos.x);
    dragLine.setAttribute('y1', startPos.y);
    dragLine.setAttribute('x2', startPos.x);
    dragLine.setAttribute('y2', startPos.y);
    dragLine.style.display = 'block';
}

function onMouseMove(e) {
    if (!isDragging || !startItem) return;
    
    // SVG 좌표계로 변환
    const rect = quizArea.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    dragLine.setAttribute('x2', x);
    dragLine.setAttribute('y2', y);
}

function onMouseUp(e) {
    if (!isDragging) return;

    const targetItem = e.target.closest('.item-card');
    
    // 유효한 연결인지 확인 (서로 다른 열이어야 함)
    if (targetItem && targetItem !== startItem) {
        const startType = startItem.dataset.type; // 'left' or 'right'
        const targetType = targetItem.dataset.type;

        if (startType !== targetType) {
            createLink(startItem, targetItem);
        }
    }

    // 초기화
    isDragging = false;
    startItem = null;
    dragLine.style.display = 'none';
}

function createLink(item1, item2) {
    // 항상 Left -> Right 기준으로 저장
    const leftItem = item1.dataset.type === 'left' ? item1 : item2;
    const rightItem = item1.dataset.type === 'left' ? item2 : item1;

    // 기존 연결 삭제 (한 단어는 하나의 뜻만)
    // 1. 왼쪽 아이템이 이미 연결된 경우
    if (connections[leftItem.dataset.id]) {
        removeLink(leftItem.dataset.id);
    }
    // 2. 오른쪽 아이템이 이미 연결된 경우 (역참조 검색)
    for (const [lId, rId] of Object.entries(connections)) {
        if (rId === rightItem.dataset.id) {
            removeLink(lId);
        }
    }

    // 데이터 저장
    connections[leftItem.dataset.id] = rightItem.dataset.id;

    // 선 그리기
    const pos1 = getDotPos(leftItem);
    const pos2 = getDotPos(rightItem);

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', pos1.x);
    line.setAttribute('y1', pos1.y);
    line.setAttribute('x2', pos2.x);
    line.setAttribute('y2', pos2.y);
    line.setAttribute('stroke', '#22c55e'); // Green
    line.setAttribute('stroke-width', '3');
    line.setAttribute('data-link-id', leftItem.dataset.id);
    linesGroup.appendChild(line);

    leftItem.classList.add('connected');
    rightItem.classList.add('connected');
}

function removeLink(leftId) {
    delete connections[leftId];
    const line = linesGroup.querySelector(`line[data-link-id="${leftId}"]`);
    if (line) line.remove();

    const leftCard = document.querySelector(`.item-card.left[data-id="${leftId}"]`);
    if (leftCard) leftCard.classList.remove('connected');
    
    // 오른쪽 카드는 상태 복잡하므로 일단 둠 (엄격하게 하려면 다시 계산 필요)
}

function getDotPos(card) {
    const dot = card.querySelector('.dot');
    const dotRect = dot.getBoundingClientRect();
    const areaRect = quizArea.getBoundingClientRect();
    return {
        x: dotRect.left + dotRect.width / 2 - areaRect.left,
        y: dotRect.top + dotRect.height / 2 - areaRect.top
    };
}

// 정답 확인 함수 (전역 호출 가능하게)
window.checkMatchingAnswer = function() {
    let correctCount = 0;
    const total = currentQuizDataForMatching.length;
    const feedbackDiv = document.getElementById('matching-feedback');
    
    // 모든 라인 초기화 (검정색 등)
    // 여기서는 간단히 결과 메시지만 출력
    
    for (const item of currentQuizDataForMatching) {
        // 내 로직상의 정답: item.id <-> item.id (ID가 같아야 정답)
        const userSelectedRightId = connections[item.id];
        if (userSelectedRightId === item.id) {
            correctCount++;
        }
    }

    feedbackDiv.style.display = 'block';
    if (correctCount === total) {
        feedbackDiv.innerHTML = `<h4 style="color:#2ecc71">🎉 완벽합니다! (${correctCount}/${total})</h4><p>모든 단어와 뜻을 바르게 연결했습니다.</p>`;
    } else {
        feedbackDiv.innerHTML = `<h4 style="color:#f1c40f">😅 조금 아쉬워요. (${correctCount}/${total})</h4><p>다시 한번 생각해 보세요!</p>`;
    }
};