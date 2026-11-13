"""Provenance-labelled paper charts from observed data, never invented results.

Recorded console summaries are used only when the original
phase3 evaluation JSON files aren't present. When all 3 originals exist, the
script requires the same split, count, and SHA-256 before it produces figures.
"""
from __future__ import annotations
import argparse
import csv
import json
from math import sqrt
from pathlib import Path
from phase3.shared import DATA_DIR, RESULTS_DIR, ROOT

EVIDENCE = Path(__file__).resolve().parent / 'evidence'
TAGS = ('base', 'v1', 'v2')
PRETTY = {'base':'Base Qwen3', 'v1':'QLoRA V1', 'v2':'QLoRA V2'}


def verified_model_rows(rows):
    if len(rows)!=3 or {x['tag'] for x in rows}!=set(TAGS):
        raise ValueError('Need exactly base, v1 and v2 models')
    by_tag={x['tag']:x for x in rows}
    checked=[]
    for tag in TAGS:
        r=by_tag[tag]
        for key in ('correct','total','false_acceptances','false_rejections'):
            val=r.get(key)
            if type(val) is not int or val<0:
                raise ValueError(f'Invalid count {tag}.{key}')
        if not (r['correct']<=r['total'] and r['false_acceptances']+r['false_rejections']<=r['total']-r['correct']):
            raise ValueError(f'Inconsistent counts for {tag}')
        checked.append(r)
    if len({x['total'] for x in checked})!=1:
        raise ValueError('Comparison must use same denominator')
    return checked


def load_models(*, prefer_local=True):
    reference=json.loads((EVIDENCE/'observed_comparison.json').read_text(encoding='utf-8'))
    original=[RESULTS_DIR/f'{tag}_validation.json' for tag in TAGS]
    if prefer_local and any(p.exists() for p in original):
        if not all(p.exists() for p in original):
            raise ValueError('Some local model evaluation JSON files exist, but not all 3. Refusing to mix sources.')
        reports=[json.loads(p.read_text(encoding='utf-8')) for p in original]
        hashes={r.get('data_sha256') for r in reports}
        import hashlib
        actual=hashlib.sha256((DATA_DIR/'validation.jsonl').read_bytes()).hexdigest()
        if hashes!={actual} or any(r.get('split')!='validation' or r.get('subset_limit') is not None for r in reports):
            raise ValueError('Source data SHA256/split/subset mismatch: do not plot mixed evaluation runs')
        if any(r.get('tag')!=t for r,t in zip(reports,TAGS)):
            raise ValueError('Model tags do not match expected provenance')
        rows=[]
        for r in reports:
            s=r['scores']
            rows.append({'tag':r['tag'],'correct':s['correct'],'total':s['total'],
                         'false_acceptances':s['false_acceptances'],'false_rejections':s['false_rejections']})
        meta={'source_kind':'local_model_evaluation_json','dataset_kind':'synthetic_rule_generated_phase3',
              'split':'validation','n':len(__import__('phase3.shared',fromlist=['read_jsonl']).read_jsonl(DATA_DIR/'validation.jsonl')),
              'data_sha256':actual,'source_files':[p.as_posix() for p in original]}
    else:
        meta={key:reference[key] for key in ('source_kind','dataset_kind','split','n','data_sha256')}
        rows=reference['models']
        current=__import__('hashlib').sha256((DATA_DIR/'validation.jsonl').read_bytes()).hexdigest()
        if current!=meta['data_sha256']:
            raise ValueError('Bundled recorded metrics do not match bundled dataset SHA256')
    checked=verified_model_rows(rows)
    if meta['n']!=checked[0]['total']:
        raise ValueError('Number of examples mismatch')
    return checked,meta


def load_training_points(model):
    if model=='v1':
        raw=json.loads((EVIDENCE/'v1_observed_training_curve.json').read_text(encoding='utf-8'))
        return {'train':raw['loss_points'],'eval':raw['eval_loss_points'],'provenance':raw['source_kind'],
                'dataset':raw['dataset']}
    if model!='v2':
        raise ValueError('Only V1/V2 available')
    checkpoints=list((ROOT/'models/qa_qlora_v2').glob('checkpoint-*/trainer_state.json'))
    if not checkpoints:
        return None
    path=max(checkpoints,key=lambda p:int(p.parent.name.rsplit('-',1)[1]))
    state=json.loads(path.read_text(encoding='utf-8'))
    log=state.get('log_history',[])
    train=[{'step':int(p['step']),'loss':float(p['loss'])} for p in log if 'loss' in p and 'step' in p]
    evaluation=[{'step':int(p['step']),'eval_loss':float(p['eval_loss'])} for p in log if 'eval_loss' in p and 'step' in p]
    if not train:
        return None
    return {'train':train,'eval':evaluation,'provenance':'local_trainer_state_json','dataset':'phase3_synthetic_480_train',
            'source_file':str(path)}


def wilson(correct,total,z=1.96):
    p=correct/total
    center=(p + z*z/(2*total))/(1+z*z/total)
    spread=(z*sqrt(p*(1-p)/total+z*z/(4*total*total)))/(1+z*z/total)
    return center-spread,center+spread


