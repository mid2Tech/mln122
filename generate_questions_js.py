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
                if i >= 3:
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
        'globalNumber': idx,
        'number': idx,
        'text': q_text,
        'options': options,
        'answer': ans,
        'note': note,
        'extra_note': extra_note
    }

all_questions = []
for idx, raw in enumerate(raw_questions):
    res = parse_block(raw, idx+1)
    all_questions.append(res)

print(f"Total parsed questions: {len(all_questions)}")

# Now create sets: 60 questions per set
sets = []
chunk_size = 60
num_sets = (len(all_questions) + chunk_size - 1) // chunk_size

for set_idx in range(num_sets):
    start = set_idx * chunk_size
    end = min(start + chunk_size, len(all_questions))
    set_questions = []
    for local_num, q in enumerate(all_questions[start:end], 1):
        q_copy = dict(q)
        q_copy['number'] = local_num
        set_questions.append(q_copy)
        
    sets.append({
        'id': f'MLN122_DE_{set_idx + 1}',
        'title': f'Đề {set_idx + 1} (Câu {start + 1} - {end})',
        'questions': set_questions
    })

# Add "Tất cả câu hỏi (526 câu)" as an option
all_qs_copy = []
for idx, q in enumerate(all_questions, 1):
    q_copy = dict(q)
    q_copy['number'] = idx
    all_qs_copy.append(q_copy)

sets.append({
    'id': 'MLN122_ALL',
    'title': f'Tất cả câu hỏi (1 - {len(all_questions)})',
    'questions': all_qs_copy
})

# Write to questions.js
with open('questions.js', 'w', encoding='utf-8') as f:
    f.write('// Dữ liệu ngân hàng câu hỏi ôn thi MLN122 - 526 câu chia đề 60 câu\n')
    f.write('const sets = ')
    json.dump(sets, f, ensure_ascii=False, indent=2)
    f.write(';\n')

print(f"Exported questions.js successfully with {len(sets)} sets!")
for s in sets:
    print(f" - {s['title']}: {len(s['questions'])} câu")

