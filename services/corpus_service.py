import pandas as pd
from kiwipiepy import Kiwi
import re
import unicodedata
import os

class CorpusService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CorpusService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        
        self.is_ready = False
        self.error_msg = ""
        self.use_mock = False 
        self.word_df = None
        self.grammar_df = None
        self.analyzer = None
        self.word_map = {}
        self.grammar_map = {}
        self.idiom_map = {}
        self.ida_entry = None

        # 매핑 테이블 (Constants)
        self.pos_map = {
            'NNG': 'N', 'NNP': 'N', 'NR': 'N', 'NP': 'N', 
            'NNB': 'NB', 
            'VV': 'V', 'VA': 'V', 'VX': 'V', 'VCP': 'V', 'VCN': 'V',
            'VV-I': 'V', 'VA-I': 'V', 'VX-I': 'V', 'VV-R': 'V', 'VA-R': 'V', 
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

        self._load_resources()
        self._initialized = True

    def _load_resources(self):
        try:
            # 1. 파일 경로 및 로드 (상위 디렉토리 기준)
            # services/corpus_service.py -> ../ (project root)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

            # '이다' 데이터
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

            self._build_lookup_tables()
            self.is_ready = True
        except Exception as e:
            self.error_msg = str(e); print(f"CorpusService 초기화 오류: {self.error_msg}")

    def clean_key(self, key_str):
        key = str(key_str)
        key = key.replace('ᆯ', 'ㄹ').replace('ᆫ', 'ㄴ').replace('ᆸ', 'ㅂ')
        key = key.replace('ᆷ', 'ㅁ').replace('ᆼ', 'ㅇ').replace('ᆨ', 'ㄱ')
        key = key.replace('.', '').replace('-', '').replace('–', '').replace('~', '').replace('"', '').replace("'", '').strip()
        key = re.sub(r'[0-9]+\([0-9]+\)', '', key)
        key = re.sub(r'\([0-9]+\)', '', key)
        key = re.sub(r'[0-9]+$', '', key)
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
                cleaned = self.clean_key(word)
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
                        valid_tokens.append(self.clean_key(t.form))
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

        for _, row in self.grammar_df.fillna('').iterrows():
            data = {'level': row['등급'], 'uid': row['전체 번호'], 'desc': row.get('길잡이말', ''), 'meaning': row.get('의미', ''), 'class': str(row['분류'])}
            main_form = str(row['대표형']).strip()
            if ' ' in main_form or '표현' in data['class']: register_idiom(main_form, data)
            
            class_str = str(row['분류'])
            pos_keys = get_grammar_pos_keys(class_str)
            if '이다' in main_form and '조사' in class_str: cleaned_main = '이다'
            else: cleaned_main = self.clean_key(main_form)
            
            if cleaned_main:
                for pk in pos_keys: register_grammar((cleaned_main, pk), data, is_main=True)
            
            for rel_form in row['search_related']:
                if ' ' in rel_form or '표현' in data['class']: register_idiom(rel_form, data)
                cleaned_rel = self.clean_key(rel_form)
                if cleaned_rel:
                    for pk in pos_keys: register_grammar((cleaned_rel, pk), data, is_main=False)

        for k in self.idiom_map:
            self.idiom_map[k].sort(key=lambda x: len(x['sequence']), reverse=True)

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
