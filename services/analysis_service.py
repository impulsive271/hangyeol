import re
import json
import google.generativeai as genai
from config import Config
from services.morph_service import MorphService
from services.data_service import DataService

class AnalysisService:
    def __init__(self):
        self.morph = MorphService()
        self.data = DataService()
        self.model = None
        self._init_ai()
    
    def _init_ai(self):
        api_key = Config.GOOGLE_API_KEY
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(
                    "models/gemini-2.0-flash-lite-preview-02-05",
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception as e:
                print(f"⚠️ AnalysisService AI Init Failed: {e}")

    def _disambiguate_with_ai(self, sentence, ambiguous_items):
        if not self.model or not ambiguous_items: return {}, "AI 미사용"
        
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
            
            clean_json_str = raw_response.replace('```json', '').replace('```', '').strip()
            if clean_json_str.endswith(',') or clean_json_str.endswith(',}'): 
                 clean_json_str = clean_json_str.rstrip(',}') + "}"
                 
            ai_data = json.loads(clean_json_str)
            return ai_data, raw_response

        except Exception as e:
            error_msg = f"Error: {e} | Raw: {raw_response}"
            return {}, error_msg

    def get_sentence_grade(self, sentence: str):
        if not self.data.is_ready: return "판독 불가", [], "데이터 로드 실패"
        if self.morph.use_mock or not self.morph.analyzer: return "분석 불가", [], "Kiwi 로드 실패"
        
        try:
            res = self.morph.analyze(sentence)
            tokens = res[0][0]
        except Exception as e: return "분석 에러", [], f"Kiwi 분석 오류: {str(e)}"

        max_level = 0; analysis_data = []; debug_lines = []
        ambiguous_items = [] 
        
        debug_lines.append(f"입력: {sentence}")
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            form = token.form; tag = token.tag; form_clean = self.data.clean_key(form)
            
            t_start = token.start
            t_len = token.len
            
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
                        next_clean = self.data.clean_key(next_t.form)
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
                        
                        last_t = tokens[i + len(seq)]
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
                debug_lines.append(f"🔒 지정사(VCP) 강제 매핑: 이다 -> {level_str} (#{final_cand['uid']})")
                if level_str:
                    try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(level_str))))
                    except: pass
                analysis_data.append({
                    "form": form, "tag_code": tag, "tag_name": self.data.friendly_pos_map.get(tag, tag),
                    "level": level_str, "id": f"문법#{final_cand['uid']}", "desc": final_cand['desc'],
                    "offset_start": t_start, "offset_len": t_len
                })
                i += 1; continue 

            # 1. 단어 병합
            if i + 1 < len(tokens):
                next_token = tokens[i+1]
                curr_pos_type = self.data.pos_map.get(tag, 'ETC')
                next_pos_type = self.data.pos_map.get(next_token.tag, 'ETC')
                
                is_noun_merge = (curr_pos_type in ['N', 'NB'] and next_pos_type in ['N', 'NB'])
                is_root_merge = (tag == 'XR' and next_token.tag in ['XSA', 'XSV', 'XSA-I', 'XSV-I'])

                if is_noun_merge or is_root_merge:
                    suffix = '다' if is_root_merge else ''
                    combined_form = form_clean + self.data.clean_key(next_token.form) + suffix
                    target_pos = 'V' if is_root_merge else 'N'
                    
                    if (combined_form, target_pos) in self.data.word_map:
                        merged_cands = self.data.word_map[(combined_form, target_pos)]
                        
                        main_cands = [c for c in merged_cands if c.get('is_main', False)]
                        if main_cands: merged_cands = main_cands

                        if len(merged_cands) > 1:
                            ambiguous_items.append({'index': len(analysis_data), 'word': combined_form, 'candidates': merged_cands})
                        
                        final_cand = merged_cands[0] 
                        level_str = final_cand['level']
                        debug_lines.append(f"🔄 병합 성공: {combined_form} ({target_pos}) -> {level_str}")
                        if level_str:
                            try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(level_str))))
                            except: pass
                        
                        pos_label = "동사/형용사(파생)" if is_root_merge else "복합어"
                        
                        analysis_data.append({
                            "form": combined_form, "tag_code": f"{tag}+{next_token.tag}", "tag_name": pos_label,
                            "level": level_str, "id": f"단어#{final_cand['uid']}", "desc": final_cand['desc'],
                            "offset_start": t_start, "offset_len": (next_token.start + next_token.len) - t_start
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
                debug_lines.append(f"['{form}'({tag})] -> 키:{search_key} -> 결과:{final_level} (#{final_id})")
                if final_level:
                    try: max_level = max(max_level, int(re.sub(r'[^0-9]', '', str(final_level))))
                    except: pass
            else:
                debug_lines.append(f"['{form}'({tag})] -> 검색 실패 (X)")

            analysis_data.append({
                "form": form, "tag_code": tag, "tag_name": self.data.friendly_pos_map.get(tag, tag),
                "level": final_level, "id": f"{source_type}#{final_id}" if final_id else "-",
                "desc": final_desc,
                "offset_start": t_start, "offset_len": t_len
            })
            i += 1

        # AI 결과 반영
        if ambiguous_items and self.model:
            debug_lines.append(f"🤖 AI 동음이의어 판독 시작 ({len(ambiguous_items)}건)...")
            ai_decisions, raw_log = self._disambiguate_with_ai(sentence, ambiguous_items)
            
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

    def analyze_morphs(self, sentence):
        if not self.morph.analyzer: return []
        res = self.morph.analyze(sentence)
        tokens = res[0][0]
        return [{'form': t.form, 'tag': t.tag} for t in tokens]

    def get_visualization_data(self, analysis_result, sentence):
        grade_counts = {f"{i}급": 0 for i in range(1, 7)}
        text_segments = []
        
        for item in analysis_result:
            lvl = item.get('level', '')
            if '급' in lvl:
                full_lvl_str = re.sub(r'[^0-9]', '', lvl)
                if full_lvl_str and f"{full_lvl_str}급" in grade_counts:
                    grade_counts[f"{full_lvl_str}급"] += 1

        visualization_data = {
            "labels": [k for k, v in grade_counts.items() if v > 0],
            "data": [v for v in grade_counts.values() if v > 0]
        }
        
        for i, item in enumerate(analysis_result):
            item['_ui_id'] = f"seg-{i}-{item.get('offset_start', 0)}"
        
        sorted_analysis = sorted(analysis_result, key=lambda x: x.get('offset_start', -1))
        current_cursor = 0
        
        for item in sorted_analysis:
            start = item.get('offset_start')
            length = item.get('offset_len')
            
            if start is None or length is None: continue
            
            if start > current_cursor:
                text_segments.append({
                    "text": sentence[current_cursor:start],
                    "type": "plain"
                })
            
            grade_class = "text-grade-none"
            lvl = item.get('level', '')
            if '급' in lvl:
                num = re.sub(r'[^0-9]', '', lvl)
                if num: grade_class = f"text-grade-{num}"
            
            text_segments.append({
                "text": item['form'],
                "type": "graded",
                "class": grade_class,
                "info": item 
            })
            
            current_cursor = max(current_cursor, start + length)
            
        if current_cursor < len(sentence):
            text_segments.append({
                "text": sentence[current_cursor:],
                "type": "plain"
            })
            
        return visualization_data, text_segments
