# Brief — translate one or more parts of the 15th Five-Year Plan Outline

You are translating a chunk of 《中华人民共和国国民经济和社会发展第十五个五年规划纲要》 (2026-03-14, Xinhua) into English.

Working directory: `/home/agheieff/fyplan`

## Read first
1. `/home/agheieff/fyplan/work/GLOSSARY.md` — mandatory term renderings + style rules. Follow it exactly.
2. Your chunk files, listed in `/home/agheieff/fyplan/work/chunks/MANIFEST.json` under your owner id (T1…T6). Each chunk is `work/chunks/part-NN.json`.

## Your chunk file format
```json
{"part": 3, "owner": "T1", "blocks": [{"id": "b0042", "type": "para", "zh": "……"}, …]}
```
`type` is one of `part`, `chapter`, `section`, `para`, `item`.
- `part` — 第X篇 (a major division). English: `Part 3  Accelerating High-Level Self-Reliance in Science and Technology and Fostering New Quality Productive Forces` — i.e. the words `Part <n>` then two spaces then the translated title (no 第X篇 prefix in the output).
- `chapter` — 第X章. Output: `Chapter 8  Strengthening Original Innovation and Efforts to Make Breakthroughs in Core Technologies in Key Fields`.
- `section` — 第X节. Output: `Section 1  The Guidance to Be Followed`.
- `para` — a body paragraph.
- `item` — a paragraph beginning with `——`. Do **not** keep the leading `——`; translate the sentence after it, capitalised, ending with a full stop (see glossary rule 3).

## Output
For **each** chunk file `work/chunks/part-NN.json`, write exactly one output file:

`/home/agheieff/fyplan/work/en/part-NN.json`

```json
{"part": 3, "translations": {"b0042": "English text for that block", "b0043": "…"}}
```

Rules:
- Every `id` present in the input must be present in the output. No extras, no omissions. The count must match exactly.
- Values are plain UTF-8 strings. No LaTeX, no Markdown, no HTML, no escaping of `& % $ # _ { } ~ ^`.
- Do not add notes, comments, or translator's remarks anywhere.
- Use `\n\n` only if a single source block genuinely needs two paragraphs of English (rare — prefer one paragraph).

## Work through the chunks in order; write each output file as soon as that chunk is done.
Do not wait until the end — partial progress must survive.

## Verify before you report done
For every output file run this check and make it pass:
```bash
cd /home/agheieff/fyplan && python3 -c "
import json,sys
p,n='work/chunks/part-03.json','work/en/part-03.json'
a=json.load(open(p)); b=json.load(open(n))
ids=[x['id'] for x in a['blocks']]; tr=b['translations']
missing=[i for i in ids if i not in tr or not tr[i].strip()]
extra=[k for k in tr if k not in ids]
print('blocks',len(ids),'translated',len(tr),'missing',missing,'extra',extra)
assert not missing and not extra
"
```
Also spot-read your own output for leaked Chinese characters:
```bash
cd /home/agheieff/fyplan && python3 -c "
import json,re,sys
d=json.load(open('work/en/part-03.json'))['translations']
bad={k:v for k,v in d.items() if re.search(r'[\u4e00-\u9fff]',v)}
print('blocks with Chinese chars:',list(bad))
"
```
A few may legitimately keep a Chinese name in parentheses — but there should be none; fix every one.

## Reporting
When all your parts are written and verified, message the Lead (`lead`) with: owner id, parts done, block counts, and any term you had to invent that is not in the glossary.
