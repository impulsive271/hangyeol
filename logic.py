import pandas as pd
from kiwipiepy import Kiwi
import re
import unicodedata
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env 로드
load_dotenv()

class SentenceGrader:
    def __init__(self):
        self.is_ready = False
        self.error_msg = ""
        self.use_mock = False 
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model = None

        # [변경] Gemini 2.0 Flash Lite 모델 + JSON 모드 강제 설정
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(
                    "models/gemini-2.0-flash-lite-preview-02-05",
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception as e:
                print(f"⚠️ Gemini 초기화 실패: {e}")

        try:
            # 1. 파일 경로 및 로드
            base_dir = os.path.dirname(os.path.abspath(__file__))
            word_path = os.path.join(base_dir, 'word.csv')
            grammar_path = os.path.join(base_dir, 'grammar.csv')

            if not os.path.exists(word_path): raise FileNotFoundError(f"파일 없음: {word_path}")
            
            self.word_df = pd.read_csv(word_path, encoding='utf-8')
            self.grammar_df = pd.read_csv(grammar_path, encoding='utf-8')
            self.grammar_df['search_related'] = self.grammar_df['관련형'].fillna('').apply(self._parse_related_forms)

            try: self.analyzer = Kiwi()
            except Exception as e:
                print(f"⚠️ Kiwi 로드 실패: {e}")
                self.analyzer = None; self.use_mock = True

            # '이다'(#17) 데이터 미리 확보
            self.ida_entry = None
            try:
                ida_row = self.grammar_df[self.grammar_df['전체 번호'] == 17].iloc[0]
                self.ida_entry = {
                    'level': ida_row['등급'], 
                    'uid': ida_row['전체 번호'], 
                    'desc': ida_row.get('길잡이말', ''), 
                    'meaning': ida_row.get('의미', '')
                }
            except:
                self.ida_entry = {'level': '1급', 'uid': 17, 'desc': '서술격 조사', 'meaning': ''}

            # 매핑 테이블
            self.pos_map = {
                'NNG': 'N', 'NNP': 'N', 'NR': 'N', 'NP': 'N', 
                'NNB': 'NB', 
                'VV': 'V', 'VA': 'V', 'VX': 'V', 'VCP': 'V', 'VCN': 'V',
                'VV-I': 'V', 'VA-I': 'V', 'VX-I': 'V',
                'MM': 'M', 'MAG': 'MA', 'MAJ': 'MA', 'IC': 'I',
                'EC': 'EC', 'EF': 'EF', 'EP': 'EP', 'ETN': 'ET', 'ETM': 'ET',
                'JKS': 'J', 'JKC': 'J', 'JKG': 'J', 'JKO': 'J', 'JKB': 'J', 
                'JKV': 'J', 'JKQ': 'J', 'JX': 'J', 'JC': 'J'
            }

            self.friendly_pos_map = {
                'NNG': '일반 명사', 'NNP': '고유 명사', 'NNB': '의존 명사', 'NR': '수사', 'NP': '대명사',
                'VV': '동사', 'VA': '형용사', 'VX': '보조 용언', 'VCP': '긍정 지정사(이다)', 'VCN': '부정 지정사',
                'MM': '관형사', 'MAG': '일반 부사', 'MAJ': '접속 부사', 'IC': '감탄사',
                'JKS': '주격 조사', 'JKC': '보격 조사', 'JKG': '관형격 조사', 'JKO': '목적격 조사',
                'JKB': '부사격 조사', 'JKV': '호격 조사', 'JKQ': '인용격 조사', 'JX': '보조사', 'JC': '접속 조사',
                'EP': '선어말 어미', 'EF': '종결 어미', 'EC': '연결 어미', 'ETN': '명사형 전성 어미', 'ETM': '관형형 전성 어미',
                'XPN': '체언 접두사', 'XSN': '명사 파생 접미사', 'XSV': '동사 파생 접미사', 'XSA': '형용사 파생 접미사',
                'XR': '어근', 'SF': '마침표', 'SP': '쉼표', 'SS': '따옴표/괄호', 'SE': '줄임표', 'SO': '붙임표', 'SW': '기타 기호'
            }

            self._build_lookup_tables()
            self.is_ready = True
        except Exception as e:
            self.error_msg = str(e); print(f"초기화 오류: {self.error_msg}")

    def _clean_key(self, key_str):
        # 1. 문자열 변환
        key = str(key_str)
        # 2. 자모 분리 보정
        key = key.replace('ᆯ', 'ㄹ').replace('ᆫ', 'ㄴ').replace('ᆸ', 'ㅂ')
        key = key.replace('ᆷ', 'ㅁ').replace('ᆼ', 'ㅇ').replace('ᆨ', 'ㄱ')
        # 3. 기본 문장부호 제거
        key = key.replace('.', '').replace('-', '').replace('–', '').replace('~', '').replace('"', '').replace("'", '').strip()
        # 4. 사전 표기 군더더기 제거
        key = re.sub(r'[0-9]+\([0-9]+\)', '', key) # -다가1(1) -> 다가
        key = re.sub(r'\([0-9]+\)', '', key)       # (1) 제거
        key = re.sub(r'[0-9]+$', '', key)          # 끝 숫자 제거
        return unicodedata.normalize('NFKC', key).strip()

    def _parse_related_forms(self, raw_str):
        if not raw_str: return []
        clean_str = re.sub(r'<[^>]+>', ' ', str(raw_str))
        return [item.strip() for item in re.split(r'[,./]', clean_str) if item.strip()]

    def _build_lookup_tables(self):
        # 1. 단어 지도
        self.word_map = {}
        for _, row in self.word_df.fillna('').iterrows():
            pos_str = str(row['품사'])
            target_pos_keys = []
            if '의존명사' in pos_str: target_pos_keys.append('NB')
            if any(x in pos_str for x in ['명사', '대명사', '수사']) and '의존명사' not in pos_str:
                target_pos_keys.append('N')
            if any(x in pos_str for x in ['동사', '형용사']): target_pos_keys.append('V')
            if '관형사' in pos_str: target_pos_keys.append('M')
            if '부사' in pos_str: target_pos_keys.append('MA')
            if '감탄사' in pos_str: target_pos_keys.append('I')
            if not target_pos_keys: target_pos_keys.append(self.pos_map.get(pos_str, 'ETC'))

            raw_words = re.split(r'[?/]', str(row['어휘']))
            for word in raw_words:
                cleaned = self._clean_key(word)
                if cleaned:
                    data = {'level': row['등급'], 'uid': row['전체 번호'], 'desc': row['길잡이말'], 'raw_pos': row['품사'], 'is_main': True}
                    for p_key in target_pos_keys:
                        if (cleaned, p_key) not in self.word_map: self.word_map[(cleaned, p_key)] = []
                        is_duplicate = False
                        for existing in self.word_map[(cleaned, p_key)]:
                            if existing['uid'] == data['uid']:
                                is_duplicate = True; break
                        if not is_duplicate:
                            self.word_map[(cleaned, p_key)].append(data)

        # 2. 문법/표현 지도
        self.grammar_map = {}
        self.idiom_map = {} 

        def get_grammar_pos_keys(class_str):
            keys = []
            if '연결어미' in class_str: keys.append('EC')
            if '종결어미' in class_str: keys.append('EF')
            if '선어말어미' in class_str: keys.append('EP')
            if '전성어미' in class_str: keys.append('ET')
            if '조사' in class_str or '보조사' in class_str: keys.append('J')
            if '의존명사' in class_str: keys.append('NB')
            elif '명사' in class_str: keys.append('N')
            return keys

        def register_grammar(key, data_dict, is_main=True):
            if key not in self.grammar_map: self.grammar_map[key] = []
            entry = data_dict.copy()
            entry['is_main'] = is_main 
            if not any(d['uid'] == entry['uid'] for d in self.grammar_map[key]):
                self.grammar_map[key].append(entry)

        def register_idiom(raw_pattern, data_dict):
            clean_pat_str = raw_pattern.replace('-', '').replace('~', '').replace('(으)', '').strip()
            if not clean_pat_str: return
            pattern_chunks = clean_pat_str.split()
            valid_tokens = []
            try:
                for chunk in pattern_chunks:
                    res = self.analyzer.analyze(chunk)
                    tokens = res[0][0]
                    for idx, t in enumerate(tokens):
                        if chunk == pattern_chunks[-1] and idx == len(tokens) - 1 and t.form == '다' and t.tag == 'EF':
                            continue
                        valid_tokens.append(self._clean_key(t.form))
                if len(valid_tokens) >= 2:
                    start_key = valid_tokens[0]
                    rest_seq = valid_tokens[1:]
                    if start_key not in self.idiom_map: self.idiom_map[start_key] = []
                    exists = False
                    for existing in self.idiom_map[start_key]:
                        if existing['sequence'] == rest_seq and existing['data']['uid'] == data_dict['uid']:
                            exists = True; break
                    if not exists:
                        entry = data_dict.copy()
                        entry['is_main'] = True
                        self.idiom_map[start_key].append({'sequence': rest_seq, 'data': entry, 'full_text': raw_pattern})
            except: pass

        for df_source in [self.grammar_df]: 
            for _, row in df_source.fillna('').iterrows():
                data = {'level': row['등급'], 'uid': row['전체 번호'], 'desc': row.get('길잡이말', ''), 'meaning': row.get('의미', ''), 'class': str(row['분류'])}
                main_form = str(row['대표형']).strip()
                if ' ' in main_form or '표현' in data['class']: register_idiom(main_form, data)
                
                class_str = str(row['분류'])
                pos_keys = get_grammar_pos_keys(class_str)
                if '이다' in main_form and '조사' in class_str: cleaned_main = '이다'
                else: cleaned_main = self._clean_key(main_form)
                
                if cleaned_main:
                    for pk in pos_keys: register_grammar((cleaned_main, pk), data, is_main=True)
                
                for rel_form in row['search_related']:
                    if ' ' in rel_form or '표현' in data['class']: register_idiom(rel_form, data)
                    cleaned_rel = self._clean_key(rel_form)
                    if cleaned_rel:
                        for pk in pos_keys: register_grammar((cleaned_rel, pk), data, is_main=False)

        for k in self.idiom_map:
            self.idiom_map[k].sort(key=lambda x: len(x['sequence']), reverse=True)

    # -------------------------------------------------------------------------
    # [수정됨] AI 판독 요청 (JSON 포맷 강제 + 인덱스 키 사용)
    # -------------------------------------------------------------------------
    def _disambiguate_with_ai(self, sentence, ambiguous_items):
        if not self.model or not ambiguous_items: return {}, "AI 미사용"
        
        # 1. 프롬프트 구성
        prompt = f"""
        당신은 한국어 어휘 판독기입니다. 아래 문맥을 보고 동음이의어 중 가장 적절한 의미를 고르세요.
        문맥: "{sentence}"
        
        [판독 대상 목록]
        """
        for i, item in enumerate(ambiguous_items):
            options_str = ", ".join([f"(ID:{cand['uid']}) {cand['desc']}" for cand in item['candidates']])
            prompt += f"[{i}] 단어: '{item['word']}' -> 후보: [{options_str}]\n"
            
        prompt += """
        [출력 규칙]
        1. 반드시 JSON 형식으로만 응답하세요. (마크다운 없이)
        2. Key는 위 목록의 [번호]를 사용하세요. (예: "0", "1")
        3. Value는 선택한 ID 값만 넣으세요.
        4. 예시: {"0": "272", "1": "677"}
        """
        
        raw_response = ""
        try:
            response = self.model.generate_content(prompt)
            raw_response = response.text
            
            # 2. 결과 파싱 (마크다운 제거 및 JSON 변환)
            clean_json_str = raw_response.replace('```json', '').replace('```', '').strip()
            
            # 혹시 모를 trailing comma 등 사소한 오류 방지
            if clean_json_str.endswith(',') or clean_json_str.endswith(',}'): 
                 clean_json_str = clean_json_str.rstrip(',}') + "}"
                 
            ai_data = json.loads(clean_json_str)
            return ai_data, raw_response

        except Exception as e:
            error_msg = f"Error: {e} | Raw: {raw_response}"
            return {}, error_msg

    def get_sentence_grade(self, sentence: str):
        if not self.is_ready: return "판독 불가", [], "데이터 로드 실패"
        if self.use_mock or not self.analyzer: return "분석 불가", [], "Kiwi 로드 실패"
        try:
            res = self.analyzer.analyze(sentence)
            tokens = res[0][0]
        except Exception as e: return "분석 에러", [], f"Kiwi 분석 오류: {str(e)}"

        max_level = 0; analysis_data = []; debug_lines = []
        ambiguous_items = [] 
        
        debug_lines.append(f"입력: {sentence}")
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            form = token.form; tag = token.tag; form_clean = self._clean_key(form)
            
            # 0. 표현 패턴 매칭
            idiom_matched = False
            if form_clean in self.idiom_map:
                candidates = self.idiom_map[form_clean]
                for cand in candidates:
                    seq = cand['sequence']
                    if i + len(seq) >= len(tokens): continue
                    match = True
                    matched_tokens_forms = [form]
                    for offset, target_stem in enumerate(seq):
                        next_t = tokens[i + 1 + offset]
                        next_clean = self._clean_key(next_t.form)
                        if next_clean != target_stem: match = False; break
                        matched_tokens_forms.append(next_t.form)
                    
                    if match:
                        data = cand['data']
                        full_pattern_text = "+".join(matched_tokens_forms)
                        debug_lines.append(f"🧩 표현 발견: {full_pattern_text} -> {data['desc']} (#{data['uid']})")
                        level_str = data['level']
                        if level_str:
                            try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(level_str))))
                            except: pass
                        analysis_data.append({
                            "form": full_pattern_text, "tag_code": "Expression", "tag_name": "문법적 표현",
                            "level": level_str, "id": f"표현#{data['uid']}", "desc": data['desc']
                        })
                        i += (1 + len(seq))
                        idiom_matched = True; break
            if idiom_matched: continue

            # [VCP 절대 우선]
            if tag.startswith('VCP'):
                final_cand = self.ida_entry
                level_str = final_cand['level']
                debug_lines.append(f"🔒 지정사(VCP) 강제 매핑: 이다 -> {level_str} (#{final_cand['uid']})")
                if level_str:
                    try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(level_str))))
                    except: pass
                analysis_data.append({
                    "form": form, "tag_code": tag, "tag_name": self.friendly_pos_map.get(tag, tag),
                    "level": level_str, "id": f"문법#{final_cand['uid']}", "desc": final_cand['desc']
                })
                i += 1; continue 

            # 1. 단어 병합
            if i + 1 < len(tokens):
                next_token = tokens[i+1]
                curr_pos_type = self.pos_map.get(tag, 'ETC')
                next_pos_type = self.pos_map.get(next_token.tag, 'ETC')
                
                if curr_pos_type in ['N', 'NB'] and next_pos_type in ['N', 'NB']:
                    combined_form = form_clean + self._clean_key(next_token.form)
                    if (combined_form, 'N') in self.word_map:
                        merged_cands = self.word_map[(combined_form, 'N')]
                        
                        # 대표형 우선 필터링
                        main_cands = [c for c in merged_cands if c.get('is_main', False)]
                        if main_cands: merged_cands = main_cands

                        if len(merged_cands) > 1:
                            ambiguous_items.append({'index': len(analysis_data), 'word': combined_form, 'candidates': merged_cands})
                        
                        final_cand = merged_cands[0] 
                        level_str = final_cand['level']
                        debug_lines.append(f"🔄 병합 성공: {combined_form} (N) -> {level_str}")
                        if level_str:
                            try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(level_str))))
                            except: pass
                        analysis_data.append({
                            "form": combined_form, "tag_code": f"{tag}+{next_token.tag}", "tag_name": "복합어",
                            "level": level_str, "id": f"단어#{final_cand['uid']}", "desc": final_cand['desc']
                        })
                        i += 2; continue

            # 2. 단일 토큰 처리
            source_type = ""; search_key = ""; candidates = []
            pos_key = self.pos_map.get(tag, 'ETC')

            if tag in ['XSV', 'XSA'] and form_clean == '하':
                source_type = "접미사"; candidates = [{'level': '1급', 'uid': 'Sys', 'desc': '파생 접미사', 'is_main': True}]
            elif tag.startswith('J') or tag.startswith('E'):
                source_type = "문법"
                if (form_clean, pos_key) in self.grammar_map:
                    candidates = self.grammar_map[(form_clean, pos_key)]
                    search_key = f"({form_clean}, {pos_key})"
                else:
                    fallback_key = 'J' if tag.startswith('J') else 'E'
                    if (form_clean, fallback_key) in self.grammar_map:
                        candidates = self.grammar_map[(form_clean, fallback_key)]
                        search_key = f"({form_clean}, {fallback_key})"
            else:
                source_type = "단어"
                target = form_clean + '다' if pos_key == 'V' and not form_clean.endswith('다') else form_clean
                search_key = f"({target}, {pos_key})"
                word_candidates = self.word_map.get((target, pos_key), [])
                grammar_candidates = []
                if (target, pos_key) in self.grammar_map:
                    grammar_candidates = self.grammar_map[(target, pos_key)]
                candidates = word_candidates + grammar_candidates

            final_level = "-"; final_id = ""; final_desc = ""
            if candidates:
                # 대표형 우선
                main_cands = [c for c in candidates if c.get('is_main', False)]
                if main_cands: candidates = main_cands

                if len(candidates) > 1:
                     ambiguous_items.append({'index': len(analysis_data), 'word': target, 'candidates': candidates})
                
                candidates.sort(key=lambda x: x['level'])
                sel = candidates[0]
                final_level = sel['level']; final_id = sel['uid']; final_desc = sel.get('desc', '') or sel.get('meaning', '')
                debug_lines.append(f"['{form}'({tag})] -> 키:{search_key} -> 결과:{final_level} (#{final_id})")
                if final_level:
                    try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(final_level))))
                    except: pass
            else:
                debug_lines.append(f"['{form}'({tag})] -> 검색 실패 (X)")

            analysis_data.append({
                "form": form, "tag_code": tag, "tag_name": self.friendly_pos_map.get(tag, tag),
                "level": final_level, "id": f"{source_type}#{final_id}" if final_id else "-",
                "desc": final_desc
            })
            i += 1

        # ---------------------------------------------------------------------
        # [수정됨] AI 결과 반영 로직 (인덱스 or 단어 매칭)
        # ---------------------------------------------------------------------
        if ambiguous_items and self.model:
            debug_lines.append(f"🤖 AI 동음이의어 판독 시작 ({len(ambiguous_items)}건)...")
            ai_decisions, raw_log = self._disambiguate_with_ai(sentence, ambiguous_items)
            
            # [디버그] AI가 실제로 뱉은 값을 로그에 찍어 확인 (필요시 주석 해제)
            # debug_lines.append(f"📝 AI Raw: {raw_log}")

            for i, item in enumerate(ambiguous_items):
                key_idx = str(i)        # "0"
                word_key = item['word'] # "배"
                target_idx = item['index']
                
                # [핵심] 1순위: 인덱스로 찾기 / 2순위: 단어로 찾기
                selected_uid = None
                
                # 1. 인덱스 매칭 ("0": "123")
                if key_idx in ai_decisions:
                    selected_uid = str(ai_decisions[key_idx])
                
                # 2. 단어 매칭 ("배": "123") - AI가 지시 어기고 단어 썼을 때 대비
                elif word_key in ai_decisions:
                    selected_uid = str(ai_decisions[word_key])
                
                if selected_uid:
                    # 후보군 내에서 해당 UID 찾기
                    found = next((c for c in item['candidates'] if str(c['uid']) == selected_uid), None)
                    if found:
                        analysis_data[target_idx]['level'] = found['level']
                        analysis_data[target_idx]['id'] = f"단어#{found['uid']}" 
                        analysis_data[target_idx]['desc'] = f"🤖 {found['desc']}" 
                        debug_lines.append(f"✅ AI 교정 [{item['word']}]: {found['desc']} (#{selected_uid})")
                        
                        try: 
                            new_lvl = int(re.sub(r'[^0-9]', '', str(found['level'])))
                            max_level = max(max_level, new_lvl)
                        except: pass
                    else:
                        debug_lines.append(f"⚠️ ID 불일치: AI가 없는 ID({selected_uid}) 반환")
                else:
                    debug_lines.append(f"⚠️ AI 응답 누락 [{i}]: {item['word']}")

        final_grade = f"{max_level}급" if max_level > 0 else "판별 불가"
        return final_grade, analysis_data, "\n".join(debug_lines)

    # (이하 search_keyword, generate_ai_sentence 등은 기존과 동일)
    def search_keyword(self, query, search_type):
        if not query or not self.is_ready: return []
        results = []
        def normalize(text):
            if not isinstance(text, str): return ""
            return re.sub(r'[\s\-\~\(\)\[\]\.\?\/ㆍ]', '', text)
        try:
            if search_type == "word":
                norm_query = normalize(query)
                mask = self.word_df['어휘'].astype(str).apply(normalize).str.contains(norm_query, na=False)
                df = self.word_df[mask].head(10)
                for _, row in df.fillna('').iterrows():
                    results.append({"text": row['어휘'], "grade": row['등급'], "desc": str(row['길잡이말']), "pos": row['품사'], "meaning": ""})
            else:
                norm_query = normalize(query)
                search_candidates = {norm_query}
                target_endings = ['다', '는', '은', 'ㄴ', '을', 'ㄹ', '요', '죠', '니', '면']
                if len(norm_query) >= 2:
                    for end in target_endings:
                        if norm_query.endswith(end):
                            stem = norm_query[:-len(end)]
                            if len(stem) > 0: search_candidates.add(stem)
                            break 
                def check_match(row_text):
                    if not row_text: return False
                    norm_target = normalize(str(row_text)) 
                    for candidate in search_candidates:
                        if candidate in norm_target: return True
                    norm_target_stem = norm_target
                    if norm_target.endswith('다'): norm_target_stem = norm_target[:-1]
                    for candidate in search_candidates:
                        if len(norm_target_stem) >= 2 and norm_target_stem in candidate: return True
                    return False
                main_mask = self.grammar_df['대표형'].apply(check_match)
                related_mask = self.grammar_df['search_related'].apply(lambda items: any(check_match(item) for item in items))
                final_mask = main_mask | related_mask
                df = self.grammar_df[final_mask].head(10)
                for _, row in df.fillna('').iterrows():
                    results.append({"text": row['대표형'], "grade": row['등급'], "desc": str(row.get('길잡이말', '')), "pos": row['분류'], "related": ", ".join(row['search_related']), "meaning": str(row.get('의미', ''))})
        except Exception as e: print(f"검색 오류: {e}")
        return results

    def generate_ai_sentence(self, model, grades, keyword, hint=""):
        prompt = "한국어 교육 전문가입니다.\n다음 조건에 맞춰 학습용 예문을 단 하나만 작성하세요.\n"
        if grades:
            valid = [int(g) for g in grades if g.isdigit()] if "all" not in grades else []
            prompt += f"- 난이도: TOPIK {max(valid)}급 수준\n" if valid else "- 난이도: 초~고급 자연스럽게\n"
        if keyword:
            hint_str = f" (문맥 힌트: {hint})" if hint and hint != 'nan' else ""
            prompt += f"- 필수 포함 단어: '{keyword}'{hint_str}\n  * 주의: 반드시 포함할 것.\n"
        prompt += "\n[출력 제약사항]\n1. 설명 금지, 오직 예문 1개만 출력.\n2. 마크다운 사용 금지.\n3. 반드시 마침표로 끝낼 것."
        try:
            return model.generate_content(prompt).text.strip().replace("**", "").replace('"', "")
        except Exception as e: return f"오류: {str(e)}"

    # 인자(argument)에 user_prompt="" 추가
    def generate_quiz_item(self, model, target, level, quiz_type, context_sentence, user_prompt=""):
        type_desc = "양자택일(Binary Choice)" if quiz_type == 'binary' else "4지선다(Multiple Choice)"
        
        # [NEW] 사용자 요청이 있을 경우 프롬프트에 추가할 텍스트
        custom_instruction = ""
        if user_prompt:
            custom_instruction = f"\n[사용자 특별 요청사항]: {user_prompt} (이 요청을 최우선으로 반영할 것)\n"

        if context_sentence:
            clean_target = target.split(' (')[0] if '(' in target else target
            prompt = f"""당신은 한국어 선생님입니다.
원문: "{context_sentence}"
정답: "{clean_target}"
유형: {type_desc}
난이도: {level}급
{custom_instruction}
지시: 정답을 빈칸(____)으로 만들고 퀴즈 생성.
출력 포맷(JSON): {{"question_text": "...", "options": ["..."], "answer_index": 0, "explanation": "..."}}"""
        else:
            prompt = f"""한국어 문제 출제자입니다.
단어: '{target}' 활용
난이도: {level}급
유형: {type_desc}
{custom_instruction}
지시: 위 조건을 만족하는 문제 생성.
출력 포맷(JSON): {{"question_text": "...", "options": ["..."], "answer_index": 0, "explanation": "..."}}"""
            
        try:
            return json.loads(model.generate_content(prompt).text.strip().replace("```json", "").replace("```", ""))
        except Exception as e: return {"error": "AI 생성 실패", "details": str(e)}