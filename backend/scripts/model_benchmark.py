"""Fixed-evidence model comparison, separate from Search acceptance.

Reads a locally prepared, authorized policy snapshot. Sends only selected blocks
to the explicitly selected Vertex project/global endpoint. Results contain source
hashes, model answers and usage; never credentials. Pricing is a dated snapshot,
not a billing statement. This is opt-in and never runs in CI.
"""
import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from google import genai
from google.oauth2.credentials import Credentials
from app.services import gemini
from app.pipelines import vertex_search as rag

CASES=[
    ('zh-confidential','政府可否直接把機密資料輸入外部人工智慧？請保留規定中的例外條件。','zh-TW',['p53','p54','p82']),
    ('en-review','What must staff review and disclose before publishing an AI-assisted document affecting citizens?','en',['p65','p102','p111']),
    ('ja-decision','市民の権利義務に影響する決定を、人の確認なしでAIが直接下してよいですか？','ja',['p53']),
    ('zh-missing','依所附證據，臺北市 2030 年人工智慧年度預算確切是多少？','zh-TW',['p23']),
]
# Standard global USD per million, excluding promotional credits and taxes.
# https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing
PRICES={'gemini-2.5-flash':(.30,2.50),'gemini-3.7-flash':(1.50,7.50)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--project',default='tdf-ocf')
    parser.add_argument('--account',default='hcchien@reviz.tw')
    args=parser.parse_args()
    source=json.loads(args.source.read_text())
    blocks={b['id']:b['text'] for b in source['blocks']}
    report={'created_at':datetime.now(timezone.utc).isoformat(),'project':args.project,'location':'global',
        'source':{k:source[k] for k in ['id','title','version']},'search_exercised':False,
        'pricing_date':'2026-09-16','pricing_basis':'standard global; excludes introductory credits, taxes, Search and hosting',
        'thresholds':{'latency_seconds':60,'usd_per_answer_before_credits':.10,'valid_citations':True},'results':[]}
    access=subprocess.run(['gcloud','auth','print-access-token','--account',args.account],check=True,capture_output=True,text=True).stdout.strip()
    with genai.Client(vertexai=True,project=args.project,location='global',credentials=Credentials(token=access),
                      http_options={'timeout':120000}) as api:
        for model in PRICES:
            for name,question,language,ids in CASES:
                text='\n\n'.join(blocks[i] for i in ids)
                def fixed_evidence(*args,**kwargs):
                    return [{'id':source['id'],'title':source['title'],'snippets':[{'snippet':text}],
                             'metadata':{'language':'zh-TW','version':source['version']}}]
                previous=rag.retrieve
                rag.retrieve=fixed_evidence
                try:
                    system,contents,_,metadata=rag.prepare_rag(question,interface_language='en')
                finally:
                    rag.retrieve=previous
                started=time.monotonic()
                response=api.models.generate_content(model=model,contents=contents,config=gemini.generation_config(system))
                elapsed=time.monotonic()-started
                usage=response.usage_metadata
                prompt=usage.prompt_token_count or 0
                output=(usage.candidates_token_count or 0)+(usage.thoughts_token_count or 0)
                usd=(prompt*PRICES[model][0]+output*PRICES[model][1])/1_000_000
                answer=response.text or ''
                citations=re.findall(r'\[(\d+)\]',answer)
                # Language and semantic fidelity are also reviewed from the saved answers.
                checks={'language_resolution':metadata['response_language']==language,
                        'citations':bool(citations) and set(citations)=={'1'},
                        'latency':elapsed<=60,'cost':usd<=.10,
                        'complete':bool(answer) and str(response.candidates[0].finish_reason).endswith('STOP')}
                row={'model':model,'case':name,'source_blocks':ids,'language':language,'answer':answer,
                     'latency_seconds':round(elapsed,3),'input_tokens':prompt,'output_including_reasoning_tokens':output,
                     'estimated_usd_before_credits':round(usd,7),'checks':checks}
                report['results'].append(row)
                args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
                print(json.dumps({k:v for k,v in row.items() if k!='answer'}),flush=True)
    if not all(all(r['checks'].values()) for r in report['results']):
        raise SystemExit('A benchmark gate failed; review saved answers before acceptance.')


if __name__=='__main__':main()
