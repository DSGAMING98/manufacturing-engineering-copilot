"""Final-review SECOM audit: multi-seed chronology, window model table and block-width sensitivity.

This code is retrospective and the test partitions have been inspected before.
All hyperparameters and thresholds are selected on their corresponding
validation periods. Never treat post-hoc ranking as a fresh blind holdout.
Run: python -m real_models.final_review_temporal_models
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score
from real_models.train_real_models import fetch
from real_models.evaluate_secom_chrono import read_labels_and_timestamps
from real_models.chronological_baselines import candidate_sets
from real_models.temporal_robustness_review import moving_block_interval

OUT=Path(__file__).resolve().parents[1]/"real_models/evidence/final_review_temporal_models.json"

def choose(y_val,models,x_train,y_train,x_val):
    good=None
    for setting,model in models:
        model.fit(x_train,y_train)
        prob=model.predict_proba(x_val)[:,1]
        auc=float(roc_auc_score(y_val,prob))
        if good is None or auc>good[0]:
            good=(auc,setting,model,prob)
    valauc,setting,model,valp=good
    threshold=float(max(np.unique(valp),key=lambda t:(f1_score(y_val,valp>=t,zero_division=0),t)))
    return model,setting,valauc,threshold

def binary_metrics(y,p):
    return {"n":int(len(y)),"failures":int(y.sum()),"prevalence":float(y.mean()),
            "roc_auc":float(roc_auc_score(y,p)),
            "average_precision":float(average_precision_score(y,p))}

def main():
    folder,sha=fetch("secom")
    x=np.genfromtxt(folder/"secom.data",missing_values="NaN")
    y,ts=read_labels_and_timestamps(folder/"secom_labels.data")
    order=np.argsort(ts,kind="stable")
    x,y=x[order],y[order]
    a,b=int(len(y)*.6),int(len(y)*.8)
    chrono_y=y[b:]

    # Fifteen independently fitted 600-tree Extra Trees models, each selects
    # its own max_features on the same chronological validation records.
    repeat=[]
    for seed in range(15):
        options=[]
        for f in ("sqrt",.3,.5):
            options.append((f"max_features={f}",make_pipeline(
                SimpleImputer(strategy="median"),
                ExtraTreesClassifier(n_estimators=600,max_features=f,
                                     class_weight="balanced",random_state=seed,n_jobs=-1))))
        model,setting,val_auc,th=choose(y[a:b],options,x[:a],y[:a],x[a:b])
        p=model.predict_proba(x[b:])[:,1]
        m=binary_metrics(chrono_y,p)
        m.update({"seed":seed,"setting":setting,"validation_auc":val_auc,"threshold":th,
                  "failure_f1":float(f1_score(chrono_y,p>=th,zero_division=0)),
                  "alerts":int((p>=th).sum()),"caught":int(((p>=th)&(chrono_y==1)).sum())})
        repeat.append(m)
        print("chronological seed",seed,"AUC",round(m["roc_auc"],5),flush=True)

    def summary(vals):
        a=np.asarray(vals,dtype=float)
        return {"n":len(a),"mean":float(a.mean()),"sd":float(a.std(ddof=1)),
                "min":float(a.min()),"max":float(a.max()),
                "median":float(np.median(a))}
    repeated={"n":len(repeat),"auc_summary":summary([z["roc_auc"] for z in repeat]),
              "average_precision_summary":summary([z["average_precision"] for z in repeat]),
              "per_seed":repeat}

    # Main seed-42 chronological release model, to match historical report.
    baseoptions=[(f"max_features={f}",make_pipeline(
          SimpleImputer(strategy="median"),ExtraTreesClassifier(n_estimators=600,
            max_features=f,class_weight="balanced",random_state=42,n_jobs=-1)))
        for f in ("sqrt",.3,.5)]
    model,setting,va,th=choose(y[a:b],baseoptions,x[:a],y[:a],x[a:b])
    prob=model.predict_proba(x[b:])[:,1]
    intervals={}
    for block in (8,16,32):
        intervals[str(block)]=moving_block_interval(y[b:],prob,block=block,n_boot=1200,seed=20261114)
    print("block CI sensitivity",intervals,flush=True)

    # All five model families on the same three expanding-origin windows.
    windows=[]
    models=candidate_sets()
    test_width=235
    for fold,train_end in enumerate((627,862,1097),start=1):
        val_end=train_end+test_width
        test_end=val_end+test_width
        if test_end>len(y):break
        result={"fold":fold,"train_n":train_end,"validation_n":test_width,
                "test_n":test_width,"train_failures":int(y[:train_end].sum()),
                "validation_failures":int(y[train_end:val_end].sum()),
                "test_failures":int(y[val_end:test_end].sum()),
                "test_prevalence":float(y[val_end:test_end].mean()),"models":{}}
        for name,options in models.items():
            choice,setting,va,threshold=choose(y[train_end:val_end],options,
                        x[:train_end],y[:train_end],x[train_end:val_end])
            scores=choice.predict_proba(x[val_end:test_end])[:,1]
            vals=binary_metrics(y[val_end:test_end],scores)
            vals.update({"selected":setting,"validation_auc":va,"threshold":threshold,
                         "alerts":int((scores>=threshold).sum()),
                         "failure_f1":float(f1_score(y[val_end:test_end],scores>=threshold,zero_division=0))})
            result["models"][name]=vals
            print("expanding",fold,name,"AUC",round(vals["roc_auc"],4),
                  "AP",round(vals["average_precision"],4),flush=True)
        windows.append(result)

    aggregate={}
    for name in models:
        metrics=[w["models"][name] for w in windows]
        aggregate[name]={
            "fold_roc_auc":[m["roc_auc"] for m in metrics],
            "fold_average_precision":[m["average_precision"] for m in metrics],
            "unweighted_mean_auc":float(np.mean([m["roc_auc"] for m in metrics])),
            "unweighted_mean_ap":float(np.mean([m["average_precision"] for m in metrics])),
            "n_folds":len(metrics)}
    result={
        "source_sha256":sha,"retrospective_post_hoc":True,
        "chronological_model_seed_repeats":repeated,
        "original_seed42_chronological":{"metrics":binary_metrics(y[b:],prob),
                                        "selected":setting,"validation_auc":va,
                                        "block_bootstrap_by_size":intervals},
        "expanding_origin":{"folds":windows,"summary":aggregate},
        "limitations":[
          "Fifteen random seeds share one temporal partition and therefore do not represent fifteen independent future datasets.",
          "Model families were selected from small validation grids; test windows had only 7,17,9 failures.",
          "A circular block bootstrap does not establish the true dependence length.",
          "The repeated tests are post-hoc on previously inspected SECOM records."
        ]
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("SAVED",OUT,flush=True)
if __name__=="__main__":main()
