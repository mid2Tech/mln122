import json
import re

with open('paragraphs.json', 'r', encoding='utf-8') as f:
    paragraphs = json.load(f)

def is_answer_line(text):
    t = text.strip()
    if re.match(r'^[A-Ea-e]{1,5}$', t):
        return True, t.upper(), ''
    m = re.match(r'^([A-Ea-e]{1,5})\s*[\(:](.*)$', t)
    if m:
        ans = m.group(1).upper()
        note = m.group(2).rstrip(')').strip()
        return True, ans, note
    m = re.match(r'^(?:Đáp\s*án|Đ/A|DA|Ans|Answer)\s*[:.]?\s*([A-Ea-e]{1,5})(.*)$', t, re.IGNORECASE)
    if m:
        ans = m.group(1).upper()
        note = m.group(2).strip()
        return True, ans, note
    m = re.match(r'^([A-Ea-e])\s*(W\s*=.*)$', t)
    if m:
        return True, m.group(1).upper(), m.group(2)
    return False, '', ''

i = 0
n = len(paragraphs)
raw_questions = []

while i < n:
    curr_lines = []
    ans = ''
    note = ''
    while i < n:
        is_ans, a, nt = is_answer_line(paragraphs[i])
        if is_ans:
            ans = a
            note = nt
            i += 1
            break
        else:
            curr_lines.append(paragraphs[i])
            i += 1
    
    extra_notes = []
    while i < n:
        p = paragraphs[i]
        if 'kiểu hỏi khác' in p.lower() or (extra_notes and not is_answer_line(p)[0]):
            extra_notes.append(p)
            i += 1
            if p.endswith(')'):
                break
        else:
            break
            
    raw_questions.append({
        'lines': curr_lines,
        'answer': ans,
        'note': note,
        'extra_note': '\n'.join(extra_notes) if extra_notes else ''
    })

def clean_text(s):
    s = re.sub(r'\s*\([Nn][Hh][Uu][Nn][Gg]\s+[Hh][OÒoò][ÀàÁá][Nn][Gg]\)\s*', ' ', s)
    return s.strip()

def find_sequential_options(text):
    styles = [
        ('upper_dot', 'A', r'\.'),
        ('upper_paren', 'A', r'\)'),
        ('lower_paren', 'a', r'\)'),
        ('lower_dot', 'a', r'\.'),
    ]
    
    for style_name, start_k, delim in styles:
        pos = 0
        matches = []
        is_upper = (start_k == 'A')
        for i, k in enumerate(['A', 'B', 'C', 'D', 'E']):
            target = k if is_upper else k.lower()
            m = re.search(rf'{target}\s*{delim}\s*', text[pos:])
            if m:
                actual_start = pos + m.start()
                matches.append((actual_start, k, pos + m.end()))
                pos = pos + m.end()
            else:
                if i >= 3: # at least A, B, C found
                    break
                else:
                    matches = []
                    break
        if len(matches) >= 3:
            q_text = text[:matches[0][0]].strip()
            options = []
            for j in range(len(matches)):
                content_start = matches[j][2]
                content_end = matches[j+1][0] if j+1 < len(matches) else len(text)
                opt_text = text[content_start:content_end].strip()
                options.append({'key': matches[j][1], 'text': opt_text})
            return q_text, options
            
    return text, []

def parse_block(raw, idx):
    lines = [clean_text(l) for l in raw['lines'] if l.strip()]
    ans = raw['answer']
    note = raw['note']
    extra_note = raw['extra_note']
    
    if not lines:
        return None
        
    has_separate = False
    if len(lines) > 1:
        if re.match(r'^[A-Da-d]\s*[\.\)]\s*', lines[1]):
            has_separate = True
            
    q_text = ''
    options = []
    
    if has_separate:
        q_text = lines[0]
        for l in lines[1:]:
            m = re.match(r'^([A-Ea-e])\s*[\.\)]\s*(.*)$', l)
            if m:
                options.append({'key': m.group(1).upper(), 'text': m.group(2).strip()})
            else:
                if options:
                    options[-1]['text'] += ' ' + l
                else:
                    q_text += ' ' + l
    else:
        full_text = ' '.join(lines)
        q_text, options = find_sequential_options(full_text)
        if not options:
            q_text = full_text
            
    return {
        'number': idx,
        'text': q_text,
        'options': options,
        'answer': ans,
        'note': note,
        'extra_note': extra_note,
        'raw_lines': lines
    }

parsed = []
failed = []
for idx, raw in enumerate(raw_questions):
    res = parse_block(raw, idx+1)
    if not res or len(res['options']) < 2:
        failed.append((idx+1, raw, res))
    else:
        parsed.append(res)

print(f"Successfully parsed: {len(parsed)}/{len(raw_questions)}")
print(f"Failed count: {len(failed)}")

for idx, raw, res in failed:
    print(f"\n--- FAILED Question {idx} ---")
    print(f"Lines: {raw['lines']}")
    print(f"Answer: {raw['answer']}")
    if res:
        print(f"Options found: {len(res['options'])}")
