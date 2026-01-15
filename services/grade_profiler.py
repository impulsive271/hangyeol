import re
import json
from services.grade_database import GradeDatabase

class GradeProfiler:
    def __init__(self, data_service: GradeDatabase):
        self.data = data_service
        self.debug_lines = []

    def _disambiguate_with_ai(self, client, model_name, sentence, ambiguous_items):
        if not client or not ambiguous_items: return {}, "AI 미사용"
        
        prompt = f"""
        당신은 한국어 어휘 분석기입니다. 아래 문맥을 보고 동음이의어 중 가장 적절한 의미를 고르세요.
        문맥: "{sentence}"
        
        [분석 대상 목록]
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
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            raw_response = response.text
            
            clean_json_str = raw_response.replace('```json', '').replace('```', '').strip()
            if clean_json_str.endswith(',') or clean_json_str.endswith(',}'): 
                 clean_json_str = clean_json_str.rstrip(',}') + "}"
                 
            ai_data = json.loads(clean_json_str)
            return ai_data, raw_response

        except Exception as e:
            error_msg = f"Error: {e} | Raw: {raw_response}"
            return {}, error_msg

    def profile(self, tokens, sentence, client=None, model_name=None):
        """
        형태소 분석 결과(tokens)를 바탕으로 등급을 프로파일링합니다.
        :param tokens: Kiwi 형태소 분석 결과 (Token 객체 리스트 or dict 리스트)
        :param sentence: 원문 문장 (AI 문맥 파악용)
        :param client: val (동음이의어 처리용)
        :param model_name: str
        :return: analysis_data (list), max_level (int), debug_log (str)
        """
        self.debug_lines = []
        max_level = 0
        analysis_data = []
        ambiguous_items = []
        
        self.debug_lines.append(f"입력: {sentence}")
        
        i = 0
        while i < len(tokens):
            # Token 객체인지 dict인지 확인 (유연성)
            token = tokens[i]
            form = token.form if hasattr(token, 'form') else token['form']
            tag = token.tag if hasattr(token, 'tag') else token['tag']
            
            # 위치 정보 (없을 수도 있음)
            t_start = getattr(token, 'start', 0)
            t_len = getattr(token, 'len', 0)

            form_clean = self.data.clean_key(form)
            
            # 0. 표현 패턴 매칭
            idiom_matched = False
            if form_clean in self.data.idiom_map:
                candidates = self.data.idiom_map[form_clean]
                for cand in candidates:
                    seq = cand['sequence']
                    if i + len(seq) >= len(tokens): continue
                    match = True
                    matched_tokens_forms = [form]
                    for offset, target_stem in enumerate(seq):
                        next_t = tokens[i + 1 + offset]
                        next_form = next_t.form if hasattr(next_t, 'form') else next_t['form']
                        next_clean = self.data.clean_key(next_form)
                        if next_clean != target_stem: match = False; break
                        matched_tokens_forms.append(next_form)
                    
                    if match:
                        data = cand['data']
                        full_pattern_text = "+".join(matched_tokens_forms)
                        self.debug_lines.append(f"🧩 표현 발견: {full_pattern_text} -> {data['desc']} (#{data['uid']})")
                        level_str = data['level']
                        if level_str:
                            try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(level_str))))
                            except: pass
                        
                        last_t = tokens[i + len(seq)]
                        # 길이 계산 주의 (Token 객체일 때만 정확)
                        full_len = 0
                        if hasattr(last_t, 'start'):
                            full_len = (last_t.start + last_t.len) - t_start

                        analysis_data.append({
                            "form": full_pattern_text, "tag_code": "Expression", "tag_name": "문법적 표현",
                            "level": level_str, "id": f"표현#{data['uid']}", "desc": data['desc'],
                            "offset_start": t_start, "offset_len": full_len
                        })
                        i += (1 + len(seq))
                        idiom_matched = True; break
            if idiom_matched: continue

            # [VCP 절대 우선]
            if tag.startswith('VCP'):
                final_cand = self.data.ida_entry
                level_str = final_cand['level']
                self.debug_lines.append(f"🔒 지정사(VCP) 강제 매핑: 이다 -> {level_str} (#{final_cand['uid']})")
                if level_str:
                    try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(level_str))))
                    except: pass
                analysis_data.append({
                    "form": form, "tag_code": tag, "tag_name": self.data.friendly_pos_map.get(tag, tag),
                    "level": level_str, "id": f"문법#{final_cand['uid']}", "desc": final_cand['desc'],
                    "offset_start": t_start, "offset_len": t_len
                })
                i += 1; continue 

            # 1. 단어 병합 (2-gram Lookahead)
            if i + 1 < len(tokens):
                next_token = tokens[i+1]
                next_form = next_token.form if hasattr(next_token, 'form') else next_token['form']
                next_tag = next_token.tag if hasattr(next_token, 'tag') else next_token['tag']

                combined_form = form_clean + self.data.clean_key(next_form)
                
                # 병합 시도: (합친단어, 'N') 또는 (합친단어, 'V') 등으로 데이터 조회
                # 우선순위: 명사(N) -> 동사(V) -> 기타
                merge_found = False
                matched_candidate = None
                matched_pos_type = ''

                # [전략] 합친 형태가 데이터베이스 'N'(명사) 혹은 'V'(동사) 등에 존재하는지 확인
                # 예: 선생(NNG) + 님(XSN) -> 선생님(N) 존재 확인
                pos_priorities = ['N', 'NB', 'V', 'M', 'MA', 'I']
                
                for p_key in pos_priorities:
                    # 1. 원형 (그대로) 검색
                    lookup_keys = [combined_form]
                    
                    # 2. 동사/표현 등인 경우 '다' 붙여서 검색 (어지 -> 어지다)
                    if p_key in ['V', 'ETC']: 
                         if not combined_form.endswith('다'):
                             lookup_keys.append(combined_form + '다')

                    for key_var in lookup_keys:

                        # [FIX] word_map과 grammar_map 모두 조회
                        # '어지다' 같은 문법적 표현이나 동사는 grammar_map에 'V' 키로 있을 수 있음
                        candidates = []
                        if (key_var, p_key) in self.data.word_map:
                            candidates.extend(self.data.word_map[(key_var, p_key)])
                        if (key_var, p_key) in self.data.grammar_map:
                            candidates.extend(self.data.grammar_map[(key_var, p_key)])

                        main_cands = [c for c in candidates if c.get('is_main', False)]
                        if main_cands: candidates = main_cands
                        
                        if candidates:
                                # 병합 성공
                                matched_candidate = candidates[0]
                                matched_pos_type = p_key
                                
                                # 만약 '다'를 붙여서 찾았다면, 형태도 그에 맞추거나 메모
                                # 여기서는 combined_form 자체는 합친 텍스트 그대로 두고,
                                # desc나 id는 찾은 '어지다'의 것을 사용함.
                                
                                if len(candidates) > 1:
                                    ambiguous_items.append({
                                        'index': len(analysis_data), 
                                        'word': key_var, 
                                        'candidates': candidates
                                    })
                                merge_found = True
                                break
                    if merge_found: break
                
                # '하다' 파생 용언의 경우 추가 처리 (어근 병합 로직 유지)
                if not merge_found:
                    is_root_merge = (tag == 'XR' and next_tag in ['XSA', 'XSV', 'XSA-I', 'XSV-I'])
                    if is_root_merge:
                         combined_form_v = combined_form + '다'
                         if (combined_form_v, 'V') in self.data.word_map:
                             candidates = self.data.word_map[(combined_form_v, 'V')]
                             if candidates:
                                 matched_candidate = candidates[0]
                                 matched_pos_type = 'V'
                                 combined_form = combined_form_v # 폼 업데이트
                                 merge_found = True

                if merge_found and matched_candidate:
                    level_str = matched_candidate['level']
                    self.debug_lines.append(f"🔄 2-gram 병합 성공: {form}+{next_form} -> {combined_form} ({matched_pos_type}) -> {level_str}")
                    
                    if level_str:
                        try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(level_str))))
                        except: pass
                    
                    # 길이 계산
                    next_len = getattr(next_token, 'len', 0)
                    next_start = getattr(next_token, 'start', 0)
                    calc_len = (next_start + next_len) - t_start if next_start > 0 else 0

                    # [NEW] 품사 명칭 동적 결정
                    pos_label = "복합어/파생어"
                    if 'class' in matched_candidate:
                        # 문법 DB 유래
                        cls_val = matched_candidate['class']
                        if '표현' in cls_val: pos_label = "문법적 표현"
                        else: pos_label = cls_val
                    elif 'raw_pos' in matched_candidate:
                        # 단어 DB 유래
                        pos_label = matched_candidate['raw_pos']

                    analysis_data.append({
                        "form": combined_form,
                        "tag_code": f"{tag}+{next_tag}",
                        "tag_name": pos_label,
                        "level": level_str,
                        "id": f"단어#{matched_candidate['uid']}",
                        "desc": matched_candidate['desc'],
                        "offset_start": t_start,
                        "offset_len": calc_len
                    })
                    i += 2; continue

            # 2. 단일 토큰 처리
            source_type = ""; search_key = ""; candidates = []
            pos_key = self.data.pos_map.get(tag, 'ETC')
            # [FIX] 기본값 초기화
            target = form_clean 

            if tag in ['XSV', 'XSA'] and form_clean == '하':
                source_type = "단어"; candidates = [{'level': '2급', 'uid': '1769', 'desc': '건강하다', 'is_main': True}]
            elif tag in ['EF'] and form_clean == '다':
                source_type = "문법"; candidates = [{'level': '3급', 'uid': '120', 'desc': '', 'is_main': True}]
            elif tag.startswith('J') or tag.startswith('E'):
                source_type = "문법"
                if (form_clean, pos_key) in self.data.grammar_map:
                    candidates = self.data.grammar_map[(form_clean, pos_key)]
                    search_key = f"({form_clean}, {pos_key})"
                else:
                    fallback_key = 'J' if tag.startswith('J') else 'E'
                    if (form_clean, fallback_key) in self.data.grammar_map:
                        candidates = self.data.grammar_map[(form_clean, fallback_key)]
                        search_key = f"({form_clean}, {fallback_key})"
            else:
                source_type = "단어"
                target = form_clean + '다' if pos_key == 'V' and not form_clean.endswith('다') else form_clean
                search_key = f"({target}, {pos_key})"
                word_candidates = self.data.word_map.get((target, pos_key), [])
                grammar_candidates = []
                if (target, pos_key) in self.data.grammar_map:
                    grammar_candidates = self.data.grammar_map[(target, pos_key)]
                candidates = word_candidates + grammar_candidates

            final_level = "-"; final_id = ""; final_desc = ""
            if candidates:
                main_cands = [c for c in candidates if c.get('is_main', False)]
                if main_cands: candidates = main_cands

                if len(candidates) > 1:
                     ambiguous_items.append({'index': len(analysis_data), 'word': target, 'candidates': candidates})
                
                candidates.sort(key=lambda x: x['level'])
                sel = candidates[0]
                final_level = sel['level']; final_id = sel['uid']; final_desc = sel.get('desc', '') or sel.get('meaning', '')
                self.debug_lines.append(f"['{form}'({tag})] -> 키:{search_key} -> 결과:{final_level} (#{final_id})")
                if final_level:
                    try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(final_level))))
                    except: pass
            else:
                self.debug_lines.append(f"['{form}'({tag})] -> 검색 실패 (X)")

            analysis_data.append({
                "form": form, "tag_code": tag, "tag_name": self.data.friendly_pos_map.get(tag, tag),
                "level": final_level, "id": f"{source_type}#{final_id}" if final_id else "-",
                "desc": final_desc,
                "offset_start": t_start, "offset_len": t_len
            })
            i += 1
            
        # AI 결과 반영 (동음이의어 분석)
        if ambiguous_items and client:
            self.debug_lines.append(f"🤖 AI 동음이의어 분석 시작 ({len(ambiguous_items)}건)...")
            ai_decisions, raw_log = self._disambiguate_with_ai(client, model_name, sentence, ambiguous_items)
            
            for i, item in enumerate(ambiguous_items):
                key_idx = str(i)
                word_key = item['word']
                target_idx = item['index']
                selected_uid = None
                
                if key_idx in ai_decisions:
                    selected_uid = str(ai_decisions[key_idx])
                elif word_key in ai_decisions:
                    selected_uid = str(ai_decisions[word_key])
                
                if selected_uid:
                    found = next((c for c in item['candidates'] if str(c['uid']) == selected_uid), None)
                    if found:
                        analysis_data[target_idx]['level'] = found['level']
                        analysis_data[target_idx]['id'] = f"단어#{found['uid']}" 
                        analysis_data[target_idx]['desc'] = f"🤖 {found['desc']}" 
                        self.debug_lines.append(f"✅ AI 교정 [{item['word']}]: {found['desc']} (#{selected_uid})")
                        try: 
                            new_lvl = int(re.sub(r'[^0-9]', '', str(found['level'])))
                            max_level = max(max_level, new_lvl)
                        except: pass
                    else:
                        self.debug_lines.append(f"⚠️ ID 불일치: AI가 없는 ID({selected_uid}) 반환")
                else:
                    self.debug_lines.append(f"⚠️ AI 응답 누락 [{i}]: {item['word']}")

        return analysis_data, max_level, "\n".join(self.debug_lines)
