# 동음이의어 분석 로직 상세 (Code Walkthrough)

> **예시 문장**: "사과가 신선하지 않다니 사과할 수밖에 없을 것 같아."

이 문장이 코드를 통과하면서 어떻게 분석되는지, 실제 파일과 변수명을 기준으로 단계별로 설명합니다.

---

## 1. 후보군 조회 (Candidate Lookup)

**파일**: `services/grade_profiler.py`
**위치**: `profile()` 메서드 내부 (Line 307 ~ 315)

형태소 분석기(Kiwi)가 문장을 단어 단위로 쪼갠 후, 각 단어에 대해 데이터베이스를 조회합니다.

### 1-1. 검색 키 생성
첫 번째 "사과"를 분석할 때, 코드는 다음과 같이 검색 키를 만듭니다.
- `target`: **"사과"** (형태)
- `pos_key`: **"N"** (명사)

### 1-2. 데이터베이스 조회 (Line 311)
```python
# 실제 코드 동작
word_candidates = self.data.word_map.get(("사과", "N"), [])
```

이때 DB(`word.csv`)에서 두 개의 결과가 나옵니다. 이것이 **`candidates`** 변수가 됩니다.

| 순서 | uid | 단어 | 길잡이말(desc) | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **0** | `100` | 사과 | 과일 | (후보 1) |
| **1** | `101` | 사과 | 사과(Apology) | (후보 2) |

---

## 2. 의심 단어 등록 (Ambiguity Detection)

**파일**: `services/grade_profiler.py`
**위치**: `profile()` 메서드 내부 (Line 322 ~ 323)

후보가 2개 이상이므로, 이 단어는 **'동음이의어(Ambiguous)'**로 의심받게 됩니다.
코드는 이 단어를 `ambiguous_items` 리스트에 따로 적어둡니다.

```python
if len(candidates) > 1:
    ambiguous_items.append({
        'index': 0,          # 문장 내 위치 (첫 번째 단어)
        'word': "사과",       # 단어 형태
        'candidates': [...]  # 위에서 찾은 후보 리스트 전체
    })
```
*(두 번째 "사과"도 똑같은 과정으로 리스트에 추가됩니다. index는 다릅니다.)*

---

## 3. AI 판별 요청 (AI Disambiguation)

**파일**: `services/grade_profiler.py`
**위치**: `profile()` 메서드 하단 (Line 347 ~ 349)

**[중요] 시점**:
1. `while` 반복문을 돌며 문장의 **모든 단어(일반 단어 + 동음이의어)**에 대한 1차 분석을 끝냅니다.
   - 이때 동음이의어는 일단 **첫 번째 후보(Default)**로 임시 저장해 두고 넘어갑니다.
2. 모든 단어의 분석이 끝나면, 그때 비로소 모아둔 `ambiguous_items` 리스트를 들고 AI에게 찾아갑니다.

### 3-1. 프롬프트 작성
AI에게 보낼 질문지(`prompt`)를 만듭니다. 여기서 **`uid`**가 핵심 역할을 합니다.

> **[AI에게 보내는 질문]**
> 문맥: "사과가 신선하지 않다니 사과할 수밖에 없을 것 같아."
>
> **[분석 대상]**
> **[1]** 단어 '사과' -> 후보: `(ID:100) 과일`, `(ID:101) 사과(Apology)`
> **[2]** 단어 '사과' -> 후보: `(ID:100) 과일`, `(ID:101) 사과(Apology)`
>
> 정답인 ID만 골라서 알려줘.

### 3-2. AI의 응답 (JSON)
AI는 문맥을 읽고 다음과 같이 답장합니다.
```json
{
    "1": "100",  // 첫 번째는 과일(100)이야. ('신선하다'와 어울림)
    "2": "101"   // 두 번째는 사과(101)야. ('하다'와 어울림)
}
```

---

## 4. 최종 결과 확정 (Finalization)

**파일**: `services/grade_profiler.py`
**위치**: `profile()` 메서드 하단 (Line 363 ~ 366)

AI가 보내준 ID(`100`, `101`)를 이용해, 임시로 비워뒀던 정보를 **확정된 정보**로 교체합니다.

```python
# AI가 선택한 uid("100")와 일치하는 후보를 찾음
found = next((c for c in item['candidates'] if str(c['uid']) == "100"), None)

if found:
    # 최종 결과 업데이트
    analysis_data[target_idx]['level'] = found['level']  # "1급"
    analysis_data[target_idx]['id'] = f"단어#{found['uid']}"   # "단어#100"
    analysis_data[target_idx]['desc'] = f"🤖 {found['desc']}" # "🤖 과일"
```

### 결과
사용자는 화면에서 첫 번째 '사과'는 **'과일'**, 두 번째 '사과'는 **'용서'**라는 뜻으로 정확히 분류된 결과를 보게 됩니다.