def build(output:Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    output.mkdir(parents=True,exist_ok=True)
    rows,meta=load_models()
    names=[PRETTY[r['tag']] for r in rows]
    accuracies=[100*r['correct']/r['total'] for r in rows]
    colors=['#8495A9','#476F95','#167D80']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','axes.labelcolor':'#293241','axes.titleweight':'semibold',
                         'savefig.facecolor':'white'})
    fig,ax=plt.subplots(figsize=(8,5))
    xs=np.arange(3)
    bars=ax.bar(xs,accuracies,color=colors,width=.57)
    error=np.array([[100*a-100*wilson(r['correct'],r['total'])[0],
                     100*wilson(r['correct'],r['total'])[1]-100*a] for a,r in zip([v/100 for v in accuracies],rows)]).T
    ax.errorbar(xs,accuracies,yerr=error,fmt='none',capsize=5,ecolor='#263645',linewidth=1.3)
    for b,r,a in zip(bars,rows,accuracies):
        ax.text(b.get_x()+b.get_width()/2,b.get_height()+2.8,f'{a:.2f}% ({r["correct"]}/{r["total"]})',
                ha='center',va='bottom',fontsize=10,fontweight='bold')
    ax.set_xticks(xs,names)
    ax.set_ylim(0,90)
    ax.set_ylabel('Decision accuracy (%)')
    ax.set_title('Qwen3 model-only validation: Phase 3 synthetic cases',loc='left',pad=18)
    ax.grid(axis='y',alpha=.20)
    ax.set_axisbelow(True)
    fig.text(.11,.025,'Error bars: Wilson 95% intervals. Synthetic validation (n=90); not industrial performance.',fontsize=8,color='#5A6371')
    fig.tight_layout(rect=(0,.06,1,1))
    _save(fig,output,'Fig01_model_validation_accuracy');plt.close(fig)

    fig,ax=plt.subplots(figsize=(8,5))
    w=.33
    fpass=[r['false_acceptances'] for r in rows]
    ffail=[r['false_rejections'] for r in rows]
    aa=ax.bar(xs-w/2,fpass,width=w,color='#CA6654',label='False PASS (acceptance risk)')
    bb=ax.bar(xs+w/2,ffail,width=w,color='#3E789F',label='False FAIL (rejection risk)')
    for bar in (*aa,*bb):
        ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.4,str(int(bar.get_height())),ha='center',fontsize=10)
    ax.set_xticks(xs,names)
    ax.set_ylim(0,max(ffail+fpass)+5)
    ax.set_ylabel('Errors (count out of 90)')
    ax.set_title('Failure-mode tradeoff: Phase 3 validation',loc='left',pad=18)
    ax.legend(loc='upper left',frameon=False)
    ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.text(.11,.025,'False PASS: gold FAIL -> predicted PASS. False FAIL: gold PASS -> predicted FAIL.',fontsize=8,color='#5A6371')
    fig.tight_layout(rect=(0,.06,1,1));_save(fig,output,'Fig02_false_acceptance_and_rejection');plt.close(fig)
    made=['Fig01_model_validation_accuracy','Fig02_false_acceptance_and_rejection']

    for model in ('v1','v2'):
        points=load_training_points(model)
        if not points:
            print('SKIP',model.upper(),'training curve: local trainer_state.json unavailable; no fictional curve generated.')
            continue
        fig,ax=plt.subplots(figsize=(8,5))
        train=points['train']; evals=points['eval']
        ax.plot([p['step'] for p in train],[p['loss'] for p in train],marker='o',markersize=3,
                linewidth=1.8,color='#167D80',label='Training loss')
        if evals:
            ax.plot([p['step'] for p in evals],[p['eval_loss'] for p in evals],marker='s',markersize=6,
                    linewidth=1.8,linestyle='--',color='#C67F39',label='Validation loss')
        ax.set_xlabel('Optimizer step');ax.set_ylabel('Loss')
        ax.set_title(f'QLoRA {model.upper()} loss history (observed logs)',loc='left',pad=18)
        ax.legend(frameon=False)
        ax.grid(alpha=.2)
        fig.text(.11,.025,f'Source: {points["provenance"]}. Dataset: {points["dataset"]}. Loss is not accuracy.',
                 fontsize=8,color='#5A6371')
        fig.tight_layout(rect=(0,.06,1,1));name=f'Fig0{len(made)+1}_{model}_training_loss';_save(fig,output,name)
        made.append(name);plt.close(fig)
    with (output/'phase3_validation_metrics.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['model','correct','total','accuracy_pct','false_acceptances','false_rejections'],lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({'model':r['tag'],'correct':r['correct'],'total':r['total'],
                        'accuracy_pct':f'{100*r["correct"]/r["total"]:.4f}',
                        'false_acceptances':r['false_acceptances'],'false_rejections':r['false_rejections']})
    (output/'figure_provenance.json').write_text(json.dumps({'model_metric_source':meta,
      'included_figures':made,'warning':'Synthetic validation and regression checks, not independent industrial evidence',
      'figure_data_note':'V1 loss uses operator terminal log; V2 loss is plotted only if its local trainer_state.json exists.'},indent=2)+'\n',encoding='utf-8')
    print('Saved',len(made),'figures and metric provenance in',output)
    return made


def _save(fig,output:Path,stem):
    fig.savefig(output/f'{stem}.png',dpi=210)
    svg_path=output/f'{stem}.svg'
    fig.savefig(svg_path)
    # Matplotlib emits trailing spaces in multi-line SVG paths; keep git diff clean.
    svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=ROOT/'paper_figures')
    args=p.parse_args()
    build(args.output)

if __name__=='__main__':
    main()
