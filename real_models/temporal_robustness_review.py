"""Temporal evaluation audit: 50 repeated random splits, 3 rolling origins, block CI.

All experiments are retrospective and post-hoc. Do not interpret them as
new independent holdouts. Run: python -m real_models.temporal_robustness_review
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             f1_score, balanced_accuracy_score, confusion_matrix)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from real_models.train_real_models import fetch
from real_models.evaluate_secom_chrono import read_labels_and_timestamps

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"real_models/evidence/temporal_robustness_report.json"
FEATURE_OPTIONS=("sqrt",.3,.5)
SEEDS=range(50)

def fit_select(x_train,y_train,x_val,y_val):
    if len(np.unique(y_train))<2 or len(np.unique(y_val))<2:
        raise ValueError("Training and validation must both contain pass and failure.")
    chosen=None
    for fraction in FEATURE_OPTIONS:
        model=make_pipeline(
            SimpleImputer(strategy="median"),
            ExtraTreesClassifier(n_estimators=600,class_weight="balanced",
                max_features=fraction,random_state=42,n_jobs=-1))
        model.fit(x_train,y_train)
        val_probability=model.predict_proba(x_val)[:,1]
        auc=float(roc_auc_score(y_val,val_probability))
        if chosen is None or auc>chosen[0]:
            chosen=(auc,fraction,model,val_probability)
    auc,fraction,model,val_probability=chosen
    threshold=float(max(np.unique(val_probability),
            key=lambda t:(f1_score(y_val,val_probability>=t,zero_division=0),t)))
    return auc,fraction,model,threshold

def metrics(y,prob,threshold):
    pred=(prob>=threshold).astype(int)
    return {
        "roc_auc":float(roc_auc_score(y,prob)),
        "average_precision":float(average_precision_score(y,prob)),
        "balanced_accuracy":float(balanced_accuracy_score(y,pred)),
        "failure_f1":float(f1_score(y,pred,zero_division=0)),
        "failure_recall":float((pred[y==1]==1).mean()),
        "confusion_matrix":confusion_matrix(y,pred,labels=(0,1)).tolist(),
    }

def moving_block_interval(y,prob,block=16,n_boot=1200,seed=20261114):
    """Consecutive, circular time blocks; not a guarantee against dependence."""
    rng=np.random.default_rng(seed)
    n=len(y)
    n_blocks=int(np.ceil(n/block))
    indices=np.arange(n)
    auroc=[]; ap=[]
    for _ in range(n_boot):
        starts=rng.integers(0,n,n_blocks)
        positions=np.concatenate([(indices[(i+np.arange(block))%n]) for i in starts])[:n]
        if len(set(y[positions]))<2:
            continue
        auroc.append(float(roc_auc_score(y[positions],prob[positions])))
        ap.append(float(average_precision_score(y[positions],prob[positions])))
    return {
       "method":f"circular moving block bootstrap; {block}-record blocks; {n_boot} replicates",
       "valid_resamples":len(auroc),
       "roc_auc_95_ci":[float(z) for z in np.quantile(auroc,[.025,.975])],
       "average_precision_95_ci":[float(z) for z in np.quantile(ap,[.025,.975])],
    }

def main():
    folder,source_hash=fetch("secom")
    x=np.genfromtxt(folder/"secom.data",missing_values="NaN")
    y,ts=read_labels_and_timestamps(folder/"secom_labels.data")
    assert x.shape==(len(y),590)
    sorted_order=np.argsort(ts,kind="stable")
    xt,yt,ts=x[sorted_order],y[sorted_order],ts[sorted_order]
    n=len(y); a=int(.6*n); b=int(.8*n)
    val_auc,fraction,chrono_model,cutoff=fit_select(xt[:a],yt[:a],xt[a:b],yt[a:b])
    prob=chrono_model.predict_proba(xt[b:])[:,1]
    ref=metrics(yt[b:],prob,cutoff)
    ref["moving_block_bootstrap"]=moving_block_interval(yt[b:],prob)
    ref["validation_auc"]=val_auc
    ref["selected_max_features"]=fraction
    ref["validation_threshold"]=cutoff
    ref["positive_count_validation"]=int(yt[a:b].sum())
    ref["positive_count_test"]=int(yt[b:].sum())
    ref["test_time_start"]=ts[b].isoformat(sep=" ")
    ref["test_time_end"]=ts[-1].isoformat(sep=" ")
    print("chronological AUC",ref["roc_auc"],"block CI",ref["moving_block_bootstrap"],flush=True)

    random_records=[]
    for seed in SEEDS:
        dx,te,dy,ty=train_test_split(x,y,test_size=.2,stratify=y,random_state=seed)
        tr,v,train_y,val_y=train_test_split(dx,dy,test_size=.25,stratify=dy,random_state=seed)
        va,mf,est,th=fit_select(tr,train_y,v,val_y)
        outcome=metrics(ty,est.predict_proba(te)[:,1],th)
        random_records.append({
            "seed":seed,"selected_max_features":mf,"validation_auc":va,
            "test_auc":outcome["roc_auc"],"test_ap":outcome["average_precision"],
            "test_failure_f1":outcome["failure_f1"],
            "train_failures":int(train_y.sum()),"validation_failures":int(val_y.sum()),
            "test_failures":int(ty.sum())})
        if seed%10==9:print("random completed",seed+1,flush=True)
    random_aucs=np.array([q["test_auc"] for q in random_records])
    random_summary={
        "seeds":len(random_records),
        "mean_auc":float(np.mean(random_aucs)),
        "sample_sd_auc":float(np.std(random_aucs,ddof=1)),
        "minimum_auc":float(np.min(random_aucs)),
        "maximum_auc":float(np.max(random_aucs)),
        "percentiles_auc":{"2.5":float(np.percentile(random_aucs,2.5)),
                         "25":float(np.percentile(random_aucs,25)),
                         "50":float(np.percentile(random_aucs,50)),
                         "75":float(np.percentile(random_aucs,75)),
                         "97.5":float(np.percentile(random_aucs,97.5))},
        "fraction_random_auc_le_chronological":float(np.mean(random_aucs<=ref["roc_auc"])),
        "individual_seeds":random_records,
    }
    # Three expanding-origin evaluation windows, with disjoint test periods.
    # Each fold strictly trains on earlier records and validates after training.
    width=235
    folds=[]
    for index,train_end in enumerate((627,862,1097),start=1):
        val_end=train_end+width
        test_end=min(val_end+width,n)
        if test_end>n:break
        tr,va,te=slice(0,train_end),slice(train_end,val_end),slice(val_end,test_end)
        if any(len(np.unique(yt[ss]))<2 for ss in (tr,va,te)):
            folds.append({"fold":index,"status":"NOT_ESTIMABLE",
                          "positive_counts":[int(yt[ss].sum()) for ss in (tr,va,te)]})
            continue
        vaauc,mf,model,threshold=fit_select(xt[tr],yt[tr],xt[va],yt[va])
        p=model.predict_proba(xt[te])[:,1]
        outcome=metrics(yt[te],p,threshold)
        folds.append({
            "fold":index,"status":"MEASURED",
            "train_n":len(yt[tr]),"validation_n":len(yt[va]),"test_n":len(yt[te]),
            "train_failures":int(yt[tr].sum()),"validation_failures":int(yt[va].sum()),
            "test_failures":int(yt[te].sum()),"test_begin":ts[te.start].isoformat(sep=" "),
            "test_end":ts[te.stop-1].isoformat(sep=" "),"selected_max_features":mf,
            "validation_auc":vaauc,"selected_threshold":threshold,
            "test":outcome,
        })
        print("rolling fold",index,"test AUC",outcome["roc_auc"],flush=True)
    result={
      "status":"MEASURED",
      "source":"UCI SECOM",
      "source_archive_sha256":source_hash,
      "post_hoc":True,
      "not_a_new_independent_holdout":True,
      "nonpaired_random_vs_chrono":True,
      "model":"600-tree balanced Extra Trees, validation-selected max_features from sqrt/0.3/0.5",
      "chronological_reference":ref,
      "random_split_distribution":random_summary,
      "rolling_origin":{"folds":folds,
          "design":"expanding training; 235-row validation, then 235-row disjoint test; 3 folds",
          "not_prospective":True},
      "interpretation_limits":[
        "Random and chronological populations, model fits and thresholds differ.",
        "These analyses were designed after initial test results were inspected.",
        "Random reference performance is not a confidence interval for time generalization.",
        "Moving block bootstrap interval depends on block width and retrospective test assumptions.",
        "Validation-positive counts are small; thresholded F1 is unstable.",
        "This is not multi-plant or prospective evaluation."
      ]
    }
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("Saved",DEST,flush=True)

if __name__=="__main__":main()
